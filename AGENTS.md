# Yapay zekâ araçları için notlar

Bu repo yatirimnotlari.github.io sitesinin kaynağıdır (Astro + GitHub Pages).
Ayrıntılı kılavuz: `KILAVUZ.md`.

## İçerik dili (SPK uyumu): her değişiklikte uy

Site bir yatırım danışmanlığı hizmeti değildir. Metin yazarken ya da araç eklerken:

- Hisse bazında al / sat / tut, "AL sinyali", hedef fiyat, fırsat, ideal, "kaçırma", "uçacak" gibi
  yönlendirici ifadeler ve ucuz / pahalı / kaliteli / vasat gibi değer yargıları kullanma.
- Sonuçları ölçütün adıyla anlat ("FVÖK / FD medyanın üzerinde", "SuperTrend yönü yukarı döndü").
- Araç sayfalarının üstüne `src/components/AracUyari.astro` bileşenini, altına veri kaynağını ve
  `/yasal-uyari/` bağlantısını koy.
- Geçmiş veriye dayanan içeriklere "geçmiş performans gelecekteki sonuçların göstergesi değildir"
  notunu ekle.

Ayrıntılar: `KILAVUZ.md` › "İçerik Dili (SPK Uyumu)".
