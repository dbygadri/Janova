"""Tests des organes : chacun doit reconnaître ses étapes, les traiter, et refuser le reste."""

import unittest

from janova.organes import OrganeCalcul, OrganeTexte


class TestOrganeCalcul(unittest.TestCase):
    def test_calculs(self):
        organe = OrganeCalcul()
        self.assertEqual(organe.traiter("calcule 12 * (3 + 4)"), "12 * (3 + 4) = 84")
        self.assertEqual(organe.traiter("combien font 7 fois 6 ?"), "7 * 6 = 42")
        self.assertEqual(organe.traiter("2,5 plus 1,5"), "2.5 + 1.5 = 4")
        self.assertEqual(organe.traiter("10 divisé par 4"), "10 / 4 = 2.5")

    def test_ne_reconnait_pas_ce_qui_n_est_pas_un_calcul(self):
        self.assertFalse(OrganeCalcul.reconnait("dis bonjour"))
        self.assertFalse(OrganeCalcul.reconnait("lis les messages reçus depuis 2020"))

    def test_refuse_le_code_et_les_calculs_dangereux(self):
        organe = OrganeCalcul()
        self.assertFalse(OrganeCalcul.reconnait('__import__("os").system("ls")'))
        self.assertIsNone(organe.traiter("calcule 1 / 0"))
        self.assertIsNone(organe.traiter("9 ** 99999999"))  # bloquerait la machine


class TestOrganeTexte(unittest.TestCase):
    def test_transformations(self):
        organe = OrganeTexte()
        self.assertEqual(organe.traiter("mets en majuscules : bonjour janova"), "BONJOUR JANOVA")
        self.assertEqual(organe.traiter("écris en minuscules : SALUT"), "salut")
        self.assertEqual(organe.traiter("compte les mots : le chat dort"), "3 mots")
        self.assertEqual(organe.traiter("écris à l'envers : janova"), "avonaj")
        self.assertEqual(organe.traiter("mets « le robot » en majuscules"), "LE ROBOT")

    def test_a_besoin_d_un_texte_vise(self):
        self.assertFalse(OrganeTexte.reconnait("mets en majuscules"))
        self.assertFalse(OrganeTexte.reconnait("calcule 2 fois 3"))


if __name__ == "__main__":
    unittest.main()
