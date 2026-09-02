#!/usr/bin/env python3
from __future__ import annotations
"""BIST hisseleri için haftalık SuperTrend (10, 3) tarama verisi üretir.

Günlük OHLC verileri Yahoo Finance'tan alınır, cuma kapanışlı haftalık
mumlara çevrilir ve Pine Script v4'teki ATR/SuperTrend mantığı uygulanır.
Çıktı, güncel haftalık mumdan bir önceki haftayı hedefler.
"""

import json
import logging
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytz


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

TRT = pytz.timezone("Europe/Istanbul")
ROOT = Path(__file__).parent.parent
TICKERS_PATH = ROOT / "data" / "bist-tickers.json"
OUTPUT_PATH = ROOT / "public" / "data" / "bist-weekly-supertrend.json"

ATR_PERIOD = 10
ATR_MULTIPLIER = 3.0
HISTORY_PERIOD = "10y"
BATCH_SIZE = 80
BATCH_DELAY_SECONDS = 1.0


def load_tickers() -> tuple[list[dict], str]:
    if not TICKERS_PATH.exists():
        log.error("Hisse listesi bulunamadı: %s", TICKERS_PATH)
        sys.exit(1)

    with TICKERS_PATH.open(encoding="utf-8") as handle:
        data = json.load(handle)

    tickers = data.get("tickers", [])
    return tickers, data.get("updated_at", "")


def target_week_end(as_of: datetime | date | None = None) -> date:
    """Grafikteki güncel haftalık mumdan bir önceki mumun cuma tarihini döndürür."""
    if as_of is None:
        local_date = datetime.now(TRT).date()
    elif isinstance(as_of, datetime):
        local_date = as_of.astimezone(TRT).date() if as_of.tzinfo else as_of.date()
    else:
        local_date = as_of

    monday = local_date - timedelta(days=local_date.weekday())
    current_week_friday = monday + timedelta(days=4)
    return current_week_friday - timedelta(days=7)


def pine_rma(series: pd.Series, length: int) -> pd.Series:
    """Pine Script rma/atr başlangıcını (ilk değer = SMA) taklit eder."""
    values = series.astype(float).to_numpy()
    result = np.full(len(values), np.nan, dtype=float)

    valid_positions = np.flatnonzero(~np.isnan(values))
    if len(valid_positions) < length:
        return pd.Series(result, index=series.index, dtype=float)

    seed_window = valid_positions[:length]
    seed_position = seed_window[-1]
    result[seed_position] = float(np.mean(values[seed_window]))

    previous = result[seed_position]
    for position in range(seed_position + 1, len(values)):
        value = values[position]
        if np.isnan(value):
            continue
        previous = ((length - 1) * previous + value) / length
        result[position] = previous

    return pd.Series(result, index=series.index, dtype=float)


def weekly_ohlc(daily: pd.DataFrame) -> pd.DataFrame:
    required = ["Open", "High", "Low", "Close"]
    frame = daily[required].copy().dropna(how="all")
    frame.index = pd.to_datetime(frame.index)
    if frame.index.tz is not None:
        frame.index = frame.index.tz_convert(TRT).tz_localize(None)
    frame = frame.sort_index()

    weekly = frame.resample("W-FRI", label="right", closed="right").agg(
        {"Open": "first", "High": "max", "Low": "min", "Close": "last"}
    )
    return weekly.dropna(subset=required)


