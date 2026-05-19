# Yatırım Notları — Kullanım Kılavuzu

Bu dosya, siteyi yönetmek için ihtiyacın olan her şeyi açıklar.

---

## Yeni Blog Yazısı Eklemek

### 1. Dosya oluştur

`src/content/blog/` klasörüne yeni bir `.md` dosyası ekle.
Dosya adı, yazının URL'si olur. Türkçe karakter ve boşluk kullanma.

**Örnek:** `src/content/blog/yeni-yazi-baslik.md`

### 2. Dosyanın başına bu bilgileri yaz

```markdown
---
title: "Yazının Başlığı"
description: "Yazının kısa açıklaması (Google'da görünen metin, ~150 karakter)"
pubDate: 2024-03-15
---

Yazının içeriği buraya gelir...
```

**Alan açıklamaları:**
- `title` — Başlık (tırnak içinde)
- `description` — Kısa açıklama, Google'da ve RSS'de görünür
- `pubDate` — Yayın tarihi, `YYYY-AA-GG` formatında
- `draft: true` — Ekleyebilirsin, yazıyı taslak olarak gizler (opsiyonel)

### 3. Markdown sözdizimi

```markdown
## Bölüm Başlığı

Normal paragraf metni burada.

**Kalın metin**, *italik metin*

- Madde listesi
- İkinci madde

> Alıntı kutusu

[Bağlantı metni](https://ornek.com)

![Görsel açıklaması](/images/gorsel-adi.png)
```

### 4. Görsel eklemek

Görseli `public/images/` klasörüne koy, sonra yazıda şöyle kullan:

```markdown
![Grafik açıklaması](/images/grafik.png)
```

---

## Siteyi Yayınlamak (Her Seferinde)

Yeni yazı veya herhangi bir değişiklik yaptıktan sonra şu üç komutu çalıştır:

```bash
git add .
git commit -m "Yeni yazı: yazı başlığı"
git push
```

Bu kadar. GitHub otomatik olarak siteyi derleyip yayınlar (~2 dakika sürer).

**Yayınlanma durumunu görmek için:**
GitHub'da repoyu aç → üstteki "Actions" sekmesine tıkla → yeşil tik = yayında.

---

## Siteyi Yerel Olarak Önizlemek

Değişiklik yapmadan önce nasıl görüneceğini görmek istersen:

```bash
npm run dev
```

Tarayıcıda `http://localhost:4321` adresine git. Ctrl+C ile durdur.

---

## Sayfa İçeriklerini Güncellemek

| Sayfa | Dosya |
|-------|-------|
| Hakkımda | `src/pages/hakkimda.astro` |
| Yasal Uyarı | `src/pages/yasal-uyari.astro` |
| Gizlilik Politikası | `src/pages/gizlilik-politikasi.astro` |
| Ana Sayfa metni | `src/pages/index.astro` |

Bu dosyaları metin editörüyle açıp düzenleyebilirsin. HTML taglerini (`<p>`, `<h2>` vb.) koruyarak sadece metin kısmını değiştir.

---

## Site Yapısı

```
src/
├── content/blog/       ← Blog yazıları (.md dosyaları) buraya
├── pages/              ← Site sayfaları
├── layouts/Base.astro  ← Ortak HTML çatısı (SEO, fontlar)
├── components/
│   ├── Header.astro    ← Üst menü + dark mode butonu
│   └── Footer.astro    ← Alt bilgi
└── styles/global.css   ← Renkler ve genel stiller

public/
├── images/             ← Görseller buraya (yazıdan /images/x.png ile erişilir)
└── data/               ← Araçların okuduğu JSON dosyaları (otomatik güncellenir)
    ├── bist-heatmap.json         ← Isı haritası verisi
    └── bist-endeks-etkisi.json   ← Endeks etkisi verisi

data/                   ← Script girdileri (GitHub'da saklanır, deploy edilmez)
├── bist-tickers.json             ← Tüm BIST hisseleri, sektörler
└── bist100-agirliklari.json      ← BIST 100 ağırlıkları (halka açıklık bazlı)

scripts/                ← Otomatik veri toplama scriptleri
├── fetch_bist_tickers.py         ← Hisse + sektör listesi (GitHub Action: güncelle-tickerlar)
├── fetch_bist_data.py            ← Isı haritası fiyatları (GitHub Action: 15 dak.)
├── fetch_endeks_agirliklari.py   ← BIST 100 ağırlıkları (GitHub Action: sabah günlük)
└── calculate_endeks_etki.py      ← Endeks etkisi hesabı (GitHub Action: 15 dak.)
```

