#!/usr/bin/env python3
"""
Magic Formula aracı için şirket listesini ve mali tabloları çeker.

Kaynaklar
  • BilancoVeri açık API (KAP / Borsa İstanbul verisi, derleyen BilancoVeri.com)
      /api/v1/sirketler.json        → şirket listesi, fiyat, piyasa değeri, sektör, son dönem
      /api/v1/hisse/{kod}.json      → dönem dönem mali tablolar (kümülatif)
  • Borsa İstanbul endeks üyelik CSV'si → BIST 30 / 50 / 100

Artımlı çalışır: bir şirketin detayı yalnızca yeni bilanço açıkladığında (son
dönem değiştiğinde), önbellekte hiç yoksa ya da son kontrolün üzerinden
YENILEME_GUN gün geçtiyse indirilir. İlk çalıştırma tüm şirketleri tek tek ve
istekler arasında bekleyerek indirir (~10 dk).

Çıktılar (data/magic-formula/)
  sirketler.json              — şirket listesinin anlık görüntüsü
  endeksler.json              — BIST 30/50/100 üyelikleri
  mali-tablolar/{KOD}.json    — şirket başına gerekli kalemler, son 8 dönem
  kontrol-gunlugu.json        — şirket başına son kontrol zamanı
"""
from __future__ import annotations

import csv
import io
import json
import logging
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

sys.path.insert(0, str(Path(__file__).parent))
from mf_lib import GEREKLI_KODLAR, donem_eksik_mi, gecerli_donemler, kapsam_disi_nedeni, sayi  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)

TRT = ZoneInfo("Europe/Istanbul")
ROOT = Path(__file__).parent.parent
VERI_DIR = ROOT / "data" / "magic-formula"
TABLO_DIR = VERI_DIR / "mali-tablolar"
SIRKETLER_PATH = VERI_DIR / "sirketler.json"
ENDEKS_PATH = VERI_DIR / "endeksler.json"
GUNLUK_PATH = VERI_DIR / "kontrol-gunlugu.json"

API = "https://bilancoveri.com/api/v1/"
BIST_CSV_URL = "https://www.borsaistanbul.com/datum/hisse_endeks_ds.csv"
HEADERS = {
    "User-Agent": "YatirimNotlari/1.0 (+https://yatirimnotlari.github.io; magic formula araci)",
    "Accept": "application/json, text/csv;q=0.9, */*;q=0.5",
    "Accept-Language": "tr-TR,tr;q=0.9",
}

SAKLANACAK_DONEM = 8          # şirket başına son 8 dönem
YENILEME_GUN = 30             # değişmeyen şirketler bu kadar günde bir yeniden kontrol edilir
GUNLUK_YENILEME_SINIRI = 40   # tek çalıştırmada en fazla bu kadar "rutin" yenileme
ISTEK_ARASI_BEKLEME = 0.8     # saniye — kaynağı yormamak için
ENDEKSLER = ("XU030", "XU050", "XU100")


def oturum() -> requests.Session:
    s = requests.Session()
    s.headers.update(HEADERS)
    return s


def getir(s: requests.Session, url: str, deneme: int = 3, json_mu: bool = True):
    son_hata = None
    for i in range(1, deneme + 1):
        try:
            r = s.get(url, timeout=45)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.json() if json_mu else r.content
        except Exception as exc:  # ağ hatası → tekrar dene
            son_hata = exc
            time.sleep(2 * i)
    raise RuntimeError(f"{url}: {son_hata}")


def json_oku(path: Path, varsayilan):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return varsayilan


def json_yaz(path: Path, veri, girinti: int | None = 1) -> bool:
    """Dosyayı yalnızca içerik değiştiyse yazar. Değiştiyse True döner."""
    metin = json.dumps(veri, ensure_ascii=False, indent=girinti, sort_keys=False) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == metin:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(metin, encoding="utf-8")
    return True


# ─── Şirket listesi ───────────────────────────────────────────────────────────

ALANLAR = ("ticker", "name", "sector", "sector_code", "fin_group", "price",
           "market_cap_mn_try", "ev_ebitda", "float_ratio", "last_period")


def sirket_listesi_cek(s: requests.Session) -> dict | None:
    veri = getir(s, API + "sirketler.json")
    sirketler = (veri or {}).get("companies") or []
    if len(sirketler) < 300:
        raise ValueError(f"Şirket listesi beklenenden kısa: {len(sirketler)}")
    return {
        "kaynak": "BilancoVeri açık API — Veri: KAP/Borsa İstanbul, derleyen BilancoVeri.com",
        "kaynak_uretim": veri.get("generated_at"),
        "sirketler": [{k: c.get(k) for k in ALANLAR} for c in sirketler],
    }


# ─── Endeks üyelikleri ────────────────────────────────────────────────────────

def endeksler_cek(s: requests.Session) -> dict:
    icerik = getir(s, BIST_CSV_URL, json_mu=False)
    metin = icerik.decode("utf-8-sig", errors="replace")
    satirlar = metin.splitlines()
    baslik_i = next(i for i, sat in enumerate(satirlar) if "INDEX CODE" in sat)
    okuyucu = csv.DictReader(io.StringIO("\n".join(satirlar[baslik_i:])), delimiter=";")
    uyeler: dict[str, set[str]] = {e: set() for e in ENDEKSLER}
    tarih = None
    for sat in okuyucu:
        kod = (sat.get("INDEX CODE") or "").strip()
        if kod in uyeler:
            uyeler[kod].add((sat.get("CONSTITUENT CODE") or "").strip().removesuffix(".E"))
            tarih = tarih or (sat.get("DATE(DD/MM/YYYY)") or "").strip()
    if len(uyeler["XU100"]) < 90 or len(uyeler["XU030"]) < 25:
        raise ValueError(f"Endeks üyelikleri eksik: { {k: len(v) for k, v in uyeler.items()} }")
    return {
        "kaynak": "Borsa İstanbul endeks üyelik listesi",
        "tarih": tarih,
        **{k: sorted(v) for k, v in uyeler.items()},
    }


