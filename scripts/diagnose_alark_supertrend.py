#!/usr/bin/env python3
"""ALARK için ham ve temettü ayarlı SuperTrend zincirini karşılaştırır."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import yfinance as yf

from fetch_weekly_supertrend import calculate_supertrend, extract_daily, weekly_ohlc


ROOT = Path(__file__).parent.parent
OUTPUT_PATH = ROOT / "public" / "data" / "alark-supertrend-diagnostic.json"
SYMBOL = "ALARK.IS"


def serialize(frame: pd.DataFrame) -> list[dict]:
    rows: list[dict] = []
    for index, row in frame.tail(16).iterrows():
        rows.append(
            {
                "week_end": index.date().isoformat(),
                "open": round(float(row["Open"]), 4),
                "high": round(float(row["High"]), 4),
                "low": round(float(row["Low"]), 4),
                "close": round(float(row["Close"]), 4),
                "atr": round(float(row["ATR"]), 4),
                "up": round(float(row["Up"]), 4),
                "down": round(float(row["Down"]), 4),
                "trend": int(row["Trend"]),
                "buy_signal": bool(row["BuySignal"]),
                "supertrend": round(float(row["SuperTrend"]), 4),
            }
        )
    return rows


def calculate(auto_adjust: bool) -> list[dict]:
    raw = yf.download(
        SYMBOL,
        period="10y",
        interval="1d",
        auto_adjust=auto_adjust,
        repair=True,
        actions=True,
        progress=False,
        threads=False,
        group_by="column",
    )
    daily = extract_daily(raw, SYMBOL, [SYMBOL])
    return serialize(calculate_supertrend(weekly_ohlc(daily)))


def main() -> None:
    result = {
        "ticker": "ALARK",
        "history_period": "10y",
        "dividend_adjusted": calculate(True),
        "splits_only": calculate(False),
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
