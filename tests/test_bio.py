"""Tests des mécanismes bio-inspirés : neurones à impulsions, homéostasie, attention, évolution."""

import json
import tempfile
import unittest
from pathlib import Path

from janova.attention import Attention
from janova.extension.evolution import evoluer, note
from janova.homeostasie import ECONOMIE, NORMAL, SURVIE, Homeostasie, SignesVitaux, choisir_mode
from janova.noyau import Janova
from janova.organes.neurones import ReseauImpulsions, reseau
from tests.test_extension import FausseAide, organe_json


class TestNeurones(unittest.TestCase):
    def test_reconnait_les_intentions(self):
        attendus = {
            "bonjour": "salutation", "Bonjour Janova !": "salutation", "comment vas-tu": "etat",
            "merci beaucoup": "remerciement", "à bientôt": "au_revoir", "qui es-tu": "identite",
            "tu es génial": "compliment",
        }
        for phrase, intention in attendus.items():
            self.assertEqual(reseau().reconnaitre(phrase), intention, phrase)

    def test_les_mots_inconnus_freinent(self):
        # « bonjour » est connu, mais les autres mots inhibent les sorties : ce n'est pas une salutation.
        for phrase in ("bonjour, calcule 2 + 2", "mets en majuscules : bonjour", "comment ça marche la photosynthèse"):
            self.assertIsNone(reseau().reconnaitre(phrase), phrase)

    def test_silence_sans_mot_connu(self):
        petit = ReseauImpulsions({"oui": ["oui"]})
        self.assertIsNone(petit.reconnaitre("calcule 2 + 2"))
        self.assertEqual(petit.impulsions, 0)  # aucun neurone n'a travaillé

    def test_dans_janova(self):
        with tempfile.TemporaryDirectory() as dossier:
            rapport = Janova(dossier, aide=None).traiter("Bonjour ! Comment vas-tu ?")
            self.assertEqual([r.niveau for r in rapport.etapes], ["organe social", "organe social"])


class FauxCapteurs:
    def __init__(self, signes):
        self.signes = signes

    def __call__(self):
        return self.signes


class TestHomeostasie(unittest.TestCase):
    def test_choix_du_mode(self):
        self.assertEqual(choisir_mode(SignesVitaux())[0], NORMAL)  # aucun capteur : rien ne déclenche
        self.assertEqual(choisir_mode(SignesVitaux(batterie=25, sur_secteur=False))[0], ECONOMIE)
        self.assertEqual(choisir_mode(SignesVitaux(batterie=5, sur_secteur=False))[0], SURVIE)
        self.assertEqual(choisir_mode(SignesVitaux(batterie=5, sur_secteur=True))[0], NORMAL)  # branché
        self.assertEqual(choisir_mode(SignesVitaux(memoire_libre_mo=300))[0], ECONOMIE)
        self.assertEqual(choisir_mode(SignesVitaux(temperature=95))[0], SURVIE)

    def janova(self, dossier, signes, aide):
        return Janova(dossier, aide=aide, homeostasie=Homeostasie(FauxCapteurs(signes)))

    def test_economie_coupe_l_aide_exterieure_sauf_urgence(self):
        with tempfile.TemporaryDirectory() as dossier:
            aide = FausseAide(json.dumps({"reponse": "Conakry"}))
            janova = self.janova(dossier, SignesVitaux(batterie=20, sur_secteur=False), aide)
            rapport = janova.traiter("quelle est la capitale de la Guinée")
            self.assertEqual(rapport.etapes[0].niveau, "aucun")
            self.assertIn("Mode économie", rapport.texte())
            self.assertEqual(aide.questions, [])
            # L'urgence (« adrénaline ») débloque l'aide extérieure en mode économie.
            urgent = janova.traiter("urgent : quelle est la capitale de la Guinée")
            self.assertEqual(urgent.etapes[0].reponse, "Conakry")

    def test_survie_ne_garde_que_l_essentiel(self):
        with tempfile.TemporaryDirectory() as dossier:
            Janova(dossier, aide=FausseAide(organe_json())).traiter("convertis 20 celsius en fahrenheit")
            janova = self.janova(dossier, SignesVitaux(batterie=5, sur_secteur=False), FausseAide())
            # L'organe appris est en pause, même en urgence ; le calcul (organe de base) marche toujours.
            self.assertEqual(janova.traiter("urgent : 50 celsius en fahrenheit").etapes[0].niveau, "aucun")
            self.assertEqual(janova.traiter("calcule 2 + 2").etapes[0].niveau, "organe calcul")
            self.assertIn("Mode survie", janova.etat())


class FausseHorloge:
    def __init__(self):
        self.maintenant = 0.0

    def __call__(self):
        return self.maintenant


class TestAttention(unittest.TestCase):
    def test_habituation_puis_desaccoutumance(self):
        horloge = FausseHorloge()
        with tempfile.TemporaryDirectory() as dossier:
            janova = Janova(dossier, aide=None, attention=Attention(horloge))
            niveaux = [janova.traiter("calcule 6 * 7").etapes[0].niveau for _ in range(3)]
            self.assertEqual(niveaux, ["organe calcul", "réflexe", "habituation"])
            horloge.maintenant += 120  # deux minutes plus tard, l'habituation est passée
            self.assertEqual(janova.traiter("calcule 6 * 7").etapes[0].niveau, "réflexe")

    def test_urgence(self):
        self.assertTrue(Attention().est_urgente("Vite, calcule 2 + 2"))
        self.assertFalse(Attention().est_urgente("calcule 2 + 2"))


class TestEvolution(unittest.TestCase):
    POSITIFS = ["convertis 0 celsius en fahrenheit", "100 degrés celsius en fahrenheit", "convertis 20 celsius"]
    NEGATIFS = ["convertis 20 fahrenheit en kelvin", "la température du four en fahrenheit"]

    def test_corrige_les_fausses_alertes_sans_rien_perdre(self):
        nouveaux = evoluer(["fahrenheit"], self.POSITIFS, self.NEGATIFS)
        reconnus, _ = note(nouveaux, self.POSITIFS, self.NEGATIFS)
        self.assertEqual(reconnus, len(self.POSITIFS))  # aucune étape réussie perdue
        self.assertFalse(any(m in "convertis 20 fahrenheit en kelvin" for m in nouveaux))

    def test_rien_a_corriger(self):
        self.assertIsNone(evoluer(["celsius"], self.POSITIFS, []))

    def test_pendant_le_sommeil(self):
        with tempfile.TemporaryDirectory() as dossier:
            organe = json.loads(organe_json())
            organe["organe"]["mots_cles"] = ["celsius", "convertis"]  # « convertis » : trop large
            janova = Janova(dossier, aide=FausseAide(json.dumps(organe)))
            janova.traiter("convertis 20 celsius en fahrenheit")
            # Fausse alerte : « convertis » réveille l'organe pour une étape qui n'est pas pour lui.
            self.assertEqual(janova.traiter("convertis 3 kilomètres en miles").etapes[0].niveau, "aucun")
            self.assertIn("1 organe(s) appris amélioré(s)", janova.dormir())
            fiche = json.loads(next(Path(dossier, "organes_appris").glob("*.json")).read_text(encoding="utf-8"))
            self.assertEqual((fiche["mots_cles"], fiche["generation"]), (["celsius"], 2))
            self.assertIn("génération 2", janova.organes())


if __name__ == "__main__":
    unittest.main()
