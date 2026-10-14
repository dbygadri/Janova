"""Tests de la mémoire des réflexes : apprendre, retrouver, garder sur le disque, oublier en dormant."""

import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from janova.reflexes import MemoireReflexes


class TestMemoireReflexes(unittest.TestCase):
    def setUp(self):
        # Un dossier temporaire, supprimé après chaque test : les tests ne touchent pas aux vraies données.
        self.dossier = tempfile.TemporaryDirectory()
        self.chemin = Path(self.dossier.name) / "reflexes.json"

    def tearDown(self):
        self.dossier.cleanup()

    def test_retrouve_la_meme_etape_ecrite_autrement(self):
        memoire = MemoireReflexes(self.chemin)
        memoire.apprendre("Calcule 2 + 2", "4", "calcul", 100.0)
        self.assertEqual(memoire.chercher("calcule  2 + 2 !")["reponse"], "4")
        self.assertIsNone(memoire.chercher("calcule 3 + 3"))

    def test_garde_les_reflexes_apres_fermeture(self):
        memoire = MemoireReflexes(self.chemin)
        memoire.apprendre("calcule 2 + 2", "4", "calcul", 100.0)
        memoire.sauvegarder()
        self.assertEqual(MemoireReflexes(self.chemin).chercher("calcule 2 + 2")["reponse"], "4")

    def test_le_sommeil_oublie_seulement_les_vieux_reflexes_jamais_reutilises(self):
        memoire = MemoireReflexes(self.chemin)
        il_y_a_un_an = (datetime.now() - timedelta(days=365)).isoformat(timespec="seconds")
        for etape in ("vieux inutile", "vieux utile", "récent"):
            memoire.apprendre(etape, "r", "calcul", 1.0)
        memoire.reflexes["vieux inutile"]["derniere_utilisation"] = il_y_a_un_an
        memoire.chercher("vieux utile")
        memoire.reflexes["vieux utile"]["derniere_utilisation"] = il_y_a_un_an

        self.assertEqual(memoire.consolider(oubli_apres_jours=30), 1)
        self.assertEqual(sorted(memoire.reflexes), ["récent", "vieux utile"])

    def test_fichier_abime_ne_fait_pas_planter(self):
        self.chemin.write_text("{ ceci n'est pas du JSON", encoding="utf-8")
        self.assertEqual(len(MemoireReflexes(self.chemin)), 0)
        self.assertTrue(self.chemin.with_suffix(".abime").exists())


if __name__ == "__main__":
    unittest.main()