---

## Araç: BIST Isı Haritası

**Sayfa:** `/araclar/bist-isi-haritasi/`

Tüm BIST hisselerini piyasa değeri ve fiyat değişimine göre görselleştirir.

**Veri kaynakları:**
- `data/bist-tickers.json` — hisse listesi ve sektörler
- `public/data/bist-heatmap.json` — güncel fiyatlar (yfinance, 15 dk.)

**Bakım gerektiren durumlar:**
- Sektör sınıflandırması yanlışsa → `scripts/fetch_bist_tickers.py` içindeki `SECTOR_MAP` sözlüğünü düzenle
- Yeni bir hisse listeye girmiyorsa → GitHub Actions "BIST Ticker Listesi Güncelle" workflow'unu elle çalıştır

---

## Araç: BIST 100 Endeks Etkisi

**Sayfa:** `/araclar/bist100-endeks-etkisi/`

Hangi hisselerin BIST 100'ü ne kadar etkilediğini gösterir.
**Katkı formülü:** `katkı = ağırlık(%) × değişim(%) / 100`

### Veri kaynakları (5 katman)

| Kaynak | Ne sağlar? | Güncelleme |
|--------|-----------|------------|
| BİST resmi CSV | BIST 100 üyelik listesi (tam 100 hisse) | Günlük |
| İş Yatırım | Piyasa değeri + halka açıklık oranı | Günlük (sabah) |
| yfinance | Anlık fiyat değişimleri | 15 dakika |
| `data/bist100-agirliklari.json` | Hesaplanmış ağırlıklar | Günlük (sabah) |
| `public/data/bist-endeks-etkisi.json` | Araç tarafından okunan son çıktı | 15 dakika |

### GitHub Actions workflow'ları

| Workflow | Dosya | Ne zaman çalışır? |
|----------|-------|-------------------|
| BIST 100 Endeks Ağırlıkları | `fetch-endeks-agirliklari.yml` | Pzt–Cuma 09:00 TRT |
| BIST Fiyat Verisi | `fetch-prices.yml` | Pzt–Cuma 09:30–18:30 TRT (15 dk.) |

### `agirlik_kaynagi` alanı nasıl kontrol edilir?

`data/bist100-agirliklari.json` dosyasını aç, `agirlik_metodoloji` bölümüne bak:

```json
"agirlik_metodoloji": {
  "kaynak": "BİST CSV + İş Yatırım (halka açıklık × piyasa değeri, %10 cap)",
  "son_basarili_cekim": "2026-05-19T09:29:04+03:00",
  "fallback_aktif": false,
  "fallback_aciklama": null
}
```

- `fallback_aktif: false` → Normal, güncel veri kullanılıyor
- `fallback_aktif: true` → İş Yatırım'dan veri alınamadı, önceki günün ağırlıkları kullanılıyor (sayfada uyarı çıkar)

### %10 cap nedir?

BIST 100 endeksinin resmi kuralı: hiçbir hisse endekste %10'dan fazla ağırlık taşıyamaz.
Aşan hissenin fazlası diğer hisselere orantılı dağıtılır.
2026 itibarıyla genellikle ASELS bu limite takılıyor.

### Çeyrek dönem revizyonları

BİST 100 endeksi her yılın Şubat, Nisan, Ağustos ve Ekim aylarında revize edilir.
Revizyon sonrası üyelik değişirse `fetch_endeks_agirliklari.py` otomatik günceller
(BİST resmi CSV'sini okur). Manuel müdahale gerekmez.

### Sorun giderme

| Sorun | Muhtemel neden | Çözüm |
|-------|---------------|-------|
| Sayfada "Veri yüklenemedi" | `bist-endeks-etkisi.json` eksik | `fetch-prices.yml` workflow'unu elle çalıştır |
| Sektörler hep "Diğer" | `bist-tickers.json` eski | "BIST Ticker Listesi Güncelle" workflow'unu çalıştır |
| Fark yüksek (>100 bps) | Aylık hesap için normaldir; günlük >50 bps ise araştır | Actions loguna bak |
| İş Yatırım fallback aktif | Site geçici olarak erişilemez | Sabah tekrar dene, genellikle kendiliğinden düzelir |

---

## İletişim & Yardım

Herhangi bir sorun için: **blog.yatirimnotlari@gmail.com**
