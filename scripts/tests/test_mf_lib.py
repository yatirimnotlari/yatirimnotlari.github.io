"""
Magic Formula hesap çekirdeği testleri.
Çalıştırma: python -m unittest discover -s scripts/tests -v
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mf_lib import (  # noqa: E402
    baskin_donem,
    donem_eksik_mi,
    kullanilacak_donem,
    ceyrek_farki,
    donem_ayristir,
    donem_sirasi,
    en_son_donem,
    kapsam_disi_nedeni,
    magic_formula_sirala,
    mali_yil_sonu_ayi,
    medyan,
    onceki_ceyrek,
    sayi,
    siralar,
    sirket_metrikleri,
    son_12_ay,
    tufe_endeksi_kur,
    tufe_orani,
)


def gelir(satis, fvok, amortisman=0):
    return {"3C": satis, "3D": fvok * 2, "3H": fvok, "4B": amortisman}


class DonemTestleri(unittest.TestCase):
    def test_ayristir_ve_sira(self):
        self.assertEqual(donem_ayristir("2026/6"), (2026, 6))
        self.assertLess(donem_sirasi("2025/12"), donem_sirasi("2026/3"))
        with self.assertRaises(ValueError):
            donem_ayristir("2026-06")

    def test_ceyrek_yardimcilari(self):
        self.assertEqual(ceyrek_farki("2025/12", "2026/6"), 2)
        self.assertEqual(onceki_ceyrek("2026/3"), "2025/12")
        self.assertEqual(en_son_donem(["2025/12", "2026/3", "bozuk", "2024/6"]), "2026/3")
        self.assertEqual(baskin_donem(["2026/6", "2026/6", "2026/3"]), "2026/6")
        self.assertEqual(baskin_donem(["2026/6", "2026/9"]), "2026/9")  # eşitlikte yeni


class SayiTestleri(unittest.TestCase):
    def test_bicimler(self):
        self.assertEqual(sayi(12.5), 12.5)
        self.assertEqual(sayi("1.234,5"), 1234.5)
        self.assertEqual(sayi("(1.000)"), -1000.0)
        self.assertIsNone(sayi(""))
        self.assertIsNone(sayi(None))
        self.assertIsNone(sayi(float("nan")))
        self.assertIsNone(sayi(True))


class TufeTestleri(unittest.TestCase):
    def test_zincirleme(self):
        e = tufe_endeksi_kur({"2025-01": 10.0, "2025-02": 10.0, "2025-03": 0.0})
        self.assertAlmostEqual(tufe_orani(e, "2025-02", "2025-01"), 1.10)
        self.assertAlmostEqual(tufe_orani(e, "2025-03", "2025-01"), 1.10)
        self.assertIsNone(tufe_orani(e, "2025-04", "2025-01"))

    def test_eksik_ay_zinciri_keser(self):
        e = tufe_endeksi_kur({"2025-01": 1.0, "2025-03": 1.0})
        self.assertEqual(list(e), ["2025-01"])


class Son12AyTestleri(unittest.TestCase):
    def setUp(self):
        self.d = {
            "2025/6": gelir(400, 80),
            "2025/12": gelir(1000, 300),
            "2026/3": gelir(250, 40),
            "2026/6": gelir(500, 100),
        }

    def test_ttm(self):
        deger, yontem = son_12_ay(self.d, "3H", "2026/6")
        self.assertEqual((deger, yontem), (320, "ttm"))

    def test_yillik(self):
        self.assertEqual(son_12_ay(self.d, "3H", "2025/12"), (300, "yillik"))

    def test_yilliklandirma(self):
        # 2025/3 yok → 2026/3 yıllıklandırılır
        self.assertEqual(son_12_ay(self.d, "3H", "2026/3"), (160, "yilliklandirilmis"))

    def test_eksik(self):
        self.assertEqual(son_12_ay(self.d, "3H", "2024/12"), (None, "eksik"))

    def test_mart_mali_yili(self):
        # Mali yılı Mart'ta biten şirket: satışlar Haziran'da sıfırlanıyor
        d = {
            "2024/12": gelir(900, 90),
            "2025/3": gelir(1200, 120),
            "2025/6": gelir(300, 30),
            "2025/9": gelir(650, 60),
            "2025/12": gelir(1000, 100),
            "2026/3": gelir(1300, 140),
            "2026/6": gelir(350, 45),
        }
        self.assertEqual(mali_yil_sonu_ayi(d), 3)
        # 2026/6 = mali yılın ilk çeyreği: 45 + 140 − 30
        self.assertEqual(son_12_ay(d, "3H", "2026/6", 3), (155, "ttm"))
        self.assertEqual(son_12_ay(d, "3H", "2026/3", 3), (140, "yillik"))

    def test_takvim_yili_tespiti(self):
        self.assertEqual(mali_yil_sonu_ayi(self.d), 12)


class MetrikTestleri(unittest.TestCase):
    def tablo(self, **bilanco):
        b = {"1A": 500, "1AA": 100, "1AB": 50, "2A": 300, "2AA": 120, "2BA": 200,
             "1BG": 400, "1BFAA": 50, "2ODA": 10, "1BL": 1500}
        b.update(bilanco)
        return {
            "2025/6": gelir(400, 80, 20),
            "2025/12": gelir(1000, 300, 50),
            "2026/6": {**gelir(500, 100, 30), **b},
        }

    def test_temel_hesap(self):
        m = sirket_metrikleri(self.tablo(), "2026/6", 1000.0)
        # FVÖK TTM = 100 + 300 − 80 = 320
        self.assertEqual(m["fvok"], 320)
        # NİS = (500 − 150) − (300 − 120) = 170 ; sermaye = 170 + 400 + 50 = 620
        self.assertEqual(m["nis"], 170)
        self.assertEqual(m["sermaye"], 620)
        # FD = 1000 + 320 − 150 + 10 = 1180
        self.assertEqual(m["fd"], 1180)
        self.assertAlmostEqual(m["ey"], 320 / 1180 * 100)
        self.assertAlmostEqual(m["roic"], 320 / 620 * 100)
        # FAVÖK = 320 + (30 + 50 − 20) = 380
        self.assertEqual(m["favok"], 380)
        self.assertNotIn("hata", m)

    def test_tufe_ile_fiyat_tarihine_tasima(self):
        endeks = tufe_endeksi_kur({"2026-06": 1.0, "2026-07": 10.0})
        m = sirket_metrikleri(self.tablo(), "2026/6", 1000.0, endeks, "2026-07")
        self.assertAlmostEqual(m["ey"], 320 * 1.10 / 1180 * 100)
        self.assertAlmostEqual(m["roic"], 320 / 620 * 100)  # ROIC aynı paradan

    def test_negatif_isletme_sermayesi_sifirlanir(self):
        m = sirket_metrikleri(self.tablo(**{"2A": 900, "2AA": 0}), "2026/6", 1000.0)
        self.assertLess(m["nis"], 0)
        self.assertEqual(m["sermaye"], 450)
        self.assertIn("nis_negatif", m["bayraklar"])

    def test_fd_negatif(self):
        m = sirket_metrikleri(self.tablo(**{"1AA": 5000}), "2026/6", 1000.0)
        self.assertIn("hata", m)
        self.assertIn("fd_negatif", m["bayraklar"])

    def test_piyasa_degeri_yok(self):
        self.assertIn("hata", sirket_metrikleri(self.tablo(), "2026/6", 0))

    def test_yatirim_amacli_gayrimenkul_sermayeye_dahil(self):
        m = sirket_metrikleri(self.tablo(**{"1BF": 380}), "2026/6", 1000.0)
        self.assertEqual(m["sermaye"], 1000)

    def test_fvok_marji_esigi(self):
        t = self.tablo()
        for d in t.values():
            d["3C"] = d["3H"]  # satış ≈ FVÖK → yatırım geliri gibi
        self.assertIn("hata", sirket_metrikleri(t, "2026/6", 1000.0))

    def test_cok_kucuk_sermaye(self):
        m = sirket_metrikleri(self.tablo(**{"1BL": 100_000}), "2026/6", 1000.0)
        self.assertIn("hata", m)

    def test_fvok_bilesenlerden(self):
        t = self.tablo()
        del t["2026/6"]["3H"]
        t["2026/6"].update({"3D": 160, "3DA": -40, "3DB": -20, "3DC": 0})
        m = sirket_metrikleri(t, "2026/6", 1000.0)
        self.assertEqual(m["fvok"], 320)
        self.assertIn("fvok_bilesenlerden", m["bayraklar"])

    def test_fvok_bilesenleri_eksikse_turetilmez(self):
        t = self.tablo()
        del t["2026/6"]["3H"]
        t["2026/6"]["3D"] = 160  # gider kalemleri yok
        m = sirket_metrikleri(t, "2026/6", 1000.0)
        self.assertIn("hata", m)

    def test_eksik_son_donem_onceki_ceyrege_duser(self):
        t = self.tablo()
        t["2026/3"] = dict(t["2026/6"])
        t["2026/6"] = {"1A": 500, "2A": 300, "1BL": 1500, "3D": 200}  # yarım işlenmiş
        self.assertTrue(donem_eksik_mi(t, "2026/6"))
        self.assertEqual(kullanilacak_donem(t, "2026/6"), ("2026/3", True))
        self.assertEqual(kullanilacak_donem(self.tablo(), "2026/6"), ("2026/6", False))

    def test_zarar(self):
        t = self.tablo()
        t["2026/6"]["3H"] = -500
        m = sirket_metrikleri(t, "2026/6", 1000.0)
        self.assertLess(m["ey"], 0)
        self.assertIn("zarar", m["bayraklar"])


class SiralamaTestleri(unittest.TestCase):
    def test_esitlik(self):
        self.assertEqual(siralar([10, 20, 20, 5]), [3.0, 1.5, 1.5, 4.0])

    def test_magic_formula(self):
        # Görseldeki örnek: HPQ birleşik sırada 1. olmalı
        veri = [
            ("EXPE", 7.6, 57), ("QCOM", 6.5, 30), ("GDDY", 7.9, 32), ("GEN", 7.9, 9),
            ("ADBE", 9.1, 26), ("HPQ", 10.9, 35), ("GIB", 12.0, 13), ("EPAM", 13.0, 14),
            ("CTSH", 14.2, 15),
        ]
        hisseler = [{"ticker": t, "ey": e, "roic": r} for t, e, r in veri]
        sirali = magic_formula_sirala(hisseler)
        self.assertEqual(sirali[0]["ticker"], "HPQ")
        self.assertEqual(sirali[0]["mf_skor"], 6)
        self.assertAlmostEqual(medyan([h["ey"] for h in hisseler]), 9.1)
        self.assertAlmostEqual(medyan([h["roic"] for h in hisseler]), 26)

    def test_medyan_cift(self):
        self.assertEqual(medyan([1, 2, 3, 4]), 2.5)
        self.assertIsNone(medyan([]))


class KapsamTestleri(unittest.TestCase):
    def test_kapsam(self):
        self.assertIsNone(kapsam_disi_nedeni("XI_29", "XMESY"))
        self.assertIsNone(kapsam_disi_nedeni("XI_29", "XHOLD"))  # holding anahtarla seçilir
        self.assertIsNotNone(kapsam_disi_nedeni("UFRS", "XBANK"))
        self.assertIsNotNone(kapsam_disi_nedeni("XI_29", "XGMYO"))
        self.assertIsNotNone(kapsam_disi_nedeni("XI_29K", "XFINK"))
        self.assertIsNotNone(kapsam_disi_nedeni(None, "XBLSM"))


if __name__ == "__main__":
    unittest.main()