# ─── Mali tablolar ────────────────────────────────────────────────────────────

def tablo_sadelestir(detay: dict) -> dict | None:
    """API yanıtından gereken kalemleri ve son dönemleri alır."""
    donemler = detay.get("periods") or {}
    if not isinstance(donemler, dict) or not donemler:
        return None
    secili = gecerli_donemler(donemler.keys())[-SAKLANACAK_DONEM:]
    sade = {}
    for d in secili:
        satir = {}
        for kod in GEREKLI_KODLAR:
            v = sayi((donemler.get(d) or {}).get(kod))
            if v is not None:
                satir[kod] = int(round(v))
        sade[d] = satir
    sirket = detay.get("company") or {}
    return {
        "ticker": sirket.get("ticker"),
        "ad": sirket.get("name"),
        "son_donem": sirket.get("last_period") or (secili[-1] if secili else None),
        "kaynak": "Veri: KAP/Borsa İstanbul, derleyen BilancoVeri.com",
        "donemler": sade,
    }


def main() -> None:
    log.info("=" * 60)
    log.info("Magic Formula: şirket listesi ve mali tablolar")
    log.info("=" * 60)
    s = oturum()
    simdi = datetime.now(TRT)

    # 1) Şirket listesi
    try:
        liste = sirket_listesi_cek(s)
        json_yaz(SIRKETLER_PATH, liste)
        log.info(f"Şirket listesi: {len(liste['sirketler'])} şirket (kaynak üretim: {liste['kaynak_uretim']})")
    except Exception as exc:
        log.error(f"Şirket listesi alınamadı: {exc}")
        liste = json_oku(SIRKETLER_PATH, None)
        if not liste:
            sys.exit(1)
        log.warning("Önceki şirket listesiyle devam ediliyor (fiyatlar eski kalabilir)")

    # 2) Endeks üyelikleri
    try:
        endeks = endeksler_cek(s)
        json_yaz(ENDEKS_PATH, endeks)
        log.info(f"Endeksler: XU030={len(endeks['XU030'])} XU050={len(endeks['XU050'])} XU100={len(endeks['XU100'])} ({endeks['tarih']})")
    except Exception as exc:
        log.error(f"Endeks üyelikleri alınamadı, önceki dosya korunuyor: {exc}")

    # 3) Mali tablolar (artımlı)
    gunluk = json_oku(GUNLUK_PATH, {})
    kapsam = [c for c in liste["sirketler"] if not kapsam_disi_nedeni(c.get("fin_group"), c.get("sector_code"))]
    log.info(f"Kapsamdaki şirket: {len(kapsam)} / {len(liste['sirketler'])}")

    yeni, degisen, eksik, rutin = [], [], [], []
    for c in kapsam:
        t = c["ticker"]
        dosya = TABLO_DIR / f"{t}.json"
        onbellek = json_oku(dosya, None)
        if onbellek is None:
            yeni.append(t)
        elif onbellek.get("son_donem") != c.get("last_period"):
            degisen.append(t)
        elif donem_eksik_mi(onbellek.get("donemler") or {}, onbellek.get("son_donem") or ""):
            eksik.append(t)  # kaynakta yarım işlenmiş son dönem: düzeltilmiş mi diye her gün bak
        else:
            son_kontrol = gunluk.get(t)
            try:
                eski = (simdi - datetime.fromisoformat(son_kontrol)) > timedelta(days=YENILEME_GUN)
            except Exception:
                eski = True
            if eski:
                rutin.append(t)
    rutin.sort(key=lambda t: gunluk.get(t) or "")
    rutin = rutin[:GUNLUK_YENILEME_SINIRI]
    sira = yeni + degisen + eksik[:GUNLUK_YENILEME_SINIRI] + rutin
    log.info(f"İndirilecek: yeni={len(yeni)} yeni_bilanço={len(degisen)} eksik_dönem={len(eksik)} rutin_yenileme={len(rutin)}")

    basarili = hatali = guncellenen = 0
    for i, t in enumerate(sira, 1):
        try:
            detay = getir(s, API + f"hisse/{t.lower()}.json")
            if not detay:
                log.warning(f"{t}: detay bulunamadı (404)")
                hatali += 1
                continue
            sade = tablo_sadelestir(detay)
            if not sade or not sade["donemler"]:
                log.warning(f"{t}: dönem verisi yok")
                hatali += 1
                continue
            sade["ticker"] = t
            degisti = json_yaz(TABLO_DIR / f"{t}.json", sade, girinti=None)
            if degisti:
                guncellenen += 1
            # Eksik dönem kontrolünde veri değişmediyse günlüğe yazma (her gün commit olmasın)
            if degisti or t not in eksik:
                gunluk[t] = simdi.isoformat(timespec="seconds")
            basarili += 1
        except Exception as exc:
            log.warning(f"{t}: {exc}")
            hatali += 1
        if i % 50 == 0:
            log.info(f"  {i}/{len(sira)} işlendi")
        time.sleep(ISTEK_ARASI_BEKLEME)

    json_yaz(GUNLUK_PATH, dict(sorted(gunluk.items())))
    log.info(f"Bitti: başarılı={basarili} güncellenen_dosya={guncellenen} hatalı={hatali}")
    print(f"OK: {basarili} şirket kontrol edildi, {guncellenen} dosya güncellendi, {hatali} hata")


if __name__ == "__main__":
    main()
