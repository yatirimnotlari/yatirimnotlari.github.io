#!/usr/bin/env python3
from __future__ import annotations
"""
BIST 100 endeks ağırlıklarını hesaplar ve data/bist100-agirliklari.json'a kaydeder.

Metodoloji:
  1. BİST resmi CSV → BIST 100 üyelik listesi (100 hisse, günlük güncelleme)
  2. İş Yatırım → piyasa değeri (mn TL) + halka açıklık oranı (%)
  3. Serbest dolaşım piyasa değeri = mcap × halka_açıklık / 100
  4. Ağırlık = ff_mcap / Σff_mcap × 100, %10 cap (BIST 100 resmi limiti)

Fallback: Scraping başarısız olursa önceki başarılı JSON kullanılır.
Çalışma sıklığı: Günde 1 kez (sabah, BIST açılmadan önce).
"""

import json
import logging
import re
import sys
import time
from datetime import datetime
from io import StringIO
from pathlib import Path

import pandas as pd
import pytz
import requests
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

TRT = pytz.timezone("Europe/Istanbul")
ROOT = Path(__file__).parent.parent
OUTPUT_PATH = ROOT / "data" / "bist100-agirliklari.json"

CAP_PCT = 10.0  # BIST 100 resmi ağırlık sınırı

BIST_CSV_URL = "https://www.borsaistanbul.com/datum/hisse_endeks_ds.csv"
ISYATIRIM_URL = (
    "https://www.isyatirim.com.tr/tr-tr/analiz/hisse/Sayfalar/"
    "Temel-Degerler-Ve-Oranlar.aspx"
)

