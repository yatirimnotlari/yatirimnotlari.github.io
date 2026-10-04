#!/usr/bin/env python3
"""
Magic Formula haritası verisini hesaplar → public/data/magic-formula.json

Girdi (data/magic-formula/, fetch_mali_tablolar.py ve fetch_tufe.py üretir)
  sirketler.json, endeksler.json, tufe.json, mali-tablolar/{KOD}.json, arsiv.json

Her şirket için ucuzluk (FVÖK/FD) ve kalite (ROIC) hesaplanır. Sıralama ve
medyan eşikleri sayfada, kullanıcının seçtiği evrene göre tarayıcıda yapılır.
Formüller ve TMS 29 notu için scripts/mf_lib.py dosyasına bakın.

Çeyreklik arşiv: her çalıştırmada baskın bilanço dönemi için ucuzluk/kalite
değerleri arsiv.json'a yazılır. Baskın dönem değiştiğinde (ör. 2026/6 → 2026/9)
önceki dönemin son hali sabit kalır; sayfa "kadran değiştirenler" listesini
bununla kurar.
"""
from __future__ import annotations

import json
import logging
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent))
from mf_lib import (  # noqa: E402
    HOLDING_SEKTORU,
    baskin_donem,
    ceyrek_farki,
    donem_sirasi,
    en_son_donem,
    kapsam_disi_nedeni,
    kullanilacak_donem,
    magic_formula_sirala,
    sirket_metrikleri,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)

TRT = ZoneInfo("Europe/Istanbul")
ROOT = Path(__file__).parent.parent
VERI_DIR = ROOT / "data" / "magic-formula"
TABLO_DIR = VERI_DIR / "mali-tablolar"
ARSIV_PATH = VERI_DIR / "arsiv.json"
OUTPUT_PATH = ROOT / "public" / "data" / "magic-formula.json"

ARSIV_DONEM_SAYISI = 8
ENDEKS_ADLARI = {"XU030": "BIST 30", "XU050": "BIST 50", "XU100": "BIST 100"}
MILYON = 1_000_000


def json_oku(path: Path, varsayilan):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return varsayilan


def mn(deger: float | None) -> float | None:
    """TL → milyon TL (1 ondalık)."""
    return None if deger is None else round(deger / MILYON, 1)


def yuvarla(deger: float | None, basamak: int = 2) -> float | None:
    return None if deger is None else round(deger, basamak)


def guncel_tufe_ayi(tufe_endeks: dict, fiyat_tarihi: str | None) -> str | None:
    """Fiyat tarihindeki ayı (yoksa en yakın önceki yayımlanmış ayı) döndürür."""
    if not tufe_endeks:
        return None
    hedef = (fiyat_tarihi or "")[:7] or max(tufe_endeks)
    adaylar = [a for a in tufe_endeks if a <= hedef]
    return max(adaylar) if adaylar else None


