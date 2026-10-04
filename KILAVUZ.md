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

## İçerik Dili (SPK Uyumu)

Site bir yatırım danışmanlığı hizmeti değildir; yazılar ve araçlar bunu dilleriyle de yansıtmalı.
Belirli hisseler için yönlendirici öneriler izinsiz yatırım danışmanlığı sayılabilir; fiyatları
etkilemek amacıyla yanlış veya yanıltıcı bilgi, söylenti ya da yorum yaymak ise piyasa dolandırıcılığı
suçudur (6362 sayılı Sermaye Piyasası Kanunu m. 107/2). "Yatırım tavsiyesi değildir" notu tek başına
yeterli değildir; asıl önemli olan metnin kendisidir.

Yeni bir yazı ya da araç eklerken (yapay zekâ araçlarıyla çalışırken de bu bölümü göster):

- Hisse bazında **al / sat / tut, AL sinyali, hedef fiyat, fırsat, ideal, kaçırma, uçacak** gibi
  yönlendirici ifadeler ve **ucuz / pahalı / kaliteli / vasat** gibi değer yargıları kullanma.
- Araç sonuçlarını ölçütün adıyla anlat: "FVÖK / FD medyanın üzerinde", "SuperTrend yönü yukarı
  döndü", "endekse en büyük pozitif katkı".
- Bir yöntemin kendi terimini kullanman gerekiyorsa sahibine atfet: "Greenblatt'ın yönteminde
  ucuzluk ölçüsü".
- Her araç sayfasının üstüne `<AracUyari />` bileşenini (`src/components/AracUyari.astro`), altına
  veri kaynağını ve Yasal Uyarı bağlantısını koy.
- Geçmiş veriye dayanan yazılara ve geriye dönük testlere "geçmiş performans gelecekteki sonuçların
  göstergesi değildir" notunu ekle; geçmişteki bir sonucu kural ya da garanti gibi sunma.
