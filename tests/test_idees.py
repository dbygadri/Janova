"""Tests des décisions rapides (façon Jev), du carnet d'idées et de la croissance."""

import json
import tempfile
import unittest
from pathlib import Path

from janova.croissance import Croissance, qui_a_resolu
from janova.decision import Decideur
from janova.idees import A_TRIER, CarnetIdees
from janova.noyau import Janova


class FauxProfesseur:
    """Une fausse IA qui répond toujours la même catégorie, et compte combien de fois on l'a appelée."""

    nom = "aide extérieure"
    modele = "faux"
    indisponible = ""

    def __init__(self, categorie):
        self.categorie = categorie
        self.appels = 0

    def demander(self, question, en_json=False):
        self.appels += 1
        return json.dumps({"categorie": self.categorie})


class BaseTest(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.TemporaryDirectory()
        self.racine = Path(self.dossier.name)

    def tearDown(self):
        self.dossier.cleanup()


class TestDecideur(BaseTest):
    def test_choisit_l_option_qui_a_vu_ces_mots(self):
        decideur = Decideur()
        decideur.enseigner("urgent ?", "le client attend une réponse avant ce soir, vite", "oui")
        decideur.enseigner("urgent ?", "newsletter du mois, à lire un jour", "non")
        decision = decideur.oui_non("urgent ?", "répondre vite au client")
        self.assertEqual(decision.choix, "oui")
        self.assertGreater(decision.confiance, 0.5)

    def test_la_reponse_est_toujours_une_option_permise(self):
        decision = Decideur().noter("importance", "texte sans rapport", ["basse", "moyenne", "haute"])
        self.assertIn(decision.choix, ["basse", "moyenne", "haute"])
        self.assertAlmostEqual(sum(decision.probabilites.values()), 1.0)
        self.assertFalse(decision.sure)  # sans exemple, 33 % : Janova sait qu'elle ne sait pas

    def test_sans_option_pas_de_decision(self):
        self.assertIsNone(Decideur().choisir("categorie", "une idée"))

    def test_garde_ses_connaissances_sur_le_disque(self):
        chemin = self.racine / "decisions.json"
        decideur = Decideur(chemin)
        decideur.enseigner("q", "pomme banane", "fruit")
        decideur.sauvegarder()
        self.assertEqual(Decideur(chemin).options("q"), ["fruit"])


class TestCarnetIdees(BaseTest):
    def carnet(self, aide=None):
        return CarnetIdees(self.racine / "idees", Decideur(self.racine / "decisions.json"), aide)

    def test_categorie_donnee_par_toi(self):
        idee = self.carnet().ranger("alkestore : ajouter le paiement mobile")
        self.assertEqual((idee.categorie, idee.rangee_par, idee.texte), ("alkestore", "toi", "ajouter le paiement mobile"))

    def test_sans_professeur_l_idee_inconnue_est_a_trier(self):
        idee = self.carnet().ranger("une idée sur un sujet jamais vu")
        self.assertEqual(idee.categorie, A_TRIER)

    def test_le_professeur_enseigne_puis_le_reflexe_prend_le_relais(self):
        professeur = FauxProfesseur("immobilier")
        carnet = self.carnet(professeur)
        carnet.ranger("janova : ajouter des réflexes de décision")
        premiere = carnet.ranger("acheter un studio locatif avec la SCI")
        self.assertEqual((premiere.categorie, premiere.rangee_par), ("immobilier", "professeur"))
        seconde = carnet.ranger("trouver un studio locatif moins cher pour la SCI")
        self.assertEqual((seconde.categorie, seconde.rangee_par), ("immobilier", "réflexe"))
        self.assertEqual(professeur.appels, 1)  # la leçon a été retenue : plus besoin du professeur

    def test_idees_proches_reliees_dans_les_deux_sens(self):
        carnet = self.carnet()
        carnet.ranger("alkestore : paiement mobile pour la boutique")
        idee = carnet.ranger("alkestore : paiement mobile sécurisé pour la boutique")
        self.assertEqual(idee.liens, [1])
        notes = sorted((self.racine / "idees").glob("*.md"))
        self.assertEqual(len(notes), 2)
        self.assertIn("[[0002-", notes[0].read_text(encoding="utf-8"))  # la 1re note pointe vers la 2e

    def test_ta_correction_devient_une_lecon(self):
        carnet = self.carnet()
        carnet.ranger("alkestore : boutique en ligne")
        carnet.ranger("une idée pas claire du tout")
        self.assertIn("rangée dans « janova »", carnet.classer(2, "janova"))
        self.assertIn("janova", carnet.decideur.options("categorie"))
        self.assertIn("Je ne trouve pas", carnet.classer(99, "x"))

    def test_garde_les_idees_apres_fermeture(self):
        self.carnet().ranger("alkestore : ajouter le paiement mobile")
        self.assertEqual(len(self.carnet()), 1)


class TestCroissance(BaseTest):
    def test_qui_a_resolu(self):
        self.assertEqual(qui_a_resolu("réflexe"), "seule")
        self.assertEqual(qui_a_resolu("raisonnement + organe calcul"), "seule")
        self.assertEqual(qui_a_resolu("aide extérieure → nouvel organe « x »"), "professeur")
        self.assertEqual(qui_a_resolu("aucun"), "echec")

    def test_stades_de_vie(self):
        croissance = Croissance(self.racine / "croissance.json")
        for _ in range(10):
            croissance.noter("réflexe")
        self.assertEqual(croissance.stade, "bébé")  # trop peu d'expérience pour juger
        for _ in range(10):
            croissance.noter("aide extérieure")
        self.assertEqual(croissance.stade, "enfant")  # 50 %
        for _ in range(80):
            croissance.noter("organe calcul")
        self.assertEqual(croissance.stade, "adulte")  # 90 %

    def test_janova_note_chaque_etape(self):
        janova = Janova(self.racine, aide=None)
        janova.traiter("calcule 2 + 2, puis ouvre le fichier")
        janova.ranger_idee("alkestore : paiement mobile")
        self.assertEqual(janova.croissance.compteurs, {"seule": 2, "professeur": 0, "echec": 1})
        self.assertIn("Stade : bébé", janova.etat_croissance())


if __name__ == "__main__":
    unittest.main()
