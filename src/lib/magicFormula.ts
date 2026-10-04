// Magic Formula haritası — sayfa ve tarayıcı tarafında ortak kullanılan
// filtreleme, sıralama ve kadran hesapları. Veri: public/data/magic-formula.json
// (scripts/calculate_magic_formula.py üretir).

export type Evren = 'XU030' | 'XU050' | 'XU100' | 'TUM';

export interface MfHisse {
  ticker: string;
  ad: string;
  sektor: string;
  sektor_kodu: string | null;
  endeksler: string[];
  holding: boolean;
  donem: string;
  ttm: string;
  piyasa_degeri: number | null; // milyon TL
  fd: number | null;
  net_borc: number | null;
  fvok: number | null;
  satis: number | null;
  favok: number | null;
  sermaye: number | null;
  nis: number | null;
  net_duran: number | null;
  ey: number; // %
  roic: number; // %
  fd_favok: number | null;
  bayraklar: string[];
}

export interface MfDisarida {
  ticker: string;
  ad: string;
  sektor: string;
  sektor_kodu: string | null;
  donem?: string;
  neden: string;
}

export interface MfVeri {
  updated_at: string | null;
  fiyat_tarihi: string | null;
  baskin_donem: string | null;
  tufe_ayi: string | null;
  endeks_tarihi: string | null;
  kaynak: Record<string, string>;
  ozet: {
    toplam_sirket: number;
    hesaplanan: number;
    disarida: number;
    kapsam_disi: Record<string, number>;
  };
  hisseler: MfHisse[];
  disarida: MfDisarida[];
  onceki: null | {
    donem: string;
    tarih: string | null;
    aciklama?: string;
    hisseler: Record<string, [number | null, number | null]>;
  };
}

export interface MfFiltre {
  evren: Evren;
  sektor: string; // '' = tüm sektörler
  holding: boolean; // holdingleri dahil et
  zarar: boolean; // zarar edenleri dahil et
}

export const VARSAYILAN_FILTRE: MfFiltre = { evren: 'XU100', sektor: '', holding: false, zarar: false };

export const EVREN_ADI: Record<Evren, string> = {
  XU030: 'BIST 30',
  XU050: 'BIST 50',
  XU100: 'BIST 100',
  TUM: 'Tüm BIST',
};

// Kadranlar yalnızca konumu anlatır: iki oranın seçili evrenin medyanına göre
// üstte mi altta mı olduğu. Değer yargısı içeren adlar ("ucuz", "kaliteli",
// "ideal" vb.) bilerek kullanılmaz — bkz. KILAVUZ.md › İçerik dili.
export type Kadran = 'sagUst' | 'solUst' | 'sagAlt' | 'solAlt';

export const KADRAN_ADI: Record<Kadran, string> = {
  sagUst: 'Sağ-üst',
  solUst: 'Sol-üst',
  sagAlt: 'Sağ-alt',
  solAlt: 'Sol-alt',
};

export const KADRAN_ACIKLAMA: Record<Kadran, string> = {
  sagUst: 'İki oran da medyanın üzerinde',
  solUst: 'Yalnız ROIC medyanın üzerinde',
  sagAlt: 'Yalnız FVÖK / FD medyanın üzerinde',
  solAlt: 'İki oran da medyanın altında',
};

/** Grafik içindeki kadran etiketleri (dar ekranda kısa biçim). */
export const KADRAN_ETIKETI: Record<Kadran, { uzun: string; kisa: string }> = {
  sagUst: { uzun: 'İkisi de medyan üstü', kisa: 'İkisi de üstte' },
  solUst: { uzun: 'Yalnız ROIC medyan üstü', kisa: 'ROIC üstte' },
  sagAlt: { uzun: 'Yalnız FVÖK / FD medyan üstü', kisa: 'FVÖK / FD üstte' },
  solAlt: { uzun: 'İkisi de medyan altı', kisa: 'İkisi de altta' },
};

export interface MfSirali extends MfHisse {
  ey_sira: number;
  roic_sira: number;
  mf_skor: number;
  mf_sira: number;
  kadran: Kadran;
}

export interface MfSonuc {
  liste: MfSirali[]; // Magic Formula sırasına göre
  medyanEy: number | null;
  medyanRoic: number | null;
}

export function filtrele(hisseler: MfHisse[], f: MfFiltre): MfHisse[] {
  return hisseler.filter((h) => {
    if (f.evren !== 'TUM' && !h.endeksler.includes(f.evren)) return false;
    if (f.sektor && h.sektor !== f.sektor) return false;
    if (!f.holding && h.holding) return false;
    if (!f.zarar && h.bayraklar.includes('zarar')) return false;
    return Number.isFinite(h.ey) && Number.isFinite(h.roic);
  });
}

export function medyan(degerler: number[]): number | null {
  const v = degerler.filter((x) => Number.isFinite(x)).sort((a, b) => a - b);
  if (!v.length) return null;
  const n = v.length;
  return n % 2 ? v[(n - 1) / 2] : (v[n / 2 - 1] + v[n / 2]) / 2;
}