- Belirli bir şirket hakkında doğrulanmamış haber veya söylenti paylaşma; resmi kaynak KAP'tır.
- Pozisyon taşıdığın bir hisseyi ayrıca ele alıyorsan bunu yazıda belirt.
- Paylaşılabilir görsellerde (ör. Magic Formula PNG'si) "yatırım tavsiyesi değildir" notu görselin
  içinde yer almalı.

---

## Site Yapısı

```
src/
├── content/blog/       ← Blog yazıları (.md dosyaları) buraya
├── pages/              ← Site sayfaları
├── layouts/Base.astro  ← Ortak HTML çatısı (SEO, fontlar)
├── components/
│   ├── Header.astro    ← Üst menü + dark mode butonu
│   ├── Footer.astro    ← Alt bilgi
│   └── AracUyari.astro ← Araç sayfalarının üstündeki kısa yasal not
└── styles/global.css   ← Renkler ve genel stiller

public/
├── images/             ← Görseller buraya (yazıdan /images/x.png ile erişilir)
└── data/               ← Araçların okuduğu JSON dosyaları (otomatik güncellenir)
    ├── bist-heatmap.json         ← Isı haritası verisi
    ├── bist-endeks-etkisi.json   ← Endeks etkisi verisi
    ├── bist-weekly-supertrend.json ← Haftalık SuperTrend tarama verisi
    └── magic-formula.json        ← Magic Formula haritası verisi

data/                   ← Script girdileri (GitHub'da saklanır, deploy edilmez)
├── bist-tickers.json             ← Tüm BIST hisseleri, sektörler
├── bist100-agirliklari.json      ← BIST 100 ağırlıkları (halka açıklık bazlı)
└── magic-formula/                ← Magic Formula girdileri (mali tablolar, TÜFE, arşiv)

scripts/                ← Otomatik veri toplama scriptleri
├── fetch_bist_tickers.py         ← Hisse + sektör listesi (GitHub Action: güncelle-tickerlar)
├── fetch_bist_data.py            ← Isı haritası fiyatları (GitHub Action: 15 dak.)
├── fetch_weekly_supertrend.py     ← Haftalık SuperTrend taraması (pazartesi)
├── fetch_endeks_agirliklari.py   ← BIST 100 ağırlıkları (GitHub Action: sabah günlük)
├── calculate_endeks_etki.py      ← Endeks etkisi hesabı (GitHub Action: 15 dak.)
├── mf_lib.py                     ← Magic Formula hesap çekirdeği (formüller burada)
├── fetch_mali_tablolar.py        ← Magic Formula: şirket listesi + mali tablolar (günlük)
├── fetch_tufe.py                 ← Magic Formula: TÜFE aylık değişimleri (günlük)
├── calculate_magic_formula.py    ← Magic Formula: FVÖK/FD ve ROIC hesabı (günlük)
└── tests/test_mf_lib.py          ← Magic Formula hesap testleri
```

---

## Araç: Magic Formula Haritası

**Sayfa:** `/araclar/magic-formula-haritasi/`

Joel Greenblatt'ın Magic Formula yöntemini BIST'e uygular. Her şirket için iki
oran hesaplanır ve haritada gösterilir:

| Ölçü | Formül |
|------|--------|
| FVÖK / FD — yatay eksen (Greenblatt'ın ucuzluk ölçüsü) | FVÖK / Firma değeri |
| ROIC — dikey eksen (Greenblatt'ın kalite ölçüsü) | FVÖK / (net işletme sermayesi + maddi duran varlıklar + kullanım hakkı varlıkları + yatırım amaçlı gayrimenkuller) |

- **FVÖK:** son 12 ayın net faaliyet kârı (brüt kâr − pazarlama − genel yönetim − Ar-Ge).
  Kur farkı / vade farkı gibi diğer faaliyet gelir-giderleri dahil değildir.
- **Firma değeri:** piyasa değeri + finansal borçlar − nakit − KV finansal yatırımlar + azınlık payları.
- **Kesikli çizgiler:** seçili evrenin (BIST 30/50/100/Tümü) medyanları. Sağ-üst köşe = iki oran da medyanın üstünde.
  Kadranlar sayfada yalnızca konumla adlandırılır (sağ-üst, sol-üst…), değer yargısı içeren ad kullanılmaz.
- **Magic Formula sırası:** FVÖK/FD sırası + ROIC sırası (toplamı en düşük olan en üstte).
- Bankalar, sigorta, aracı kurumlar, finansal kiralama/faktoring, yatırım ortaklıkları,
  GYO'lar ve spor kulüpleri kapsam dışıdır. Holdingler sayfada bir anahtarla açılır.
- Formüllerin kodu: `scripts/mf_lib.py` (testleri `scripts/tests/test_mf_lib.py`).

### Veri kaynakları

| Kaynak | Ne sağlar? | Dosya |
|--------|-----------|-------|
| BilancoVeri açık API (KAP / Borsa İstanbul verisi) | Şirket listesi, fiyat, piyasa değeri, mali tablolar | `data/magic-formula/sirketler.json`, `data/magic-formula/mali-tablolar/*.json` |
| Borsa İstanbul endeks CSV | BIST 30 / 50 / 100 üyelikleri | `data/magic-formula/endeksler.json` |
| TCMB (TÜİK verisi) | TÜFE aylık değişimleri | `data/magic-formula/tufe.json` |
| Hesap sonucu | Sayfanın okuduğu dosya | `public/data/magic-formula.json` |
| Çeyreklik arşiv | "Kadran değiştirenler" karşılaştırması | `data/magic-formula/arsiv.json` |
| Günlük arşiv (backtest için) | Her günün tüm BIST Magic Formula listesi | `data/magic-formula/gecmis/YYYY/YYYY-AA-GG.csv.gz` |

BilancoVeri'nin ücretsiz geliştirici planı kaynak gösterilmesini şart koşar; sayfanın
altındaki "Veri: KAP/Borsa İstanbul, derleyen BilancoVeri.com" satırı bu yüzden var,
silinmemeli. Site ileride ticari kullanıma (ör. reklam) geçerse BilancoVeri'nin
ücretli lisansı gerekir.

**Enflasyon muhasebesi (TMS 29):** BilancoVeri geçmiş dönemleri son bilançonun satın
alma gücüyle tutar (ör. 6A/2025 rakamı, 6A/2026 raporundaki düzeltilmiş karşılaştırmalı
rakamdır). Bu yüzden son 12 ay = cari dönem + önceki yıl − önceki yılın aynı dönemi.
TÜFE yalnızca FVÖK'ü bilanço tarihinden fiyat tarihine taşımak için kullanılır.

### Güncelleme

İş akışı: **Magic Formula Verisi Güncelle** (`.github/workflows/magic-formula.yml`)

- Her gün 22:40 TRT'de çalışır (GitHub zamanlanmış işleri bazen gecikmeli başlatır).
- Yalnızca yeni bilanço açıklayan şirketlerin tablolarını indirir; diğerlerini ayda bir kontrol eder.
- Sonuç değiştiyse siteyi kendisi yeniden yayınlar (`deploy.yml`'yi tetikler).
- Baskın bilanço dönemi değişince (ör. 2026/6 → 2026/9) önceki dönemin son hali
  arşivde kalır; sayfadaki "kadran değiştirenler" listesi buna göre kurulur.

Elle yenilemek için: GitHub → **Actions** → **Magic Formula Verisi Güncelle** → **Run workflow**.

Sayfanın üstündeki "Son güncelleme" rozeti son hesaplamanın zamanını gösterir. Veri 3 günden
eskiyse rozet sarıya döner ve altında bir uyarı çıkar; bu, otomatik güncellemenin aksadığı anlamına gelir.

### Günlük arşiv (backtest için)

Her çalıştırmada, tüm BIST şirketlerinin o günkü listesi (ucuzluk, kalite, Magic Formula sırası,
fiyat, piyasa değeri, firma değeri, FVÖK, sermaye, bilanço dönemi, endeks üyeliği) sıkıştırılmış CSV
olarak `data/magic-formula/gecmis/` klasörüne yazılır. Sitede yayınlanmaz, yalnızca GitHub'da durur.

- Dosya adı fiyatların ait olduğu gündür: `2026/2026-10-05.csv.gz`
- İçerik bir önceki günle aynıysa (hafta sonu, tatil) yeni dosya açılmaz.
- Bir dosya ~14 KB; yılda ~3,5 MB, 10 yılda ~35 MB.
- Sütunların açıklaması ve Python ile okuma örneği: `data/magic-formula/gecmis/README.md`

### Sorun giderme

| Sorun | Muhtemel neden | Çözüm |
|-------|---------------|-------|
| Sayfada "Veri henüz hazır değil" | `public/data/magic-formula.json` yok | İş akışını elle çalıştır |
| "Veri X gündür güncellenmedi" uyarısı | İş akışı birkaç gündür başarısız ya da kaynak güncellenmiyor | Actions'ta kırmızı çalışmaya bak, elle çalıştır |
| Bir şirket haritada yok | Finansal şirket ya da "Haritada olmayan şirketler" listesindeki neden | Sayfadaki listeye bak |
| İş akışı kırmızı (başarısız) | BilancoVeri / Borsa İstanbul geçici olarak erişilemez | Ertesi gün kendiliğinden düzelir; önceki veri sayfada kalır |
| Testler başarısız | `scripts/mf_lib.py` değiştirilmiş | Değişikliği geri al ya da testi güncelle |

---

## Araç: Haftalık SuperTrend Taraması

**Sayfa:** `/araclar/haftalik-supertrend-taramasi/`

Tüm BIST hisselerinde SuperTrend (ATR 10, çarpan 3, kaynak HL2) hesaplar.
Güncel haftalık mum taramaya alınmaz; yalnızca bir önceki haftalık mumda
SuperTrend göstergesinin yönü aşağıdan yukarıya dönen hisseler listelenir. Yahoo Finance OHLC
verisi bölünme ve nakit temettülere göre düzeltilir; eksik şirket işlemleri
fiyat onarım özelliğiyle tamamlanır.

Sayfa güncel sonucun altında önceki 12 tarama haftasını da gösterir. Her geçmiş
haftada pazartesi tarama tarihi, değerlendirilen cuma kapanışı ve o kapanışta
gösterge yönü yukarı dönen hisseler yer alır. Pazartesi güncellemesinde liste otomatik olarak bir
hafta ileri kayar.

Veri her pazartesi 10:15 TRT'de otomatik yenilenir. Elle yenilemek için:

1. GitHub'da **Actions** sekmesini aç.
2. **Haftalık SuperTrend Taraması** iş akışını seç.
3. **Run workflow** düğmesine bas.

Tarama tamamlanınca site de otomatik olarak yeniden yayınlanır.

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
| BIST Fiyat Verisi | `fetch-prices.yml` | Pzt–Cuma 09:30–18:30 TRT (15 dk.); veri değişince siteyi yeniden yayınlar |

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
