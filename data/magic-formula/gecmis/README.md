# Magic Formula günlük arşivi

Bu klasör sitede yayınlanmaz, yalnızca GitHub'da durur. Amacı, ileride geriye dönük
test (backtest) yapabilmek için her günün Magic Formula listesini **o gün bilinen
haliyle** saklamaktır. Dosyaları `scripts/calculate_magic_formula.py` her gün
otomatik yazar; elle değiştirilmemelidir.

## Dosyalar

`YYYY/YYYY-AA-GG.csv.gz` — o günün listesi (gzip ile sıkıştırılmış CSV).

- Tarih, fiyatların ait olduğu gündür (İstanbul saati).
- İçerik bir önceki dosyayla aynıysa (hafta sonu, resmi tatil) yeni dosya açılmaz;
  o günler için bir önceki dosya geçerlidir.
- Bir dosya yaklaşık 14 KB. Yılda ~250 dosya ≈ 3,5 MB, 10 yılda ≈ 35 MB.
- macOS'te çift tıklayınca açılır; Windows'ta 7-Zip ile açılabilir.

## Sütunlar

| Sütun | Açıklama |
|-------|----------|
| `ticker` | Hisse kodu |
| `sektor_kodu` | BIST sektör endeksi kodu (`XHOLD` = holding ve yatırım) |
| `endeks` | O günkü endeks üyeliği: `30` = BIST 30 (aynı zamanda 50 ve 100), `50` = BIST 50 (ve 100), `100` = yalnızca BIST 100, boş = hiçbiri |
| `donem` | Hesapta kullanılan bilanço dönemi (`2026/6` = 30 Haziran 2026) |
| `fiyat` | Fiyat (TL). Kaynak verisi en az 15 dakika gecikmelidir; günün kapanışına karşılık gelir |
| `piyasa_degeri` | Piyasa değeri (milyon TL) |
| `fd` | Firma değeri = piyasa değeri + finansal borçlar − nakit − KV finansal yatırımlar + azınlık payları (milyon TL) |
| `fvok` | Son 12 ay net faaliyet kârı = brüt kâr − pazarlama − genel yönetim − Ar-Ge (milyon TL, bilanço tarihinin parasıyla) |
| `sermaye` | Yatırılan sermaye = max(net işletme sermayesi, 0) + maddi duran varlıklar + kullanım hakkı varlıkları + yatırım amaçlı gayrimenkuller (milyon TL) |
| `ey` | FVÖK / FD (%) = FVÖK (TÜFE ile fiyat ayına taşınmış) / firma değeri — Greenblatt'ın "earnings yield" ölçüsü |
| `roic` | ROIC (%) = FVÖK / yatırılan sermaye |
| `mf_sira` | Magic Formula sırası: tüm BIST'te, holdingler ve zarar edenler hariç (1 = sıralamada ilk). Boşsa o gün sıralamaya girmedi |
| `not` | Bayraklar (`zarar`, `onceki_donem`, `yilliklandirilmis`, `son_donem_eksik`, `fvok_bilesenlerden`, `mali_yil_sonu_N`) ya da haritaya girmediyse `disarida:<kod>` |

`disarida` kodları: `fd_negatif`, `sermaye_negatif`, `sermaye_kucuk` (sermaye toplam
varlıkların %2'sinden az), `fvok_marji` (FVÖK satışların %90'ından büyük), `fvok_yok`,
`bilanco_eksik`, `bilanco_eski`, `tablo_eksik`, `piyasa_degeri_yok`, `veri_yok`.

Finansal şirketler (banka, sigorta, aracı kurum, finansal kiralama/faktoring, yatırım
ortaklıkları, GYO) ve spor kulüpleri dosyalarda yer almaz.

## Python ile okuma

```python
import glob
import pandas as pd

dosyalar = sorted(glob.glob("data/magic-formula/gecmis/*/*.csv.gz"))
df = pd.concat(
    pd.read_csv(f, dtype={"endeks": str}).assign(tarih=f[-17:-7]) for f in dosyalar
)
# Örnek: yalnızca BIST 100 üyeleri
bist100 = df[df["endeks"].isin(["30", "50", "100"])]
```

`mf_sira` tüm BIST içindir; başka bir evren (ör. yalnızca BIST 100) için sırayı
`ey` ve `roic` sütunlarından yeniden hesaplayın: iki ölçütte ayrı ayrı büyükten
küçüğe sıra verilir, sıraların toplamı en küçük olan ilk sırayı alır.

## Notlar

- Veriler o gün bilinen haliyle saklanır (point-in-time). Sonradan düzeltilen
  bilançolar eski dosyaları değiştirmez; bu, geriye dönük testte "geleceği görme"
  hatasını önler.
- `fiyat` temettü ve sermaye artırımlarına göre düzeltilmemiştir. Getiri hesabında
  düzeltilmiş fiyat kullanın ya da bu etkileri ayrıca hesaba katın.
- Hesap yöntemi ve eşikler: `scripts/mf_lib.py`.
- Kaynak: Veri: KAP/Borsa İstanbul, derleyen BilancoVeri.com · Endeks üyelikleri:
  Borsa İstanbul · TÜFE: TCMB/TÜİK.
- Arşiv 4 Ekim 2026'da başladı.
