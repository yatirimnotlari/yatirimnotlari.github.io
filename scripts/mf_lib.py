"""
Magic Formula hesap çekirdeği — saf fonksiyonlar (ağ erişimi yok, test edilebilir).

Tanımlar (Joel Greenblatt, "The Little Book That Beats the Market" uyarlaması):
  FVÖK (EBIT)   = Brüt kâr − pazarlama − genel yönetim − Ar-Ge giderleri
                  (BilancoVeri / İş Yatırım kalem kodu 3H "Net Faaliyet Kar/Zararı").
                  Kur farkı, vade farkı gibi "esas faaliyetlerden diğer gelir/gider"
                  kalemleri ve parasal kazanç/kayıp dışarıda kalır.
  FD (EV)       = Piyasa değeri + finansal borçlar − nakit − KV finansal yatırımlar
                  + azınlık payları
  Ucuzluk (EY)  = FVÖK / FD
  Sermaye       = max(net işletme sermayesi, 0) + maddi duran varlıklar
                  + kullanım hakkı varlıkları + yatırım amaçlı gayrimenkuller
  Kalite (ROIC) = FVÖK / Sermaye

Veri kalitesi eşikleri (yöntemin anlamlı olmadığı durumlar sıralama dışı):
  • FVÖK satışların %90'ından büyükse (gelirin çoğu yatırım/değerleme geliri)
  • Yatırılan sermaye toplam varlıkların %2'sinden küçükse (ROIC anlamsızlaşır)

Enflasyon muhasebesi (TMS 29) ve veri kaynağının dönem kuralı
--------------------------------------------------------------
BilancoVeri her şirketin geçmiş dönemlerini son bilançonun satın alma gücüyle
tutuyor (doğrulandı: ASELS 6A/2025 hasılatı raporda 53,7 milyar TL, veride
70,96 milyar TL = 53,7 × TÜFE Haz26/Haz25; FROTO 2025 yılı hasılatı raporda
831 milyar TL, veride 978,4 milyar TL = 831 × TÜFE Haz26/Ara25). Bu yüzden son
12 ay = cari dönem + önceki mali yıl − önceki yılın aynı dönemi, ek düzeltme
gerekmez. TÜFE yalnızca FVÖK'ü bilanço tarihinden fiyat tarihine taşımak için
(ucuzluk oranında) kullanılır.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Iterable

# ─── Kalem kodları ────────────────────────────────────────────────────────────

KOD_SATIS = "3C"
KOD_BRUT_KAR = "3D"
KOD_PAZARLAMA = "3DA"
KOD_GENEL_YONETIM = "3DB"
KOD_ARGE = "3DC"
KOD_FAALIYET_KARI = "3DF"   # esas faaliyet kârı (diğer gelir/giderler dahil)
KOD_FVOK = "3H"             # Net Faaliyet Kar/Zararı = 3D + 3DA + 3DB + 3DC
KOD_NET_KAR = "3L"
KOD_AMORTISMAN = "4B"
KOD_DONEN = "1A"
KOD_NAKIT = "1AA"
KOD_KV_FIN_YAT = "1AB"
KOD_DURAN = "1AK"
KOD_MDV = "1BG"             # maddi duran varlıklar
KOD_KULLANIM_HAKKI = "1BFAA"
KOD_YATIRIM_GAYRIMENKUL = "1BF"
KOD_TOPLAM_VARLIK = "1BL"
KOD_KVY = "2A"              # kısa vadeli yükümlülükler
KOD_KV_FIN_BORC = "2AA"
KOD_UVY = "2B"
KOD_UV_FIN_BORC = "2BA"
KOD_OZKAYNAK = "2N"
KOD_ANA_OZKAYNAK = "2O"
KOD_AZINLIK = "2ODA"

# Önbellekte saklanan kalemler (hesap + doğrulama için gerekenler)
GEREKLI_KODLAR = (
    KOD_SATIS, KOD_BRUT_KAR, KOD_PAZARLAMA, KOD_GENEL_YONETIM, KOD_ARGE,
    "3DD", "3DE", KOD_FAALIYET_KARI, KOD_FVOK, KOD_NET_KAR, KOD_AMORTISMAN,
    KOD_DONEN, KOD_NAKIT, KOD_KV_FIN_YAT, KOD_DURAN, KOD_MDV, KOD_KULLANIM_HAKKI,
    "1BH", "1BGA", "1BF", "1BD", KOD_TOPLAM_VARLIK,
    KOD_KVY, KOD_KV_FIN_BORC, KOD_UVY, KOD_UV_FIN_BORC, KOD_OZKAYNAK,
    KOD_ANA_OZKAYNAK, KOD_AZINLIK,
)

# Her zaman dışarıda kalan sektörler (Greenblatt finansalları hariç tutar)
HARIC_SEKTORLER = {
    "XBANK": "Banka",
    "XSGRT": "Sigorta",
    "XAKUR": "Aracı kurum",
    "XFINK": "Finansal kiralama / faktoring",
    "XYORT": "Menkul kıymet yatırım ortaklığı",
    "XGSYO": "Girişim sermayesi yatırım ortaklığı",
    "XGMYO": "Gayrimenkul yatırım ortaklığı",
    "XUMAL": "Mali (diğer)",
    "XSPOR": "Spor kulübü (farklı mali yıl)",
}
# Sanayi şirketi formatında olmayan mali tablolar (banka, sigorta, finansman)
HARIC_FIN_GRUPLARI = {"UFRS", "UFRS_K", "XI_29K"}
HOLDING_SEKTORU = "XHOLD"

ESIK_FVOK_MARJI = 0.90          # FVÖK / satış bunu aşarsa sıralama dışı
ESIK_SERMAYE_VARLIK = 0.02      # sermaye / toplam varlık bunun altındaysa sıralama dışı


def kapsam_disi_nedeni(fin_group: str | None, sector_code: str | None) -> str | None:
    """Şirket Magic Formula evrenine hiç girmiyorsa nedenini döndürür."""
    if not fin_group:
        return "Mali tablo verisi yok"
    if fin_group in HARIC_FIN_GRUPLARI:
        return "Finansal şirket (banka/sigorta/finansman tablosu)"
    if sector_code in HARIC_SEKTORLER:
        return HARIC_SEKTORLER[sector_code]
    return None


# ─── Dönem yardımcıları ──────────────────────────────────────────────────────

_DONEM_RE = re.compile(r"^(\d{4})/(\d{1,2})$")


def donem_ayristir(donem: str) -> tuple[int, int]:
    """'2026/6' → (2026, 6). Geçersizse ValueError."""
    m = _DONEM_RE.match(str(donem).strip())
    if not m:
        raise ValueError(f"Geçersiz dönem: {donem!r}")
    yil, ay = int(m.group(1)), int(m.group(2))
    if not 1 <= ay <= 12:
        raise ValueError(f"Geçersiz ay: {donem!r}")
    return yil, ay


def donem_sirasi(donem: str) -> int:
    """Karşılaştırma için tek sayı: yıl*12 + ay."""
    yil, ay = donem_ayristir(donem)
    return yil * 12 + ay


def donem_anahtari(yil: int, ay: int) -> str:
    return f"{yil}/{ay}"


def ay_anahtari(donem: str) -> str:
    """'2026/6' → '2026-06' (TÜFE anahtarı)."""
    yil, ay = donem_ayristir(donem)
    return f"{yil}-{ay:02d}"


def ceyrek_farki(eski: str, yeni: str) -> int:
    """İki dönem arasındaki çeyrek sayısı (yeni − eski)."""
    return (donem_sirasi(yeni) - donem_sirasi(eski)) // 3


def onceki_ceyrek(donem: str) -> str:
    yil, ay = donem_ayristir(donem)
    ay -= 3
    if ay <= 0:
        ay += 12
        yil -= 1
    return donem_anahtari(yil, ay)


def gecerli_donemler(donemler: Iterable[str]) -> list[str]:
    sonuc = []
    for d in donemler:
        try:
            donem_sirasi(d)
            sonuc.append(d)
        except ValueError:
            continue
    return sorted(sonuc, key=donem_sirasi)


def en_son_donem(donemler: Iterable[str]) -> str | None:
    g = gecerli_donemler(donemler)
    return g[-1] if g else None


# ─── Sayı yardımcıları ───────────────────────────────────────────────────────

def sayi(deger) -> float | None:
    """JSON'dan gelen değeri float'a çevirir; boş/NaN/geçersizse None."""
    if deger is None or isinstance(deger, bool):
        return None
    if isinstance(deger, (int, float)):
        f = float(deger)
    else:
        s = str(deger).strip().replace(" ", "").replace(" ", "")
        if not s or s in {"-", "—", "null", "None", "NaN"}:
            return None
        negatif = s.startswith("(") and s.endswith(")")
        s = s.strip("()")
        if "," in s:  # Türkçe biçim: 1.234,56
            s = s.replace(".", "").replace(",", ".")
        elif re.fullmatch(r"-?\d{1,3}(\.\d{3})+", s):  # Türkçe binlik: 1.000
            s = s.replace(".", "")
        try:
            f = float(s)
        except ValueError:
            return None
        if negatif:
            f = -abs(f)
    return f if math.isfinite(f) else None


def kalem(donemler: dict, donem: str, kod: str) -> float | None:
    return sayi((donemler.get(donem) or {}).get(kod))


def sifirla(deger: float | None) -> float:
    return 0.0 if deger is None else deger


def donem_dolu_mu(donemler: dict, donem: str) -> bool:
    """Dönemde gelir tablosu verisi gerçekten var mı (hepsi 0 değil mi)?"""
    v = donemler.get(donem) or {}
    return any(sayi(v.get(k)) not in (None, 0.0) for k in (KOD_SATIS, KOD_BRUT_KAR, KOD_FVOK))


# ─── TÜFE ─────────────────────────────────────────────────────────────────────

def tufe_endeksi_kur(aylik_degisim: dict[str, float]) -> dict[str, float]:
    """
    Aylık % değişimlerden zincirleme endeks kurar (ilk ay öncesi = 100).
    Baz yılı değişse de (2003=100 → 2025=100) aylık değişimler zinciri bozmaz.
    """
    endeks: dict[str, float] = {}
    deger = 100.0
    onceki = None
    for ay in sorted(aylik_degisim):
        oran = sayi(aylik_degisim[ay])
        if oran is None:
            break
        if onceki is not None and _ay_farki(onceki, ay) != 1:
            break  # eksik ay varsa zincir kopar
        deger *= 1 + oran / 100
        endeks[ay] = deger
        onceki = ay
    return endeks


def _ay_farki(a: str, b: str) -> int:
    ya, ma = int(a[:4]), int(a[5:7])
    yb, mb = int(b[:4]), int(b[5:7])
    return (yb * 12 + mb) - (ya * 12 + ma)


def tufe_orani(endeks: dict[str, float], hedef_ay: str, kaynak_ay: str) -> float | None:
    """TÜFE(hedef) / TÜFE(kaynak); ay anahtarları 'YYYY-MM'."""
    a, b = endeks.get(hedef_ay), endeks.get(kaynak_ay)
    if not a or not b:
        return None
    return a / b


# ─── Mali yıl ve son 12 ay ───────────────────────────────────────────────────

def mali_yil_sonu_ayi(donemler: dict) -> int:
    """
    Mali yılın bittiği ayı bulur (çoğu şirkette 12). Kümülatif satışlar mali yıl
    sonundan sonraki çeyrekte sıfırlanıp belirgin şekilde düşer.
    """
    sirali = gecerli_donemler(donemler)
    sifirlanma: Counter = Counter()
    for a, b in zip(sirali, sirali[1:]):
        if donem_sirasi(b) - donem_sirasi(a) != 3:
            continue
        va, vb = kalem(donemler, a, KOD_SATIS), kalem(donemler, b, KOD_SATIS)
        if va and vb is not None and va > 0 and vb < va * 0.8:
            sifirlanma[donem_ayristir(a)[1]] += 1
    if not sifirlanma or sifirlanma.get(12):
        return 12
    return sifirlanma.most_common(1)[0][0]


def son_12_ay(donemler: dict, kod: str, son: str, yil_sonu_ayi: int = 12) -> tuple[float | None, str]:
    """
    Kümülatif gelir tablosu kaleminden son 12 ay değeri (son dönemin parasıyla).
    Döndürür: (değer, yöntem) — yöntem ∈ {"yillik", "ttm", "yilliklandirilmis", "eksik"}.
    """
    yil, ay = donem_ayristir(son)
    cari = kalem(donemler, son, kod)
    if cari is None:
        return None, "eksik"
    if ay == yil_sonu_ayi:
        return cari, "yillik"

    # Son dönemden önceki en yakın mali yıl sonu
    fy_yil = yil if yil_sonu_ayi < ay else yil - 1
    onceki_yil_sonu = donem_anahtari(fy_yil, yil_sonu_ayi)
    onceki_ayni_donem = donem_anahtari(yil - 1, ay)
    if donem_dolu_mu(donemler, onceki_yil_sonu) and donem_dolu_mu(donemler, onceki_ayni_donem):
        fy = kalem(donemler, onceki_yil_sonu, kod)
        py = kalem(donemler, onceki_ayni_donem, kod)
        if fy is not None and py is not None:
            return cari + fy - py, "ttm"

    # Mali yıl başından itibaren geçen ay sayısı
    gecen_ay = (ay - yil_sonu_ayi) % 12 or 12
    return cari * 12 / gecen_ay, "yilliklandirilmis"


# ─── Şirket metrikleri ───────────────────────────────────────────────────────

def donem_eksik_mi(donemler: dict, donem: str) -> bool:
    """
    Kaynakta yarım işlenmiş dönemleri yakalar (ör. son raporda maddi duran
    varlıklar ve faaliyet giderleri boş gelmiş). Böyle bir dönem hesaba girmez.
    """
    v = donemler.get(donem) or {}
    for kod in (KOD_DONEN, KOD_KVY, KOD_TOPLAM_VARLIK):
        if sayi(v.get(kod)) is None:
            return True
    if sayi(v.get(KOD_FVOK)) is None and (
        sayi(v.get(KOD_BRUT_KAR)) is None or sayi(v.get(KOD_GENEL_YONETIM)) is None
    ):
        return True
    # Önceki dönemde maddi duran varlık varken bu dönemde hiç yoksa eksik say
    onceki = onceki_ceyrek(donem)
    if donemler.get(onceki) and sayi(v.get(KOD_MDV)) is None and sayi(v.get(KOD_YATIRIM_GAYRIMENKUL)) is None:
        eski_mdv = sifirla(kalem(donemler, onceki, KOD_MDV)) + sifirla(kalem(donemler, onceki, KOD_YATIRIM_GAYRIMENKUL))
        eski_varlik = sifirla(kalem(donemler, onceki, KOD_TOPLAM_VARLIK))
        if eski_varlik and eski_mdv > eski_varlik * 0.05:
            return True
    return False


def kullanilacak_donem(donemler: dict, son: str) -> tuple[str | None, bool]:
    """
    Hesapta kullanılacak bilanço dönemi. Son dönem kaynakta eksikse bir önceki
    çeyreğe düşer. Döndürür: (dönem ya da None, son dönem eksik miydi).
    """
    if son in donemler and not donem_eksik_mi(donemler, son):
        return son, False
    onceki = onceki_ceyrek(son)
    if onceki in donemler and not donem_eksik_mi(donemler, onceki):
        return onceki, True
    return None, True


def fvok_tamamla(donemler: dict) -> tuple[dict, set[str]]:
    """
    Bazı raporlarda 3H (net faaliyet kârı) boş gelir. Bu dönemlerde FVÖK'ü
    bileşenlerinden kurar: 3D + 3DA + 3DB + 3DC (gider kalemleri negatif tutulur).
    Verideki dönemlerin %99,7'sinde bu eşitlik birebir tutuyor.
    """
    sonuc, turetilen = {}, set()
    for d, v in donemler.items():
        v = dict(v or {})
        if (
            sayi(v.get(KOD_FVOK)) is None
            and sayi(v.get(KOD_BRUT_KAR)) is not None
            and sayi(v.get(KOD_GENEL_YONETIM)) is not None  # gider kalemleri de gelmiş olmalı
        ):
            v[KOD_FVOK] = sayi(v.get(KOD_BRUT_KAR)) + sum(
                sifirla(sayi(v.get(k))) for k in (KOD_PAZARLAMA, KOD_GENEL_YONETIM, KOD_ARGE)
            )
            turetilen.add(d)
        sonuc[d] = v
    return sonuc, turetilen


def sirket_metrikleri(
    donemler: dict,
    son: str,
    piyasa_degeri: float | None,
    endeks: dict[str, float] | None = None,
    guncel_tufe_ayi: str | None = None,
) -> dict:
    """
    Tek şirket için Magic Formula bileşenlerini hesaplar.
    Tutarlar TL; oranlar yüzde. `hata` doluysa şirket sıralamaya girmez.
    """
    endeks = endeks or {}
    sonuc: dict = {"donem": son, "bayraklar": []}
    donemler, turetilen = fvok_tamamla(donemler)
    if son in turetilen:
        sonuc["bayraklar"].append("fvok_bilesenlerden")
    fy_ay = mali_yil_sonu_ayi(donemler)
    if fy_ay != 12:
        sonuc["bayraklar"].append(f"mali_yil_sonu_{fy_ay}")

    fvok, yontem = son_12_ay(donemler, KOD_FVOK, son, fy_ay)
    if fvok is not None and fvok == 0.0 and not donem_dolu_mu(donemler, son):
        fvok, yontem = None, "eksik"
    sonuc["ttm_yontemi"] = yontem
    if yontem == "yilliklandirilmis":
        sonuc["bayraklar"].append("yilliklandirilmis")

    satis, _ = son_12_ay(donemler, KOD_SATIS, son, fy_ay)
    amortisman, _ = son_12_ay(donemler, KOD_AMORTISMAN, son, fy_ay)

    donen = kalem(donemler, son, KOD_DONEN)
    kvy = kalem(donemler, son, KOD_KVY)
    nakit = sifirla(kalem(donemler, son, KOD_NAKIT)) + sifirla(kalem(donemler, son, KOD_KV_FIN_YAT))
    kv_borc = sifirla(kalem(donemler, son, KOD_KV_FIN_BORC))
    fin_borc = kv_borc + sifirla(kalem(donemler, son, KOD_UV_FIN_BORC))
    azinlik = sifirla(kalem(donemler, son, KOD_AZINLIK))
    mdv = sifirla(kalem(donemler, son, KOD_MDV))
    kullanim = sifirla(kalem(donemler, son, KOD_KULLANIM_HAKKI))
    yatirim_gm = sifirla(kalem(donemler, son, KOD_YATIRIM_GAYRIMENKUL))
    toplam_varlik = kalem(donemler, son, KOD_TOPLAM_VARLIK)

    sonuc.update({
        "fvok": fvok,
        "satis": satis,
        "nakit": nakit,
        "finansal_borc": fin_borc,
        "net_borc": fin_borc - nakit,
        "azinlik": azinlik,
        "piyasa_degeri": piyasa_degeri,
    })

    if fvok is None:
        sonuc["hata"] = "FVÖK verisi yok"
        return sonuc
    if not donen or kvy is None:
        sonuc["hata"] = "Bilanço verisi eksik"
        return sonuc
    if not piyasa_degeri or piyasa_degeri <= 0:
        sonuc["hata"] = "Piyasa değeri yok"
        return sonuc

    nis = (donen - nakit) - (kvy - kv_borc)
    net_duran = mdv + kullanim + yatirim_gm
    sermaye = max(nis, 0.0) + net_duran
    fd = piyasa_degeri + fin_borc - nakit + azinlik
    sonuc.update({"nis": nis, "net_duran": net_duran, "sermaye": sermaye, "fd": fd})
    if nis < 0:
        sonuc["bayraklar"].append("nis_negatif")

    # FVÖK'ü bilanço tarihinden fiyat tarihine en yakın TÜFE ayının parasına taşı
    k = None
    if guncel_tufe_ayi:
        k = tufe_orani(endeks, guncel_tufe_ayi, ay_anahtari(son))
    k = k if (k and 0.5 < k < 5) else 1.0
    sonuc["tufe_katsayisi"] = k
    fvok_guncel = fvok * k
    sonuc["fvok_guncel"] = fvok_guncel

    if amortisman is not None:
        favok = fvok + abs(amortisman)
        sonuc["favok"] = favok
        if favok > 0 and fd > 0:
            sonuc["fd_favok"] = fd / (favok * k)

    if fd <= 0:
        sonuc["hata"] = "Firma değeri sıfır ya da negatif (net nakit piyasa değerini aşıyor)"
        sonuc["bayraklar"].append("fd_negatif")
        return sonuc
    if sermaye <= 0:
        sonuc["hata"] = "Yatırılan sermaye sıfır ya da negatif"
        return sonuc
    if fvok > 0 and (satis is None or satis <= 0 or fvok > satis * ESIK_FVOK_MARJI):
        sonuc["hata"] = "FVÖK satışların %90'ından büyük; gelirin çoğu yatırım/değerleme geliri görünüyor"
        return sonuc
    if toplam_varlik and sermaye < toplam_varlik * ESIK_SERMAYE_VARLIK:
        sonuc["hata"] = "Yatırılan sermaye toplam varlıkların %2'sinden az; ROIC anlamlı değil"
        return sonuc

    sonuc["ey"] = fvok_guncel / fd * 100
    sonuc["roic"] = fvok / sermaye * 100
    if fvok <= 0:
        sonuc["bayraklar"].append("zarar")
    return sonuc


# ─── Sıralama ─────────────────────────────────────────────────────────────────

def siralar(degerler: list[float], azalan: bool = True) -> list[float]:
    """Ortalama sıra (eşitlikte ortalama), 1 = en iyi."""
    sirali = sorted(range(len(degerler)), key=lambda i: degerler[i], reverse=azalan)
    sonuc = [0.0] * len(degerler)
    i = 0
    while i < len(sirali):
        j = i
        while j + 1 < len(sirali) and degerler[sirali[j + 1]] == degerler[sirali[i]]:
            j += 1
        ort = (i + j) / 2 + 1
        for k in range(i, j + 1):
            sonuc[sirali[k]] = ort
        i = j + 1
    return sonuc


def magic_formula_sirala(hisseler: list[dict]) -> list[dict]:
    """ey ve roic alanı olan hisseleri birleşik sıraya dizer (kopya döndürür)."""
    gecerli = [dict(h) for h in hisseler if h.get("ey") is not None and h.get("roic") is not None]
    ey_sira = siralar([h["ey"] for h in gecerli])
    roic_sira = siralar([h["roic"] for h in gecerli])
    for h, a, b in zip(gecerli, ey_sira, roic_sira):
        h["ey_sira"], h["roic_sira"], h["mf_skor"] = a, b, a + b
    gecerli.sort(key=lambda h: (h["mf_skor"], h["ey_sira"]))
    for n, h in enumerate(gecerli, 1):
        h["mf_sira"] = n
    return gecerli


def medyan(degerler: Iterable[float | None]) -> float | None:
    v = sorted(x for x in degerler if x is not None)
    if not v:
        return None
    n = len(v)
    return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2


def baskin_donem(donemler: Iterable[str]) -> str | None:
    """En çok şirketin bulunduğu bilanço dönemi (eşitlikte en yeni)."""
    sayac = Counter(d for d in donemler if d)
    if not sayac:
        return None
    return max(sayac.items(), key=lambda kv: (kv[1], donem_sirasi(kv[0])))[0]