def main() -> None:
    liste = json_oku(VERI_DIR / "sirketler.json", None)
    if not liste:
        log.error("data/magic-formula/sirketler.json yok — önce fetch_mali_tablolar.py çalıştırın")
        sys.exit(1)
    endeks_veri = json_oku(VERI_DIR / "endeksler.json", {})
    tufe = json_oku(VERI_DIR / "tufe.json", {})
    tufe_endeks = tufe.get("endeks", {})
    fiyat_tarihi = liste.get("kaynak_uretim")
    tufe_ayi = guncel_tufe_ayi(tufe_endeks, fiyat_tarihi)
    if not tufe_ayi:
        log.warning("TÜFE verisi yok — FVÖK fiyat tarihine taşınmayacak")

    uyelik: dict[str, list[str]] = {}
    for kod in ENDEKS_ADLARI:
        for t in endeks_veri.get(kod, []):
            uyelik.setdefault(t, []).append(kod)

    hisseler, disarida = [], []
    kapsam_disi = Counter()
    for c in liste["sirketler"]:
        t = c["ticker"]
        neden = kapsam_disi_nedeni(c.get("fin_group"), c.get("sector_code"))
        if neden:
            kapsam_disi[neden] += 1
            continue
        temel = {
            "ticker": t,
            "ad": c.get("name") or t,
            "sektor": c.get("sector") or "Diğer",
            "sektor_kodu": c.get("sector_code"),
        }
        tablo = json_oku(TABLO_DIR / f"{t}.json", None)
        if not tablo or not tablo.get("donemler"):
            disarida.append({**temel, "neden": "Mali tablo verisi alınamadı"})
            continue
        donemler = tablo["donemler"]
        son = c.get("last_period") if c.get("last_period") in donemler else en_son_donem(donemler)
        if not son:
            disarida.append({**temel, "neden": "Bilanço dönemi yok"})
            continue
        kullanilan, son_eksik = kullanilacak_donem(donemler, son)
        if not kullanilan:
            disarida.append({**temel, "donem": son, "neden": f"Son mali tablo ({son}) kaynakta eksik"})
            continue
        piyasa_degeri = (c.get("market_cap_mn_try") or 0) * MILYON
        m = sirket_metrikleri(donemler, kullanilan, piyasa_degeri, tufe_endeks, tufe_ayi)
        if son_eksik:
            m["bayraklar"].append("son_donem_eksik")
        son = kullanilan
        if m.get("hata"):
            disarida.append({**temel, "donem": son, "neden": m["hata"]})
            continue
        hisseler.append({
            **temel,
            "endeksler": sorted(uyelik.get(t, [])),
            "holding": c.get("sector_code") == HOLDING_SEKTORU,
            "donem": son,
            "ttm": m["ttm_yontemi"],
            "piyasa_degeri": mn(piyasa_degeri),
            "fd": mn(m["fd"]),
            "net_borc": mn(m["net_borc"]),
            "fvok": mn(m["fvok"]),
            "satis": mn(m.get("satis")),
            "favok": mn(m.get("favok")),
            "sermaye": mn(m["sermaye"]),
            "nis": mn(m["nis"]),
            "net_duran": mn(m["net_duran"]),
            "ey": yuvarla(m["ey"]),
            "roic": yuvarla(m["roic"]),
            "fd_favok": yuvarla(m.get("fd_favok")),
            "bayraklar": m["bayraklar"],
        })

    # Bilanço dönemi baskın dönemin 2+ çeyrek gerisindeyse karşılaştırma dışı
    baskin = baskin_donem(h["donem"] for h in hisseler)
    guncel = []
    for h in hisseler:
        fark = ceyrek_farki(h["donem"], baskin) if baskin else 0
        if fark >= 2:
            disarida.append({k: h[k] for k in ("ticker", "ad", "sektor", "sektor_kodu", "donem")}
                            | {"neden": f"Bilanço dönemi eski ({h['donem']})"})
            continue
        if fark == 1:
            h["bayraklar"].append("onceki_donem")
        guncel.append(h)
    hisseler = sorted(guncel, key=lambda h: h["ticker"])
    disarida.sort(key=lambda h: h["ticker"])

    # Çeyreklik arşiv
    arsiv = json_oku(ARSIV_PATH, {})
    if baskin:
        arsiv[baskin] = {
            "tarih": fiyat_tarihi,
            "aciklama": f"{baskin} bilançoları, {str(fiyat_tarihi)[:10]} fiyatları",
            "hisseler": {h["ticker"]: [h["ey"], h["roic"]] for h in hisseler},
        }
        anahtarlar = sorted(arsiv, key=donem_sirasi)[-ARSIV_DONEM_SAYISI:]
        arsiv = {k: arsiv[k] for k in anahtarlar}
        ARSIV_PATH.write_text(json.dumps(arsiv, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    onceki = None
    if baskin:
        eskiler = [k for k in arsiv if donem_sirasi(k) < donem_sirasi(baskin)]
        if eskiler:
            k = max(eskiler, key=donem_sirasi)
            onceki = {"donem": k, **arsiv[k]}

    # Özet (log + sayfa notu)
    ilk = magic_formula_sirala([h for h in hisseler if not h["holding"] and "zarar" not in h["bayraklar"]])
    log.info(f"Hesaplanan: {len(hisseler)} şirket | dışarıda: {len(disarida)} | kapsam dışı: {sum(kapsam_disi.values())}")
    log.info(f"Baskın dönem: {baskin} | TÜFE ayı: {tufe_ayi} | fiyat: {fiyat_tarihi}")
    log.info("İlk 10 (tümü, holding ve zarar edenler hariç): " + ", ".join(f"{h['ticker']}" for h in ilk[:10]))

    cikti = {
        "updated_at": None,  # aşağıda, içerik değiştiyse doldurulur
        "fiyat_tarihi": fiyat_tarihi,
        "baskin_donem": baskin,
        "tufe_ayi": tufe_ayi,
        "endeks_tarihi": endeks_veri.get("tarih"),
        "kaynak": {
            "mali_tablo": "Veri: KAP/Borsa İstanbul, derleyen BilancoVeri.com",
            "fiyat": "BilancoVeri (en az 15 dk gecikmeli)",
            "endeks": "Borsa İstanbul endeks üyelik listesi",
            "tufe": "TCMB / TÜİK",
        },
        "ozet": {
            "toplam_sirket": len(liste["sirketler"]),
            "hesaplanan": len(hisseler),
            "disarida": len(disarida),
            "kapsam_disi": dict(kapsam_disi.most_common()),
        },
        "hisseler": hisseler,
        "disarida": disarida,
        "onceki": onceki,
    }

    # Yalnızca içerik değiştiyse yaz (gereksiz commit/yayın olmasın)
    eski = json_oku(OUTPUT_PATH, {})
    eski_icerik = {k: v for k, v in eski.items() if k != "updated_at"}
    yeni_icerik = {k: v for k, v in cikti.items() if k != "updated_at"}
    if eski_icerik == json.loads(json.dumps(yeni_icerik, ensure_ascii=False)):
        log.info("Çıktı değişmedi — dosya yazılmadı")
        print("DEĞİŞİKLİK YOK")
        return
    cikti["updated_at"] = datetime.now(TRT).isoformat(timespec="seconds")
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(cikti, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    log.info(f"Kaydedildi: {OUTPUT_PATH} ({OUTPUT_PATH.stat().st_size // 1024} KB)")
    print(f"OK: {len(hisseler)} şirket, baskın dönem {baskin}")


if __name__ == "__main__":
    main()
