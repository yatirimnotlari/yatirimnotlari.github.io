#!/usr/bin/env python3
from __future__ import annotations
"""
BIST hisse listesini çeker ve data/bist-tickers.json'a kaydeder.
Kaynaklar:
  Birincil: İş Yatırım (ticker + sektör + piyasa değeri)
  Endeks üyelikleri: İş Yatırım filtrelenmiş sayfalar, yedek Bigpara
  Fallback: Son başarılı bist-tickers.json
"""

import requests
from bs4 import BeautifulSoup
import json
import os
import sys
import logging
import time
import re
from datetime import datetime
from pathlib import Path
import pytz

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

TRT = pytz.timezone("Europe/Istanbul")
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "tr-TR,tr;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

ROOT = Path(__file__).parent.parent
OUTPUT_PATH = ROOT / "data" / "bist-tickers.json"

# ─── Sektör eşleştirme tablosu ───────────────────────────────────────────────
SECTOR_MAP = {
    # Finans
    "Bankacılık": "Finans",
    "Banka": "Finans",
    "Sigorta": "Finans",
    "Aracı Kurumlar": "Finans",
    "Aracı Kurum": "Finans",
    "Yatırım Ortaklıkları": "Finans",
    "Yatırım Ortaklığı": "Finans",
    "Girişim Sermayesi": "Finans",
    "Holding ve Yatırım Şirketleri": "Finans",
    "Holding": "Finans",
    "Finansal Kiralama": "Finans",
    "Faktoring": "Finans",
    "Varlık Yönetimi": "Finans",
    "Finansman": "Finans",
    # Gayrimenkul (GYO'lar Finans'tan ayrı)
    "GYO": "Gayrimenkul",
    "Gayrimenkul Yatırım Ortaklığı": "Gayrimenkul",
    "Gayrimenkul Yatırım": "Gayrimenkul",
    "Gayrimenkul": "Gayrimenkul",
    # Sanayi
    "Metal Ana Sanayi": "Sanayi",
    "Metal Ana": "Sanayi",
    "Metal Eşya, Makine": "Sanayi",
    "Metal Eşya": "Sanayi",
    "Makine": "Sanayi",
    "Kimya, Petrol, Plastik": "Sanayi",
    "Kimya": "Sanayi",
    "Petrokimya": "Sanayi",
    "Plastik": "Sanayi",
    "Kauçuk": "Sanayi",
    "Boya": "Sanayi",
    "Gıda": "Sanayi",
    "İçecek": "Sanayi",
    "Gıda ve İçecek": "Sanayi",
    "Tekstil, Deri": "Sanayi",
    "Tekstil": "Sanayi",
    "Deri": "Sanayi",
    "Konfeksiyon": "Sanayi",
    "İplik": "Sanayi",
    "Otomotiv": "Sanayi",
    "Otomotiv ve Yedek": "Sanayi",
    "Beyaz Eşya": "Sanayi",
    "Küçük Ev Aletleri": "Sanayi",
    "Elektrikli Ev Aletleri": "Sanayi",
    "Dayanıklı Tüketim": "Sanayi",
    "Orman Ürünleri, Mobilya": "Sanayi",
    "Orman": "Sanayi",
    "Mobilya": "Sanayi",
    "Kağıt": "Sanayi",
    "Ambalaj": "Sanayi",
    "Cam": "Sanayi",
    "Çimento": "Sanayi",
    "Seramik": "Sanayi",
    "Porselen": "Sanayi",
    "İlaç": "Sanayi",
    "Eczacılık": "Sanayi",
    "Medikal": "Sanayi",
    "Tıbbi Cihaz": "Sanayi",
    "Demir": "Sanayi",
    "Çelik": "Sanayi",
    "Demir-Çelik": "Sanayi",
    "Döküm": "Sanayi",
    "Alüminyum": "Sanayi",
    "Çinko": "Sanayi",
    "Yapı Malzemeleri": "Sanayi",
    "Tarım": "Sanayi",
    "Tarımsal": "Sanayi",
    "Hayvancılık": "Sanayi",
    "Kuyumculuk": "Sanayi",
    "Mücevher": "Sanayi",
    "Savunma": "Teknoloji",
    "Havacılık ve Savunma": "Teknoloji",
    # Enerji
    "Elektrik": "Enerji",
    "Petrol ve Doğalgaz": "Enerji",
    "Petrol": "Enerji",
    "Doğalgaz": "Enerji",
    "Enerji": "Enerji",
    "Yenilenebilir Enerji": "Enerji",
    # Hizmetler
    "Telekomünikasyon": "Hizmetler",
    "Telekom": "Hizmetler",
    "Haberleşme": "Hizmetler",
    "Perakende Ticaret": "Hizmetler",
    "Toptan Ticaret": "Hizmetler",
    "Ticaret": "Hizmetler",
    "Ulaştırma": "Hizmetler",
    "Havacılık": "Hizmetler",
    "Turizm": "Hizmetler",
    "Otelcilik": "Hizmetler",
    "Konaklama": "Hizmetler",
    "Eğitim": "Hizmetler",
    "Sağlık": "Hizmetler",
    "Medya": "Hizmetler",
    "Yayıncılık": "Hizmetler",
    "Spor": "Hizmetler",
    "Lojistik": "Hizmetler",
    "Nakliye": "Hizmetler",
    "Denizcilik": "Hizmetler",
    "Su": "Hizmetler",
    # Teknoloji
    "Bilişim": "Teknoloji",
    "Teknoloji": "Teknoloji",
    "Yazılım": "Teknoloji",
    "E-Ticaret": "Teknoloji",
    "Bilgisayar": "Teknoloji",
    "Elektronik": "Teknoloji",
    "Yarı İletken": "Teknoloji",
    # Madencilik
    "Madencilik": "Madencilik",
    "Altın": "Madencilik",
    "Maden": "Madencilik",
    "Gümüş": "Madencilik",
    "Bakır": "Madencilik",
    "Kömür": "Madencilik",
    "Bor": "Madencilik",
    # İnşaat
    "İnşaat": "İnşaat ve Bayındırlık",
    "Bayındırlık": "İnşaat ve Bayındırlık",
    "Çelik Yapı": "İnşaat ve Bayındırlık",
    "Prefabrik": "İnşaat ve Bayındırlık",
    "Altyapı": "İnşaat ve Bayındırlık",
}