/** Ortalama sıra (eşitlikte ortalama), 1 = en yüksek değer. */
export function siralar(degerler: number[]): number[] {
  const idx = degerler.map((_, i) => i).sort((a, b) => degerler[b] - degerler[a]);
  const sonuc = new Array<number>(degerler.length);
  let i = 0;
  while (i < idx.length) {
    let j = i;
    while (j + 1 < idx.length && degerler[idx[j + 1]] === degerler[idx[i]]) j++;
    const ort = (i + j) / 2 + 1;
    for (let k = i; k <= j; k++) sonuc[idx[k]] = ort;
    i = j + 1;
  }
  return sonuc;
}

export function kadranBul(ey: number, roic: number, mx: number | null, my: number | null): Kadran {
  const eyUstte = mx !== null && ey >= mx;
  const roicUstte = my !== null && roic >= my;
  if (eyUstte && roicUstte) return 'sagUst';
  if (roicUstte) return 'solUst';
  if (eyUstte) return 'sagAlt';
  return 'solAlt';
}

export function hesapla(hisseler: MfHisse[], f: MfFiltre): MfSonuc {
  const secili = filtrele(hisseler, f);
  const medyanEy = medyan(secili.map((h) => h.ey));
  const medyanRoic = medyan(secili.map((h) => h.roic));
  const eySira = siralar(secili.map((h) => h.ey));
  const roicSira = siralar(secili.map((h) => h.roic));
  const liste: MfSirali[] = secili.map((h, i) => ({
    ...h,
    ey_sira: eySira[i],
    roic_sira: roicSira[i],
    mf_skor: eySira[i] + roicSira[i],
    mf_sira: 0,
    kadran: kadranBul(h.ey, h.roic, medyanEy, medyanRoic),
  }));
  liste.sort((a, b) => a.mf_skor - b.mf_skor || a.ey_sira - b.ey_sira || a.ticker.localeCompare(b.ticker, 'tr'));
  liste.forEach((h, i) => (h.mf_sira = i + 1));
  return { liste, medyanEy, medyanRoic };
}

/** Önceki çeyreğin anlık görüntüsüne göre sağ-üst kadrana girenler / çıkanlar. */
export function kadranDegisimleri(veri: MfVeri, sonuc: MfSonuc) {
  const onceki = veri.onceki;
  if (!onceki) return null;
  const ortak = sonuc.liste.filter((h) => {
    const p = onceki.hisseler[h.ticker];
    return p && Number.isFinite(p[0] as number) && Number.isFinite(p[1] as number);
  });
  if (ortak.length < 5) return null;
  const pEy = ortak.map((h) => onceki.hisseler[h.ticker][0] as number);
  const pRoic = ortak.map((h) => onceki.hisseler[h.ticker][1] as number);
  const mx = medyan(pEy);
  const my = medyan(pRoic);
  const girenler: MfSirali[] = [];
  const cikanlar: MfSirali[] = [];
  ortak.forEach((h, i) => {
    const eskiSagUst = kadranBul(pEy[i], pRoic[i], mx, my) === 'sagUst';
    const yeniSagUst = h.kadran === 'sagUst';
    if (yeniSagUst && !eskiSagUst) girenler.push(h);
    if (!yeniSagUst && eskiSagUst) cikanlar.push(h);
  });
  return { donem: onceki.donem, tarih: onceki.tarih, aciklama: onceki.aciklama, girenler, cikanlar, karsilastirilan: ortak.length };
}

// ─── Biçimlendirme ──────────────────────────────────────────────────────────

const nf1 = new Intl.NumberFormat('tr-TR', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const nf0 = new Intl.NumberFormat('tr-TR', { maximumFractionDigits: 0 });

export function yuzde(v: number | null | undefined): string {
  if (v === null || v === undefined || !Number.isFinite(v)) return '—';
  return `%${nf1.format(v)}`;
}

/** Milyon TL → okunur tutar ("12,3 milyar TL", "845 milyon TL"). */
export function tutar(mn: number | null | undefined): string {
  if (mn === null || mn === undefined || !Number.isFinite(mn)) return '—';
  const abs = Math.abs(mn);
  if (abs >= 1_000_000) return `${nf1.format(mn / 1_000_000)} trilyon TL`;
  if (abs >= 1_000) return `${nf1.format(mn / 1_000)} milyar TL`;
  return `${nf0.format(mn)} milyon TL`;
}

export function sira(v: number): string {
  return Number.isInteger(v) ? String(v) : nf1.format(v);
}

export function tarihTr(iso: string | null | undefined, saatli = false): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleString('tr-TR', {
    day: '2-digit',
    month: 'long',
    year: 'numeric',
    ...(saatli ? { hour: '2-digit', minute: '2-digit' } : {}),
    timeZone: 'Europe/Istanbul',
  });
}

export function donemTr(donem: string | null | undefined): string {
  return donem || '—';
}