HEADERS = {
    "User-Agent": (
        "YatirimNotlari/1.0 - bilgi amacli kisisel proje "
        "(github.com/yatirimnotlari/yatirimnotlari.github.io)"
    ),
    "Accept-Language": "tr-TR,tr;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


# ─── Kaynak 1: BİST CSV ──────────────────────────────────────────────────────

def fetch_bist100_members() -> set[str]:
    """BİST resmi üyelik CSV'sinden BIST 100 hisse listesini döndürür."""
    log.info(f"BİST üyelik CSV çekiliyor: {BIST_CSV_URL}")
    resp = requests.get(BIST_CSV_URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()

    df = pd.read_csv(StringIO(resp.content.decode("utf-8")), sep=";", skiprows=1)
    members = set(
        df[df["INDEX CODE"] == "XU100"]["CONSTITUENT CODE"]
        .str.replace(r"\.E$", "", regex=True)
    )
    tarih = df[df["INDEX CODE"] == "XU100"]["DATE(DD/MM/YYYY)"].iloc[0] if len(df) else "?"
    log.info(f"BIST 100 üye sayısı: {len(members)} (BİST verisi tarihi: {tarih})")
    return members


# ─── Kaynak 2: İş Yatırım ────────────────────────────────────────────────────

def fetch_isyatirim_data() -> dict[str, dict]:
    """
    İş Yatırım tablo sayfasından piyasa değeri + halka açıklık oranı çeker.
    Döndürür: {ticker: {name, mcap_tl, halka_aciklik, ff_mcap_tl}}
    """
    log.info(f"İş Yatırım çekiliyor (1.5s gecikme): {ISYATIRIM_URL}")
    time.sleep(1.5)

    resp = requests.get(ISYATIRIM_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    resp.encoding = "utf-8"

    soup = BeautifulSoup(resp.text, "lxml")
    tables = soup.find_all("table")
    if not tables:
        raise ValueError("İş Yatırım sayfasında tablo bulunamadı")

    best_table = max(tables, key=lambda t: len(t.find_all("tr")))
    rows = best_table.find_all("tr")

    if len(rows) < 50:
        raise ValueError(f"İş Yatırım tablosu beklenenin altında: {len(rows)} satır")

    # Sütun indeksleri
    col_names = [
        th.get_text(strip=True).lower()
        for th in rows[0].find_all(["th", "td"])
    ]
    log.info(f"İş Yatırım sütunları: {col_names}")

    # TL piyasa değeri sütunu — "tl" geçen piyasa değeri
    mc_i = next(
        (i for i, h in enumerate(col_names) if "piyasa değeri" in h and "tl" in h),
        None,
    )
    ha_i = next(
        (i for i, h in enumerate(col_names) if "açıklık" in h),
        None,
    )
    name_i = next(
        (i for i, h in enumerate(col_names) if any(k in h for k in ["hisse adı", "şirket", " adı"])),
        1,  # genellikle 2. sütun
    )

    if ha_i is None or mc_i is None:
        raise ValueError(
            f"Gerekli sütunlar bulunamadı — halka_aciklik={ha_i}, mcap={mc_i}. "
            f"Mevcut: {col_names}"
        )

    log.info(f"Sütun indeksleri — ad:{name_i} mcap_tl:{mc_i} halka_aciklik:{ha_i}")

    result: dict[str, dict] = {}
    for row in rows[1:]:
        cells = row.find_all(["td", "th"])
        if len(cells) < max(mc_i, ha_i) + 1:
            continue

        def ct(idx: int) -> str:
            if idx >= len(cells):
                return ""
            link = cells[idx].find("a")
            return (link or cells[idx]).get_text(strip=True)

        ticker = re.sub(r"\.IS$", "", ct(0).upper()).strip()
        if not ticker or len(ticker) < 2 or not ticker[0].isalpha():
            continue

        try:
            mcap = float(ct(mc_i).replace(".", "").replace(",", ".")) * 1_000_000
            ha = float(ct(ha_i).replace(",", "."))
        except ValueError:
            continue

        if mcap <= 0 or not (0 < ha <= 100):
            continue

        result[ticker] = {
            "name":          ct(name_i),
            "mcap_tl":       mcap,
            "halka_aciklik": ha,
            "ff_mcap_tl":    mcap * ha / 100,
        }

    log.info(f"İş Yatırım: {len(result)} hisse ayrıştırıldı")
    return result


# ─── Ağırlık hesabı ──────────────────────────────────────────────────────────

def apply_cap(
    weights: dict[str, float], cap: float = CAP_PCT
) -> tuple[dict[str, float], list[str]]:
    """
    Ağırlıklara iteratif cap uygular: aşım miktarı cap altındaki hisselere
    oransal dağıtılır, toplam %100 korunur.
    """
    w = dict(weights)
    capped_set: set[str] = set()

    for _ in range(20):
        over = {k: v for k, v in w.items() if v > cap}
        if not over:
            break
        capped_set |= set(over.keys())
        excess = sum(v - cap for v in over.values())
        for k in over:
            w[k] = cap
        under = {k: v for k, v in w.items() if v < cap}
        tot = sum(under.values())
        if tot == 0:
            break
        for k in under:
            w[k] += excess * w[k] / tot

    return w, sorted(capped_set)


# ─── Fallback & persistence ──────────────────────────────────────────────────

def load_previous() -> dict:
    if OUTPUT_PATH.exists():
        try:
            with open(OUTPUT_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log.warning(f"Önceki veri okunamadı: {e}")
    return {}


# ─── Ana akış ─────────────────────────────────────────────────────────────────

def main() -> None:
    log.info("=" * 60)
    log.info("BIST 100 ağırlık hesabı başladı")
    log.info("=" * 60)

    now = datetime.now(TRT)
    prev_data = load_previous()
    prev_hisseler = {h["ticker"]: h for h in prev_data.get("hisseler", [])}

    fallback_aktif = False
    fallback_aciklama: str | None = None
    hisseler: list[dict] = []
    cap_list: list[str] = []
    total_ff = 0.0
    son_basarili_cekim = now.isoformat()

    try:
        # 1. Üyelik listesi
        members = fetch_bist100_members()
        if len(members) < 90:
            raise ValueError(f"BIST 100 üye sayısı beklenenden az: {len(members)}")

        # 2. İş Yatırım verisi
        isyat = fetch_isyatirim_data()

        # 3. Sadece BIST 100 üyeleri
        bist100_pairs = [(t, isyat[t]) for t in members if t in isyat]
        eksik = sorted(t for t in members if t not in isyat)
        if eksik:
            log.warning(f"İş Yatırım'da bulunmayan üyeler ({len(eksik)}): {', '.join(eksik)}")

        if len(bist100_pairs) < 90:
            raise ValueError(
                f"Yeterli BIST 100 verisi yok: {len(bist100_pairs)}/100"
            )

        # 4. Ham ağırlıklar (free float normalize)
        total_ff = sum(v["ff_mcap_tl"] for _, v in bist100_pairs)
        raw_weights = {
            t: v["ff_mcap_tl"] / total_ff * 100 for t, v in bist100_pairs
        }
        max_raw = max(raw_weights.values())

        # 5. %10 cap uygula
        capped_weights, cap_list = apply_cap(raw_weights)
        total_capped = sum(capped_weights.values())

        log.info(f"Toplam FF piyasa değeri: {total_ff / 1e12:.2f} trilyon TL")
        log.info(f"Ham max ağırlık: {max_raw:.2f}%")
        log.info(f"Cap uygulanan ({CAP_PCT}%): {cap_list if cap_list else 'yok'}")
        log.info(f"Cap sonrası toplam ağırlık: {total_capped:.4f}% (100 olmalı)")

        # 6. Hisse listesi — ağırlığa göre sıralı
        hisseler = sorted(
            [
                {
                    "ticker":         t,
                    "name":           info["name"],
                    "agirlik":        round(capped_weights[t], 4),
                    "mcap_tl":        round(info["mcap_tl"]),
                    "halka_aciklik":  info["halka_aciklik"],
                    "ff_mcap_tl":     round(info["ff_mcap_tl"]),
                }
                for t, info in bist100_pairs
            ],
            key=lambda x: x["agirlik"],
            reverse=True,
        )

        log.info(
            "En büyük 5 ağırlık: "
            + str([(h["ticker"], f"{h['agirlik']:.2f}%") for h in hisseler[:5]])
        )

        # 7. Halka açıklık oranı değişimlerini logla
        ha_degisimler = []
        for h in hisseler:
            prev = prev_hisseler.get(h["ticker"])
            if prev:
                fark = abs(h["halka_aciklik"] - prev["halka_aciklik"])
                if fark >= 1.0:
                    ha_degisimler.append(
                        f"{h['ticker']}: {prev['halka_aciklik']:.1f}% → {h['halka_aciklik']:.1f}%"
                    )
        if ha_degisimler:
            log.info(
                f"Halka açıklık oranı değişimleri ({len(ha_degisimler)}): "
                + ", ".join(ha_degisimler[:10])
                + (f" ...+{len(ha_degisimler)-10}" if len(ha_degisimler) > 10 else "")
            )
        else:
            log.info("Halka açıklık oranı değişikliği yok (≥1 puan eşiği)")

        son_basarili_cekim = now.isoformat()

    except Exception as exc:
        log.error(f"Çekim hatası: {exc}")

        if prev_data.get("hisseler"):
            log.warning("FALLBACK: önceki başarılı veri kullanılıyor")
            fallback_aktif = True
            fallback_aciklama = (
                f"Güncel veri alınamadı: {exc}. "
                f"Önceki başarılı çekim kullanılıyor."
            )
            hisseler = prev_data["hisseler"]
            cap_list = prev_data.get("cap_uygulanan", [])
            total_ff = prev_data.get("toplam_ff_piyasa_degeri_tl", 0.0)
            son_basarili_cekim = (
                prev_data.get("agirlik_metodoloji", {}).get("son_basarili_cekim", "?")
            )
            log.info(f"Fallback: {len(hisseler)} hisse, son başarılı: {son_basarili_cekim}")
        else:
            log.error("Önceki veri de bulunamadı, çıkılıyor")
            sys.exit(1)

    # 8. Kaydet
    output = {
        "updated_at": now.isoformat(),
        "agirlik_metodoloji": {
            "kaynak": (
                f"BİST CSV + İş Yatırım (halka açıklık × piyasa değeri, %{int(CAP_PCT)} cap)"
            ),
            "son_basarili_cekim": son_basarili_cekim,
            "fallback_aktif":     fallback_aktif,
            "fallback_aciklama":  fallback_aciklama,
        },
        "toplam_ff_piyasa_degeri_tl": round(total_ff),
        "cap_uygulanan":  cap_list,
        "hisse_sayisi":   len(hisseler),
        "hisseler":       hisseler,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    log.info(f"Kaydedildi: {OUTPUT_PATH} ({len(hisseler)} hisse)")
    status = "FALLBACK" if fallback_aktif else "OK"
    print(
        f"{status}: {len(hisseler)} hisse, "
        f"cap={cap_list or 'yok'}, "
        f"ff_mcap={total_ff / 1e12:.1f}T TL"
    )


if __name__ == "__main__":
    main()
