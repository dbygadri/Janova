"""Tests du noyau : le moins cher d'abord, organes endormis par défaut, réflexes, sommeil, bilan."""

import tempfile
import unittest

from janova.noyau import Janova
from janova.organes import Organe, OrganeCalcul


class OrganeGraphique(Organe):
    """Un faux organe qui aurait besoin de la carte graphique, avec un coût annoncé très bas."""

    nom = "graphique"
    cout = 0
    besoin_gpu = True

    @classmethod
    def reconnait(cls, etape):
        return True

    def traiter(self, etape):
        return "réponse graphique"


class TestNoyau(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.TemporaryDirectory()
        self.janova = Janova(dossier_donnees=self.dossier.name, aide=None)

    def tearDown(self):
        self.dossier.cleanup()

    def test_chaque_etape_va_au_bon_organe(self):
        rapport = self.janova.traiter("calcule 2 + 3, puis mets en majuscules : salut. Ensuite ouvre le fichier")
        self.assertEqual([r.niveau for r in rapport.etapes], ["organe calcul", "organe texte", "aucun"])
        self.assertEqual(rapport.etapes[0].reponse, "2 + 3 = 5")
        self.assertIn("je ne sais pas encore", rapport.texte())

    def test_la_deuxieme_fois_c_est_un_reflexe(self):
        self.janova.traiter("calcule 6 * 7")
        rapport = self.janova.traiter("Calcule 6 * 7 !")
        self.assertEqual(rapport.etapes[0].niveau, "réflexe")
        self.assertEqual(rapport.etapes[0].reponse, "6 * 7 = 42")

    def test_les_reflexes_survivent_a_un_redemarrage(self):
        self.janova.traiter("calcule 6 * 7")
        redemarree = Janova(dossier_donnees=self.dossier.name, aide=None)
        self.assertEqual(redemarree.traiter("calcule 6 * 7").etapes[0].niveau, "réflexe")

    def test_les_organes_dorment_tant_qu_on_n_en_a_pas_besoin(self):
        self.assertEqual(self.janova.organes_eveilles, {})
        self.janova.traiter("calcule 1 + 1")
        self.assertEqual(list(self.janova.organes_eveilles), ["calcul"])  # l'organe texte dort toujours
        self.assertIn("1 organe(s) endormi(s)", self.janova.dormir())
        self.assertEqual(self.janova.organes_eveilles, {})

    def test_la_carte_graphique_passe_en_dernier(self):
        janova = Janova(dossier_donnees=self.dossier.name, organes=[OrganeGraphique, OrganeCalcul], aide=None)
        self.assertEqual(janova.traiter("calcule 1 + 1").etapes[0].niveau, "organe calcul")
        self.assertEqual(janova.traiter("dis bonjour").etapes[0].niveau, "organe graphique")
        self.assertIn("Carte graphique : utilisée par graphique", janova.bilan())

    def test_bilan_de_toutes_les_ressources(self):
        self.janova.traiter("calcule 6 * 7")
        self.janova.traiter("calcule 6 * 7")
        bilan = self.janova.bilan()
        for ressource in ("Électricité", "Mémoire vive", "Carte graphique : non utilisée", "Stockage", "Économisé"):
            self.assertIn(ressource, bilan)


if __name__ == "__main__":
    unittest.main()
