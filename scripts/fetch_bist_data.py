#!/usr/bin/env python3
from __future__ import annotations
"""
BIST hisselerinin fiyat verilerini yfinance üzerinden çeker.
public/data/bist-heatmap.json dosyasına kaydeder.
Her 15 dakikada bir çalışır (GitHub Actions cron).
"""

import yfinance as yf
import pandas as pd
import json
import logging
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
import pytz

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

TRT     = pytz.timezone("Europe/Istanbul")
ROOT    = Path(__file__).parent.parent
TICKERS_PATH = ROOT / "data" / "bist-tickers.json"
OUTPUT_PATH  = ROOT / "public" / "data" / "bist-heatmap.json"

BATCH_SIZE   = 100   # yfinance'e aynı anda gönderilecek hisse sayısı
BATCH_DELAY  = 1.0   # batch'ler arası bekleme (saniye)


def load_tickers() -> list[dict]:
    if not TICKERS_PATH.exists():
        log.error(f"Ticker dosyası bulunamadı: {TICKERS_PATH}")
        log.error("Önce fetch_bist_tickers.py çalıştırın.")
        sys.exit(1)
    with open(TICKERS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    tickers = data.get("tickers", [])
    log.info(f"{len(tickers)} hisse yüklendi (güncel: {data.get('updated_at', '?')})")
    return tickers, data.get("updated_at", "")


def pct_change(new_val, old_val) -> float | None:
    """İki fiyat arasındaki % değişimi hesaplar."""
    if old_val is None or new_val is None or old_val == 0:
        return None
    return round((new_val - old_val) / old_val * 100, 2)


def fetch_prices_batch(tickers_is: list[str]) -> pd.DataFrame:
    """
    Verilen .IS uzantılı ticker listesi için son 1 yıllık günlük kapanış verisi çeker.
    Döndürür: DataFrame (sütun=ticker, satır=tarih, değer=kapanış fiyatı)
    """
    try:
        raw = yf.download(
            tickers=tickers_is,
            period="2y",
            interval="1d",
            auto_adjust=True,
            progress=False,
            threads=True,
        )
        if raw.empty:
            return pd.DataFrame()

        # Çoklu ticker: MultiIndex sütun yapısı → Sadece 'Close' al
        if isinstance(raw.columns, pd.MultiIndex):
            close = raw["Close"]
        else:
            # Tek ticker durumu
            close = raw[["Close"]]
            close.columns = [tickers_is[0]]

        return close
    except Exception as e:
        log.warning(f"Batch indirme hatası: {e}")
        return pd.DataFrame()


def calculate_stock_data(ticker_info: dict, close_series: pd.Series) -> dict | None:
    """Tek bir hisse için tüm değişim metriklerini hesaplar."""
    if close_series is None or close_series.dropna().empty:
        return None

    series = close_series.dropna()
    if len(series) < 2:
        return None

    # İndeksleri sırala
    series = series.sort_index()

    last_price = float(series.iloc[-1])

    def price_n_days_ago(n: int) -> float | None:
        cutoff = series.index[-1] - timedelta(days=n)
        past = series[series.index <= cutoff]
        return float(past.iloc[-1]) if not past.empty else None

    price_1d  = price_n_days_ago(1)    # dün
    price_7d  = price_n_days_ago(7)    # ~1 hafta
    price_30d = price_n_days_ago(30)   # ~1 ay
    price_365d = price_n_days_ago(365) # ~1 yıl

    return {
        "ticker":         ticker_info["ticker"],
        "name":           ticker_info.get("name", ""),
        "sector":         ticker_info.get("sector", "Diğer"),
        "indices":        ticker_info.get("indices", []),
        "market_cap_tl":  ticker_info.get("market_cap_tl"),
        "price":          round(last_price, 2),
        "change_daily":   pct_change(last_price, price_1d),
        "change_weekly":  pct_change(last_price, price_7d),
        "change_monthly": pct_change(last_price, price_30d),
        "change_yearly":  pct_change(last_price, price_365d),
    }


def main():
    log.info("=" * 60)
    log.info("BIST fiyat verisi çekiliyor")
    log.info("=" * 60)
    t_start = time.time()

    tickers_data, tickers_updated_at = load_tickers()
    if not tickers_data:
        log.error("Ticker listesi boş")
        sys.exit(1)

    # .IS uzantısını ekle
    all_tickers_is = [t["ticker"] + ".IS" for t in tickers_data]
    ticker_map = {t["ticker"]: t for t in tickers_data}

    log.info(f"Toplam {len(all_tickers_is)} hisse için veri çekilecek")

    # Batch'lere böl
    batches = [
        all_tickers_is[i : i + BATCH_SIZE]
        for i in range(0, len(all_tickers_is), BATCH_SIZE)
    ]
    log.info(f"{len(batches)} batch × ~{BATCH_SIZE} hisse")

    all_close: dict[str, pd.Series] = {}
    skipped_tickers = []

    for i, batch in enumerate(batches, 1):
        log.info(f"Batch {i}/{len(batches)}: {len(batch)} hisse indiriliyor...")
        df = fetch_prices_batch(batch)

        if df.empty:
            log.warning(f"Batch {i} boş döndü, atlandı")
            skipped_tickers.extend(t.replace(".IS", "") for t in batch)
            time.sleep(BATCH_DELAY)
            continue

        for ticker_is in batch:
            ticker = ticker_is.replace(".IS", "")
            if ticker_is in df.columns:
                series = df[ticker_is].dropna()
                if not series.empty:
                    all_close[ticker] = series
                else:
                    skipped_tickers.append(ticker)
            else:
                skipped_tickers.append(ticker)

        if i < len(batches):
            time.sleep(BATCH_DELAY)

    log.info(f"Veri alınan: {len(all_close)}, atlanan: {len(skipped_tickers)}")
    if skipped_tickers:
        log.info(f"Atlanan hisseler: {', '.join(skipped_tickers[:20])}" +
                 (f" ...+{len(skipped_tickers)-20}" if len(skipped_tickers) > 20 else ""))

    # Sonuçları derle
    stocks_out = []
    no_data_count = 0

    for t_info in tickers_data:
        ticker = t_info["ticker"]
        if ticker in all_close:
            result = calculate_stock_data(t_info, all_close[ticker])
            if result:
                stocks_out.append(result)
                continue
        # Veri yok → gri hücre
        stocks_out.append({
            "ticker":         ticker,
            "name":           t_info.get("name", ""),
            "sector":         t_info.get("sector", "Diğer"),
            "indices":        t_info.get("indices", []),
            "market_cap_tl":  t_info.get("market_cap_tl"),
            "price":          None,
            "change_daily":   None,
            "change_weekly":  None,
            "change_monthly": None,
            "change_yearly":  None,
        })
        no_data_count += 1

    # Market cap'e göre sırala (büyükten küçüğe)
    stocks_out.sort(
        key=lambda x: x["market_cap_tl"] if x["market_cap_tl"] else 0,
        reverse=True
    )

    elapsed = round(time.time() - t_start, 1)
    log.info(f"Tamamlandı: {len(stocks_out)} hisse, {no_data_count} verimsiz, {elapsed}s")

    # Kaydet
    output = {
        "updated_at":        datetime.now(TRT).isoformat(),
        "tickers_updated_at": tickers_updated_at,
        "total":             len(stocks_out),
        "with_data":         len(stocks_out) - no_data_count,
        "without_data":      no_data_count,
        "elapsed_seconds":   elapsed,
        "stocks":            stocks_out,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, separators=(",", ":"))

    log.info(f"Kaydedildi: {OUTPUT_PATH}")
    print(f"OK: {len(stocks_out)} hisse, {no_data_count} verimsiz, {elapsed}s")


if __name__ == "__main__":
    main()
