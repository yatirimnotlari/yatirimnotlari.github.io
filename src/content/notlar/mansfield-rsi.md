---
title: Mansfield RSI
description: Stan Weinstein'ın popülerleştirdiği gösterge — bir hissenin piyasaya göre ne kadar güçlü olduğunu ölçer. Adındaki "RSI"ya aldanmayın, Wilder'ın klasik RSI'ıyla hiçbir ilgisi yoktur.
pubDate: 2026-05-19
aiAuthored: true
draft: false
---

Mansfield RSI (Mansfield Relative Strength Index), Stan Weinstein'ın *Secrets for Profiting in Bull and Bear Markets* kitabıyla popülerleşen ve bir hissenin piyasaya göre ne kadar güçlü olduğunu ölçen bir göstergedir. Adındaki "RSI"ya aldanmayın — Welles Wilder'ın klasik RSI'ı ile hiçbir ilgisi yoktur. Tamamen farklı bir hesap, farklı bir mantık.

## Temel fikir

Bir hisse yükselebilir, ama önemli olan endeksten daha mı hızlı yükseliyor, yoksa geride mi kalıyor?

Örneğin BIST 100 son bir yılda %30 yükselmiş. Sizin baktığınız hisse de %30 yükselmişse, aslında piyasayla aynı tempoda — özel bir şey yapmıyor. Ama hisse %60 yükselmişse piyasadan belirgin biçimde güçlü; %10 yükselmişse zayıf. Mansfield RSI işte bu farkı, bir çizgi olarak çiziyor.

## Nasıl hesaplanıyor

İki adımdan ibaret:

**Adım 1 — Ham göreli güç (RS):** Hissenin fiyatını endeksin fiyatına bölersin.

$$RS = \frac{\text{Hisse fiyatı}}{\text{Endeks fiyatı}}$$

Bu oran yükseliyorsa hisse endeksten iyi performans gösteriyor demektir, düşüyorsa kötü. Tek başına şu sorunu var: oranın mutlak değeri kafa karıştırıyor (hisse 100 TL, endeks 10.000 puan → 0.01 gibi anlamsız bir sayı). O yüzden ikinci adım gelir.

**Adım 2 — Normalize et:** Bu oranın bugünkü değerini, son 52 haftalık (yıllık) ortalamasına göre yüzdesel sapma olarak ifade et.

$$\text{Mansfield RSI} = \left( \frac{RS_{\text{bugün}}}{\overline{RS}_{52\text{ hafta}}} - 1 \right) \times 100$$

Bu sayede gösterge sıfır etrafında salınır: pozitifse hisse son bir yıllık göreli güç ortalamasının üzerinde, negatifse altında.

## Nasıl okunur

Sıfır çizgisi her şeyin merkezidir.

**Pozitif bölge (>0):** Hisse piyasanın üzerinde performans gösteriyor. Weinstein'ın Stage 2 (yükseliş aşaması) için kritik şartı budur — bir hisse Stage 2'ye geçtiğinde Mansfield RSI sıfırın üzerine çıkmalı ve orada kalmalıdır. Sıfırın üzerinde olmayan bir breakout, Weinstein'a göre satın alınmaz.

**Negatif bölge (<0):** Hisse piyasanın gerisinde. Yükseliyor olsa bile, endeks daha hızlı yükseliyor demektir. Stage 4 (düşüş) ve Stage 1 (taban) hisseleri genelde burada bulunur.

**Sıfır çizgisi kesişimleri:** Negatiften pozitife geçiş, liderlik değişiminin erken sinyalidir. Pozitiften negatife geçiş ise zayıflama uyarısıdır.

## Klasik RSI'dan farkı

Bunu netleştirmekte fayda var çünkü isim aynı:

**Wilder'ın RSI'ı** hissenin kendi içindeki momentumu ölçer (0–100 arası, 70 üstü aşırı alım, 30 altı aşırı satım). Sadece o hissenin fiyat hareketine bakar.

**Mansfield RSI** ise hissenin endekse göre gücünü ölçer. Sıfır etrafında salınır, "aşırı alım/satım" kavramı yoktur. Tamamen göreli bir ölçüdür.

## Pratik kullanım

Weinstein metodunda Mansfield RSI bir filtre olarak çalışır: 30 haftalık hareketli ortalamanın üzerinde, yatay direnci kıran ve aynı zamanda Mansfield RSI'ı sıfırın üzerinde olan hisseler Stage 2 adayıdır. Bu üçlü şart, sahte breakout'ları büyük ölçüde eler.

BIST tarafında uygulamak isterseniz karşılaştırma endeksi olarak XU100 (veya hissenin sektör endeksi) doğal seçimdir; aynı analizi sektör endeksi vs. XU100 üzerine kurarak hangi sektörün liderlik ettiğini de görebilirsiniz.
