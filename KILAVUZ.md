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
└── images/             ← Görseller buraya (yazıdan /images/x.png ile erişilir)
```

---

## İletişim & Yardım

Herhangi bir sorun için: **blog.yatirimnotlari@gmail.com**
