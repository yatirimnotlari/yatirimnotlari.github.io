#!/usr/bin/env python3
"""
TÜFE (tüketici fiyat endeksi) aylık değişimlerini TCMB'nin sayfasından çeker
ve data/magic-formula/tufe.json dosyasına yazar.

Kaynak: TCMB › İstatistikler › Enflasyon Verileri › Tüketici Fiyatları
(TÜİK verisi; 2026'dan itibaren 2025=100 bazında yayımlanıyor). Aylık
değişimler zincirlenerek baz yılından bağımsız bir endeks kurulur.

Magic Formula aracında yalnızca FVÖK'ü bilanço tarihinden fiyat tarihine
taşımak için kullanılır. Çekim başarısız olursa önceki dosya korunur.
"""
from __future__ import annotations

import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent))
from mf_lib import tufe_endeksi_kur  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)

TRT = ZoneInfo("Europe/Istanbul")
ROOT = Path(__file__).parent.parent
OUTPUT_PATH = ROOT / "data" / "magic-formula" / "tufe.json"
TCMB_URL = (
    "https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/Main+Menu/"
    "Istatistikler/Enflasyon+Verileri/Tuketici+Fiyatlari"
)
HEADERS = {
    "User-Agent": "YatirimNotlari/1.0 (+https://yatirimnotlari.github.io; kisisel bilgi amacli proje)",
    "Accept-Language": "tr-TR,tr;q=0.9",
}


def ayristir(html: str) -> dict[str, float]:
    """Tablo satırlarını ('08-2026', yıllık %, aylık %) okur → {'2026-08': aylık %}."""
    soup = BeautifulSoup(html, "lxml")
    aylik: dict[str, float] = {}
    for tr in soup.find_all("tr"):
        hucreler = [td.get_text(" ", strip=True) for td in tr.find_all(["td", "th"])]
        if len(hucreler) < 3 or not re.fullmatch(r"\d{2}-\d{4}", hucreler[0]):
            continue
        ay, yil = hucreler[0].split("-")
        try:
            aylik[f"{yil}-{ay}"] = float(hucreler[2].replace(",", "."))
        except ValueError:
            continue
    return aylik


def main() -> None:
    onceki = {}
    if OUTPUT_PATH.exists():
        onceki = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))

    try:
        r = requests.get(TCMB_URL, headers=HEADERS, timeout=30)
        r.raise_for_status()
        aylik = ayristir(r.text)
        if len(aylik) < 100:
            raise ValueError(f"Beklenenden az satır: {len(aylik)}")
        son_ay = max(aylik)
        # Son veri 4 aydan eski olmamalı
        simdi = datetime.now(TRT)
        fark = (simdi.year * 12 + simdi.month) - (int(son_ay[:4]) * 12 + int(son_ay[5:]))
        if fark > 4:
            raise ValueError(f"TÜFE verisi eski görünüyor: son ay {son_ay}")
    except Exception as exc:  # ağ/ayrıştırma hatası → önceki veriyle devam
        log.error(f"TÜFE çekilemedi: {exc}")
        if onceki:
            log.warning("Önceki TÜFE dosyası korunuyor")
            return
        sys.exit(1)

    # Önceki dosyadaki aylarla birleştir (kaynak sayfa eski ayları kısaltırsa diye)
    birlesik = dict(onceki.get("aylik_degisim", {}))
    birlesik.update(aylik)
    endeks = tufe_endeksi_kur(birlesik)

    cikti = {
        "updated_at": datetime.now(TRT).isoformat(timespec="seconds"),
        "kaynak": "TCMB / TÜİK — Tüketici Fiyatları (aylık % değişim)",
        "kaynak_url": TCMB_URL,
        "son_ay": max(endeks),
        "aciklama": "endeks: aylık değişimlerin zincirlenmesiyle kurulmuştur (ilk ay öncesi = 100); oranlar baz yılından bağımsızdır.",
        "aylik_degisim": dict(sorted(birlesik.items())),
        "endeks": {k: round(v, 6) for k, v in endeks.items()},
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(cikti, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    log.info(f"TÜFE kaydedildi: {len(endeks)} ay, son ay {cikti['son_ay']}")


if __name__ == "__main__":
    main()
