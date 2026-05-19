#!/usr/bin/env python3
from __future__ import annotations
"""
BIST 100 endeks etkisi hesaplar ve public/data/bist-endeks-etkisi.json'a kaydeder.

Metodoloji:
  1. data/bist100-agirliklari.json → ağırlıklar (fetch_endeks_agirliklari.py çıktısı)
  2. yfinance → her hissenin günlük / haftalık / aylık fiyat değişimi
  3. Katkı (bps) = ağırlık_yüzde × değişim_yüzde  (yüzde puan × yüzde = bps değil ama
     piyasada kabul gören "katkı" tanımı: ağırlık × değişim, birimsiz; biz bunu
     "etki endeksi puanına katkı (yaklaşık bps)" olarak etiketliyoruz)
  4. Doğrulama: Σkatki vs XU100.IS değişimi (fark genellikle <10 bps)

Çalışma sıklığı: 15 dakikada bir (BIST açık saatlerinde), fetch-prices.yml içinden.
"""

import json
import logging
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytz
import yfinance as yf

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

TRT = pytz.timezone("Europe/Istanbul")
ROOT = Path(__file__).parent.parent
WEIGHTS_PATH = ROOT / "data" / "bist100-agirliklari.json"
TICKERS_PATH = ROOT / "data" / "bist-tickers.json"
OUTPUT_PATH = ROOT / "public" / "data" / "bist-endeks-etkisi.json"

# yfinance parametreleri
YF_DELAY = 0.3  # saniye — çok hızlı istekten kaçınmak için
BIST_INDEX_TICKER = "XU100.IS"


# ─── Sektör verisi yükleme ───────────────────────────────────────────────────