def calculate_supertrend(weekly: pd.DataFrame) -> pd.DataFrame:
    """Kullanıcının Pine Script v4 SuperTrend hesaplamasını uygular."""
    frame = weekly.copy()
    previous_close = frame["Close"].shift(1)
    true_range = pd.concat(
        [
            frame["High"] - frame["Low"],
            (frame["High"] - previous_close).abs(),
            (frame["Low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    atr = pine_rma(true_range, ATR_PERIOD)
    source = (frame["High"] + frame["Low"]) / 2
    basic_up = source - ATR_MULTIPLIER * atr
    basic_down = source + ATR_MULTIPLIER * atr

    final_up = np.full(len(frame), np.nan, dtype=float)
    final_down = np.full(len(frame), np.nan, dtype=float)
    trend = np.ones(len(frame), dtype=int)

    closes = frame["Close"].to_numpy(dtype=float)
    up_values = basic_up.to_numpy(dtype=float)
    down_values = basic_down.to_numpy(dtype=float)

    for i in range(len(frame)):
        if np.isnan(up_values[i]) or np.isnan(down_values[i]):
            if i > 0:
                trend[i] = trend[i - 1]
            continue

        previous_up = final_up[i - 1] if i > 0 and not np.isnan(final_up[i - 1]) else up_values[i]
        previous_down = final_down[i - 1] if i > 0 and not np.isnan(final_down[i - 1]) else down_values[i]

        if i > 0 and closes[i - 1] > previous_up:
            final_up[i] = max(up_values[i], previous_up)
        else:
            final_up[i] = up_values[i]

        if i > 0 and closes[i - 1] < previous_down:
            final_down[i] = min(down_values[i], previous_down)
        else:
            final_down[i] = down_values[i]

        previous_trend = trend[i - 1] if i > 0 else 1
        if previous_trend == -1 and closes[i] > previous_down:
            trend[i] = 1
        elif previous_trend == 1 and closes[i] < previous_up:
            trend[i] = -1
        else:
            trend[i] = previous_trend

    frame["ATR"] = atr
    frame["Up"] = final_up
    frame["Down"] = final_down
    frame["Trend"] = trend
    frame["BuySignal"] = (frame["Trend"] == 1) & (frame["Trend"].shift(1) == -1)
    frame["SuperTrend"] = np.where(frame["Trend"] == 1, frame["Up"], frame["Down"])
    return frame


def _field_frame(raw: pd.DataFrame, field: str, requested: list[str]) -> pd.DataFrame:
    if raw.empty:
        return pd.DataFrame()

    if isinstance(raw.columns, pd.MultiIndex):
        try:
            data = raw[field]
        except KeyError:
            return pd.DataFrame()
        return data if isinstance(data, pd.DataFrame) else data.to_frame(requested[0])

    if field not in raw.columns or len(requested) != 1:
        return pd.DataFrame()
    return raw[[field]].rename(columns={field: requested[0]})


def download_batch(symbols: list[str], attempts: int = 3) -> pd.DataFrame:
    import yfinance as yf

    for attempt in range(1, attempts + 1):
        try:
            raw = yf.download(
                tickers=symbols,
                period=HISTORY_PERIOD,
                interval="1d",
                # Yahoo'nun ham OHLC serisi bölünmeleri fiyat geçmişine uygular.
                # Adj Close oranını kullanan auto_adjust nakit temettüleri de
                # geçmiş OHLC'ye taşır. TradingView'ın temettü düzeltmesi kapalı
                # standart grafiğiyle eşleşmek için Yahoo'nun bölünme uyumlu ham
                # OHLC serisi kullanılır.
                auto_adjust=False,
                actions=True,
                progress=False,
                threads=True,
                group_by="column",
            )
            if not raw.empty:
                return raw
        except Exception as exc:
            log.warning("İndirme denemesi %s/%s başarısız: %s", attempt, attempts, exc)
        if attempt < attempts:
            time.sleep(attempt * 2)
    return pd.DataFrame()


def extract_daily(raw: pd.DataFrame, symbol: str, requested: list[str]) -> pd.DataFrame:
    columns: dict[str, pd.Series] = {}
    for field in ("Open", "High", "Low", "Close"):
        field_data = _field_frame(raw, field, requested)
        if symbol not in field_data.columns:
            return pd.DataFrame()
        columns[field] = field_data[symbol]
    return pd.DataFrame(columns).dropna(how="all")


def stock_result(info: dict, daily: pd.DataFrame, target: date) -> dict | None:
    if daily.empty:
        return None

    calculated = calculate_supertrend(weekly_ohlc(daily))
    rows = calculated[calculated.index.date == target]
    if rows.empty:
        return None

    row = rows.iloc[-1]
    if pd.isna(row["ATR"]) or pd.isna(row["SuperTrend"]):
        return None

    return {
        "ticker": info["ticker"],
        "name": info.get("name", ""),
        "sector": info.get("sector", "Diğer"),
        "indices": info.get("indices", []),
        "week_end": target.isoformat(),
        "close": round(float(row["Close"]), 2),
        "supertrend": round(float(row["SuperTrend"]), 2),
        "trend": int(row["Trend"]),
        "buy_signal": bool(row["BuySignal"]),
    }


def main() -> None:
    started = time.time()
    tickers, tickers_updated_at = load_tickers()
    target = target_week_end()
    ticker_map = {f"{item['ticker']}.IS": item for item in tickers}
    symbols = list(ticker_map)

    log.info("%s BIST hissesi taranacak; hedef hafta: %s", len(symbols), target)
    results: list[dict] = []
    failed: list[str] = []

    for start in range(0, len(symbols), BATCH_SIZE):
        batch = symbols[start : start + BATCH_SIZE]
        batch_number = start // BATCH_SIZE + 1
        batch_count = (len(symbols) + BATCH_SIZE - 1) // BATCH_SIZE
        log.info("Paket %s/%s indiriliyor (%s hisse)", batch_number, batch_count, len(batch))
        raw = download_batch(batch)

        if raw.empty:
            failed.extend(symbol.replace(".IS", "") for symbol in batch)
            continue

        for symbol in batch:
            result = stock_result(ticker_map[symbol], extract_daily(raw, symbol, batch), target)
            if result is None:
                failed.append(symbol.replace(".IS", ""))
            else:
                results.append(result)

        if start + BATCH_SIZE < len(symbols):
            time.sleep(BATCH_DELAY_SECONDS)

    results.sort(key=lambda item: item["ticker"])
    signals = sum(1 for item in results if item["buy_signal"])
    elapsed = round(time.time() - started, 1)

    output = {
        "ready": True,
        "generated_at": datetime.now(TRT).isoformat(),
        "target_week_end": target.isoformat(),
        "tickers_updated_at": tickers_updated_at,
        "source": "Yahoo Finance",
        "parameters": {
            "timeframe": "weekly",
            "atr_period": ATR_PERIOD,
            "atr_multiplier": ATR_MULTIPLIER,
            "source": "HL2",
            "history_period": HISTORY_PERIOD,
            "price_adjustment": "splits_only",
            "dividend_adjusted": False,
            "current_week_excluded": True,
        },
        "total_tickers": len(symbols),
        "scanned": len(results),
        "failed": len(failed),
        "failed_tickers": failed,
        "signal_count": signals,
        "elapsed_seconds": elapsed,
        "stocks": results,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as handle:
        json.dump(output, handle, ensure_ascii=False, separators=(",", ":"))

    log.info(
        "Tamamlandı: %s/%s hisse, %s AL sinyali, %ss",
        len(results),
        len(symbols),
        signals,
        elapsed,
    )


if __name__ == "__main__":
    main()
