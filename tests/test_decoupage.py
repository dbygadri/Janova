"""Tests du découpage en étapes.

Pour les lancer : python -m unittest
Chaque fonction qui commence par « test_ » vérifie un cas précis.
"""

import unittest

from janova.noyau import decouper_en_etapes


class TestDecoupage(unittest.TestCase):
    def test_mots_de_liaison_et_ponctuation(self):
        tache = "Ouvre le fichier, puis lis la première ligne. Ensuite compte les mots, et enfin affiche le résultat."
        self.assertEqual(
            decouper_en_etapes(tache),
            ["Ouvre le fichier", "lis la première ligne", "compte les mots", "affiche le résultat"],
        )

    def test_majuscules_ignorees(self):
        self.assertEqual(decouper_en_etapes("Range la chambre. Puis fais la vaisselle"),
                         ["Range la chambre", "fais la vaisselle"])

    def test_tache_simple(self):
        self.assertEqual(decouper_en_etapes("Dis bonjour"), ["Dis bonjour"])

    def test_tache_vide(self):
        self.assertEqual(decouper_en_etapes("   "), [])

    def test_mot_contenant_puis_non_coupe(self):
        # « depuis » contient « puis », mais ce n'est pas un mot de liaison.
        self.assertEqual(decouper_en_etapes("Lis les messages reçus depuis hier"),
                         ["Lis les messages reçus depuis hier"])


if __name__ == "__main__":
    unittest.main()