def load_sector_map() -> dict[str, str]:
    """data/bist-tickers.json'dan {ticker: sektor} sözlüğü döndürür."""
    if not TICKERS_PATH.exists():
        log.warning(f"Ticker dosyası bulunamadı: {TICKERS_PATH} — sektör bilgisi yok")
        return {}
    try:
        with open(TICKERS_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return {t["ticker"]: t.get("sector", "Diğer") for t in data.get("tickers", [])}
    except Exception as e:
        log.warning(f"Ticker dosyası okunamadı: {e}")
        return {}


# ─── Ağırlık verisi yükleme ──────────────────────────────────────────────────

def load_weights() -> dict:
    """data/bist100-agirliklari.json'u yükler. Yoksa çıkılır."""
    if not WEIGHTS_PATH.exists():
        log.error(f"Ağırlık dosyası bulunamadı: {WEIGHTS_PATH}")
        log.error("Önce fetch_endeks_agirliklari.py çalıştırın.")
        sys.exit(1)
    with open(WEIGHTS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    hisseler = data.get("hisseler", [])
    if not hisseler:
        log.error("Ağırlık dosyasında hisse verisi yok.")
        sys.exit(1)
    log.info(
        f"Ağırlık dosyası yüklendi: {len(hisseler)} hisse, "
        f"güncelleme: {data.get('updated_at', '?')}"
    )
    return data


# ─── yfinance fiyat çekimi ────────────────────────────────────────────────────

def _pct_change(series, offset_days: int) -> float | None:
    """
    Bir fiyat serisinden offset_days öncesine göre yüzde değişim hesaplar.
    Günlük (1), haftalık (7), aylık (30) için kullanılır.
    """
    if series is None or len(series) < 2:
        return None
    now_price = float(series.iloc[-1])
    if now_price == 0:
        return None

    cutoff = series.index[-1] - timedelta(days=offset_days)
    past = series[series.index <= cutoff]
    if past.empty:
        return None
    past_price = float(past.iloc[-1])
    if past_price == 0:
        return None
    return (now_price - past_price) / past_price * 100  # % cinsinden


def fetch_price_changes(tickers: list[str]) -> dict[str, dict]:
    """
    yfinance ile her hisse için günlük/haftalık/aylık değişim yüzdesi çeker.
    Döndürür: {ticker: {daily, weekly, monthly}}  (None = veri yok)
    """
    yf_tickers = [f"{t}.IS" for t in tickers]
    log.info(f"yfinance: {len(yf_tickers)} hisse çekiliyor (period=2mo)…")

    # Tek seferde toplu indirme — daha az API isteği
    raw = yf.download(
        yf_tickers,
        period="2mo",
        interval="1d",
        auto_adjust=True,
        progress=False,
        threads=True,
    )

    close = raw["Close"] if "Close" in raw.columns else raw

    result: dict[str, dict] = {}
    for t in tickers:
        col = f"{t}.IS"
        if col not in close.columns:
            result[t] = {"daily": None, "weekly": None, "monthly": None}
            continue
        s = close[col].dropna()
        result[t] = {
            "daily":   _pct_change(s, 1),
            "weekly":  _pct_change(s, 7),
            "monthly": _pct_change(s, 30),
        }

    found = sum(1 for v in result.values() if v["daily"] is not None)
    log.info(f"Fiyat verisi: {found}/{len(tickers)} hisse için günlük değişim var")
    return result


def fetch_index_change() -> dict:
    """XU100.IS için günlük/haftalık/aylık değişimi çeker."""
    time.sleep(YF_DELAY)
    log.info(f"XU100.IS endeks değişimi çekiliyor…")
    try:
        raw = yf.download(
            BIST_INDEX_TICKER,
            period="2mo",
            interval="1d",
            auto_adjust=True,
            progress=False,
        )
        s = raw["Close"].dropna() if "Close" in raw.columns else raw.iloc[:, 0].dropna()
        return {
            "daily":   _pct_change(s, 1),
            "weekly":  _pct_change(s, 7),
            "monthly": _pct_change(s, 30),
        }
    except Exception as e:
        log.warning(f"XU100.IS çekilemedi: {e}")
        return {"daily": None, "weekly": None, "monthly": None}


# ─── Katkı hesabı ─────────────────────────────────────────────────────────────

def calculate_contributions(
    hisseler: list[dict],
    price_changes: dict[str, dict],
    period: str,  # "daily" | "weekly" | "monthly"
) -> list[dict]:
    """
    Her hisse için endeks katkısını hesaplar.
    katki = agirlik_yuzde × degisim_yuzde (yaklaşık bps cinsinden ifade edilir)
    """
    result = []
    for h in hisseler:
        t = h["ticker"]
        agirlik = h["agirlik"]  # % cinsinden (ör. 8.43)
        degisim = (price_changes.get(t) or {}).get(period)

        if degisim is not None:
            katki = round(agirlik * degisim / 100, 4)  # bps olarak
        else:
            katki = None

        result.append({
            "ticker":  t,
            "name":    h["name"],
            "agirlik": agirlik,
            "degisim": round(degisim, 4) if degisim is not None else None,
            "katki":   katki,
        })

    # katkı büyüklüğüne göre sırala (None en sona)
    result.sort(
        key=lambda x: (x["katki"] is None, -(x["katki"] or 0))
    )
    return result


def sector_contributions(
    sector_map: dict[str, str],
    contributions: list[dict],
) -> list[dict]:
    """
    Sektör bazlı toplam katkıları hesaplar.
    sector_map: {ticker: sektor_adı}  (bist-tickers.json'dan)
    """
    agg: dict[str, dict] = {}

    for item in contributions:
        t = item["ticker"]
        sektor = sector_map.get(t, "Diğer")
        if sektor not in agg:
            agg[sektor] = {"sektor": sektor, "katki": 0.0, "hisse_sayisi": 0, "eksik": 0}
        if item["katki"] is not None:
            agg[sektor]["katki"] += item["katki"]
            agg[sektor]["hisse_sayisi"] += 1
        else:
            agg[sektor]["eksik"] += 1

    result = sorted(agg.values(), key=lambda x: abs(x["katki"]), reverse=True)
    for s in result:
        s["katki"] = round(s["katki"], 4)
    return result


# ─── Fallback ─────────────────────────────────────────────────────────────────

def load_previous_output() -> dict:
    if OUTPUT_PATH.exists():
        try:
            with open(OUTPUT_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log.warning(f"Önceki çıktı okunamadı: {e}")
    return {}


# ─── Ana akış ─────────────────────────────────────────────────────────────────

def main() -> None:
    log.info("=" * 60)
    log.info("BIST 100 endeks etkisi hesabı başladı")
    log.info("=" * 60)

    now = datetime.now(TRT)

    # 1. Ağırlıkları ve sektör haritasını yükle
    weights_data = load_weights()
    hisseler = weights_data["hisseler"]
    agirlik_metodoloji = weights_data.get("agirlik_metodoloji", {})
    tickers = [h["ticker"] for h in hisseler]

    sector_map = load_sector_map()
    log.info(f"Sektör haritası: {len(sector_map)} ticker")

    # 2. Fiyat değişimlerini çek
    try:
        price_changes = fetch_price_changes(tickers)
    except Exception as e:
        log.error(f"Fiyat çekme hatası: {e}")
        prev = load_previous_output()
        if prev:
            log.warning("FALLBACK: önceki çıktı kullanılıyor")
            prev["updated_at"] = now.isoformat()
            prev["fallback_aktif"] = True
            prev["fallback_aciklama"] = f"Fiyat verisi alınamadı: {e}"
            OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
                json.dump(prev, f, ensure_ascii=False, indent=2)
            print(f"FALLBACK: önceki veri kullanıldı — {e}")
        else:
            log.error("Önceki çıktı da yok, çıkılıyor")
            sys.exit(1)
        return

    # 3. Endeks değişimini çek (doğrulama için)
    index_change = fetch_index_change()

    # 4. Her dönem için katkıları hesapla
    periods = ["daily", "weekly", "monthly"]
    contributions: dict[str, list[dict]] = {}
    endeks_katki_toplam: dict[str, float | None] = {}
    dogrulama_farki: dict[str, float | None] = {}

    for period in periods:
        contribs = calculate_contributions(hisseler, price_changes, period)
        contributions[period] = contribs

        toplam = sum(c["katki"] for c in contribs if c["katki"] is not None)
        endeks_katki_toplam[period] = round(toplam, 4)

        # Doğrulama: Σkatki ≈ endeks_degisim
        # katki = agirlik% × degisim% / 100 → birim: yüzde puan (endeks değişimiyle aynı)
        # fark = (Σkatki - endeks_degisim) × 100 → bps cinsinden
        idx = index_change.get(period)
        if idx is not None:
            dogrulama_farki[period] = round((toplam - idx) * 100, 2)
        else:
            dogrulama_farki[period] = None

    # 5. Sektör katkıları
    sektor_katkisi: dict[str, list[dict]] = {}
    for period in periods:
        sektor_katkisi[period] = sector_contributions(sector_map, contributions[period])

    # 6. Loglama
    for period, label in [("daily", "Günlük"), ("weekly", "Haftalık"), ("monthly", "Aylık")]:
        idx_val = index_change.get(period)
        toplam_val = endeks_katki_toplam.get(period)
        fark_val = dogrulama_farki.get(period)
        log.info(
            f"{label}: XU100={idx_val:.2f}% | "
            f"Σkatkı={toplam_val:.2f} | "
            f"Fark={fark_val:.2f} bps"
            if all(v is not None for v in [idx_val, toplam_val, fark_val])
            else f"{label}: veri eksik"
        )
        top3_pos = [c for c in contributions[period] if (c["katki"] or 0) > 0][:3]
        top3_neg = sorted(
            [c for c in contributions[period] if (c["katki"] or 0) < 0],
            key=lambda x: x["katki"]
        )[:3]
        if top3_pos:
            log.info(
                f"  En çok artı: "
                + str([(c["ticker"], f"{c['katki']:+.3f}") for c in top3_pos])
            )
        if top3_neg:
            log.info(
                f"  En çok eksi: "
                + str([(c["ticker"], f"{c['katki']:+.3f}") for c in top3_neg])
            )

    # 7. Kaydet
    output = {
        "updated_at": now.isoformat(),
        "fallback_aktif": False,
        "fallback_aciklama": None,
        "agirlik_metodoloji": agirlik_metodoloji,
        "endeks_degisim": {
            "daily":   round(index_change["daily"], 4) if index_change["daily"] is not None else None,
            "weekly":  round(index_change["weekly"], 4) if index_change["weekly"] is not None else None,
            "monthly": round(index_change["monthly"], 4) if index_change["monthly"] is not None else None,
        },
        "endeks_katki_toplam": endeks_katki_toplam,
        "dogrulama_farki_bps": dogrulama_farki,
        "hisse_sayisi": len(hisseler),
        "stocks": {
            period: contributions[period]
            for period in periods
        },
        "sektor_katki": sektor_katkisi,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    daily_idx = index_change.get("daily")
    log.info(f"Kaydedildi: {OUTPUT_PATH}")
    print(
        f"OK: {len(hisseler)} hisse, "
        f"XU100={daily_idx:.2f}% (günlük), "
        f"Σkatkı={endeks_katki_toplam['daily']:.2f}"
        if daily_idx is not None
        else f"OK: {len(hisseler)} hisse, günlük endeks verisi yok"
    )


if __name__ == "__main__":
    main()