def map_sector(raw: str) -> str:
    if not raw:
        return "Diğer"
    raw = raw.strip()
    if raw in SECTOR_MAP:
        return SECTOR_MAP[raw]
    for key, val in SECTOR_MAP.items():
        if key.lower() in raw.lower():
            return val
    return raw  # bilinmeyen sektörü olduğu gibi döndür


def fetch_with_retry(url: str, max_retries: int = 3, delay: float = 2.0) -> requests.Response:
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            return resp
        except Exception as e:
            log.warning(f"Deneme {attempt}/{max_retries} başarısız: {e}")
            if attempt < max_retries:
                time.sleep(delay)
    raise RuntimeError(f"{url} adresine {max_retries} denemede de ulaşılamadı")


# ─── Kaynak 1: İş Yatırım — tüm hisseler ────────────────────────────────────

def fetch_isyatirim_all() -> list[dict]:
    url = (
        "https://www.isyatirim.com.tr/tr-tr/analiz/hisse/Sayfalar/"
        "Temel-Degerler-Ve-Oranlar.aspx"
    )
    log.info(f"İş Yatırım ana sayfa: {url}")
    resp = fetch_with_retry(url)
    resp.encoding = "utf-8"
    return _parse_isyatirim_table(resp.text)


def _parse_isyatirim_table(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")

    # Tüm tabloları dene, en fazla satırı olan büyük data tablosunu al
    tables = soup.find_all("table")
    best_table = None
    best_count = 0
    for t in tables:
        rows = t.find_all("tr")
        if len(rows) > best_count:
            best_count = len(rows)
            best_table = t

    if not best_table or best_count < 5:
        raise ValueError(f"Yeterli veri içeren tablo bulunamadı (max {best_count} satır)")

    # Başlıkları bul
    header_row = best_table.find("tr")
    headers = [th.get_text(strip=True).lower() for th in header_row.find_all(["th", "td"])]
    log.info(f"Tablo başlıkları: {headers}")

    # Sütun indekslerini bul
    def col_idx(*keywords):
        for i, h in enumerate(headers):
            if any(k in h for k in keywords):
                return i
        return None

    idx_ticker = col_idx("kod", "ticker", "sembol")
    idx_name   = col_idx("hisse adı", "şirket", "unvan", "ad")
    idx_sector = col_idx("sektör", "sector")
    idx_mcap   = col_idx("piyasa değeri", "piyasa d")

    log.info(f"Sütun indeksleri — ticker:{idx_ticker} ad:{idx_name} sektör:{idx_sector} mcap:{idx_mcap}")

    stocks = []
    for row in best_table.find_all("tr")[1:]:  # başlığı atla
        cells = row.find_all(["td", "th"])
        if len(cells) < 3:
            continue

        def cell_text(idx):
            if idx is None or idx >= len(cells):
                return ""
            # Link varsa link metnini al
            link = cells[idx].find("a")
            return (link or cells[idx]).get_text(strip=True)

        ticker = cell_text(idx_ticker) if idx_ticker is not None else cell_text(0)
        ticker = re.sub(r"\.IS$", "", ticker.upper()).strip()
        if not ticker or len(ticker) < 2 or not ticker[0].isalpha():
            continue

        name   = cell_text(idx_name)   if idx_name   is not None else cell_text(1)
        sector_raw = cell_text(idx_sector) if idx_sector is not None else ""

        # Piyasa değeri: "1.234,56" → float (mn TL → TL)
        market_cap_tl = None
        if idx_mcap is not None:
            raw_mc = cell_text(idx_mcap).replace(".", "").replace(",", ".")
            try:
                market_cap_tl = float(raw_mc) * 1_000_000  # mn TL → TL
            except ValueError:
                pass

        stocks.append({
            "ticker":       ticker,
            "name":         name,
            "sector":       map_sector(sector_raw),
            "sector_raw":   sector_raw,
            "market_cap_tl": market_cap_tl,
            "indices":      [],
        })

    log.info(f"İş Yatırım'dan {len(stocks)} hisse ayrıştırıldı")
    return stocks


# ─── Kaynak 2: Endeks üyelikleri ─────────────────────────────────────────────

# ─── BIST30 sabit liste (her çeyrek Borsa İstanbul tarafından güncellenir) ────
# Web kaynakları JS render gerektirdiğinden, market-cap sıralamasıyla birlikte
# bu seed liste endeks üyeliğini belirlemek için kullanılır.
# Kaynak güncellendikçe bu listeyi de güncelleyin.
BIST30_SEED: set[str] = {
    "AKBNK", "ARCLK", "ASELS", "BIMAS", "EKGYO", "ENKAI", "EREGL",
    "FROTO", "GARAN", "HALKB", "ISCTR", "KCHOL", "KRDMD", "KOZAL",
    "PETKM", "PGSUS", "SAHOL", "SASA", "SISE", "TAVHL", "TCELL",
    "THYAO", "TKFEN", "TOASO", "TTKOM", "TUPRS", "VAKBN", "VESTL",
    "YKBNK", "ZOREN",
}

# Kaç hissenin "gerçekçi" sayıldığı (üstü = tüm lista döndü, geçersiz)
INDEX_MAX_SIZE = {"BIST30": 60, "BIST50": 90, "BIST100": 180}


def build_index_members_from_market_cap(
    stocks: list[dict],
    bist30_seed: set[str],
    n50: int = 50,
    n100: int = 100,
) -> dict[str, set[str]]:
    """
    BIST30: seed listesini kullanır.
    BIST50/100: tüm hisse listesini piyasa değerine göre sıralar,
    ilk n50/n100 hisseyi alır (+ seed hisseleri dahil).
    """
    sorted_by_mcap = sorted(
        [s for s in stocks if s.get("market_cap_tl")],
        key=lambda x: x["market_cap_tl"],
        reverse=True,
    )
    top50 = {s["ticker"] for s in sorted_by_mcap[:n50]}
    top100 = {s["ticker"] for s in sorted_by_mcap[:n100]}

    bist30 = bist30_seed & {s["ticker"] for s in stocks}  # sadece listede olanlar
    bist50 = bist30 | top50
    bist100 = bist50 | top100

    log.info(f"Piyasa değeri bazlı endeks: BIST30={len(bist30)}, BIST50={len(bist50)}, BIST100={len(bist100)}")
    return {"BIST30": bist30, "BIST50": bist50, "BIST100": bist100}


# ─── Diff hesaplama ───────────────────────────────────────────────────────────

def compute_diff(old_tickers: list[dict], new_tickers: list[dict]) -> list[str]:
    """Eski ve yeni listeler arasındaki farkları döndürür (log için)."""
    old_map = {t["ticker"]: t for t in old_tickers}
    new_map = {t["ticker"]: t for t in new_tickers}

    changes = []
    added   = set(new_map) - set(old_map)
    removed = set(old_map) - set(new_map)

    for t in sorted(added):
        changes.append(f"YENİ: {t} ({new_map[t].get('name', '')})")
    for t in sorted(removed):
        changes.append(f"ÇIKARILDI: {t} ({old_map[t].get('name', '')})")

    for t in set(old_map) & set(new_map):
        old_s = old_map[t].get("sector", "")
        new_s = new_map[t].get("sector", "")
        if old_s != new_s:
            changes.append(f"SEKTÖR DEĞİŞTİ: {t} ({old_s} → {new_s})")

        old_i = set(old_map[t].get("indices", []))
        new_i = set(new_map[t].get("indices", []))
        if old_i != new_i:
            changes.append(f"ENDEKS DEĞİŞTİ: {t} ({old_i} → {new_i})")

    return changes


# ─── Ana akış ─────────────────────────────────────────────────────────────────

def load_existing() -> list[dict]:
    if OUTPUT_PATH.exists():
        try:
            with open(OUTPUT_PATH, encoding="utf-8") as f:
                data = json.load(f)
                return data.get("tickers", [])
        except Exception:
            pass
    return []


def main():
    log.info("=" * 60)
    log.info("BIST ticker listesi güncelleniyor")
    log.info("=" * 60)

    # 1. Mevcut listeyi yükle (fallback için)
    existing = load_existing()
    existing_map = {t["ticker"]: t for t in existing}

    # 2. Tüm hisseleri İş Yatırım'dan çek
    stocks = []
    try:
        stocks = fetch_isyatirim_all()
    except Exception as e:
        log.error(f"İş Yatırım başarısız: {e}")
        if existing:
            log.warning("Son başarılı liste korunuyor.")
            print("FALLBACK: son liste kullanıldı")
            sys.exit(0)
        else:
            log.error("Hiç kayıt yok, çıkılıyor.")
            sys.exit(1)

    if not stocks:
        log.error("İş Yatırım'dan hiç hisse alınamadı")
        sys.exit(1)

    # 3. Endeks üyeliklerini belirle (piyasa değeri sıralaması + seed liste)
    max_size = INDEX_MAX_SIZE
    index_members: dict[str, set[str]] = {}

    # Önce önceki JSON'dan mevcut üyelikleri kontrol et
    prev_bist30 = {t["ticker"] for t in existing if "BIST30" in t.get("indices", [])}
    prev_is_valid = 5 <= len(prev_bist30) <= max_size["BIST30"]

    if prev_is_valid:
        # Önceki liste geçerliyse koru
        log.info(f"Önceki endeks verileri geçerli: BIST30={len(prev_bist30)}")
        for index_name in ["BIST30", "BIST50", "BIST100"]:
            index_members[index_name] = {
                t["ticker"] for t in existing if index_name in t.get("indices", [])
            }
    else:
        # Önceki liste bozuk veya yok → piyasa değeri + seed
        log.warning("Önceki endeks verileri geçersiz, piyasa değeri sıralaması kullanılıyor")
        index_members = build_index_members_from_market_cap(stocks, BIST30_SEED)

    # 4. Her hisseye endeks etiketlerini ata
    ticker_map = {s["ticker"]: s for s in stocks}
    for index_name, members in index_members.items():
        for ticker in members:
            if ticker in ticker_map:
                if index_name not in ticker_map[ticker]["indices"]:
                    ticker_map[ticker]["indices"].append(index_name)

    # BIST30 ⊂ BIST50 ⊂ BIST100 mantığını uygula
    for s in stocks:
        indices = set(s["indices"])
        if "BIST30" in indices:
            indices |= {"BIST50", "BIST100"}
        elif "BIST50" in indices:
            indices |= {"BIST100"}
        s["indices"] = sorted(indices)

    # 5. Diff hesapla ve logla
    changes = compute_diff(existing, stocks)
    if changes:
        log.info(f"Değişiklikler ({len(changes)}):")
        for c in changes:
            log.info(f"  {c}")
        print(f"CHANGES: {'; '.join(changes[:10])}")
    else:
        log.info("Değişiklik yok")
        print("NO_CHANGES")

    # 6. Kaydet
    output = {
        "updated_at": datetime.now(TRT).isoformat(),
        "total": len(stocks),
        "index_counts": {k: len(v) for k, v in index_members.items()},
        "tickers": stocks,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    log.info(f"Kaydedildi: {OUTPUT_PATH} ({len(stocks)} hisse)")

    # Sektör dağılımı özeti
    sector_count: dict[str, int] = {}
    for s in stocks:
        sector_count[s["sector"]] = sector_count.get(s["sector"], 0) + 1
    log.info("Sektör dağılımı: " + ", ".join(f"{k}:{v}" for k, v in sorted(sector_count.items())))


if __name__ == "__main__":
    main()
