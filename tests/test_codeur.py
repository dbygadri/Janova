"""Tests de l'atelier de code : coder, tester, se corriger, installer, modifier, annuler."""

import json
import tempfile
import unittest
from pathlib import Path

from janova.codeur import Atelier, essayer, verifier_application
from janova.codeur.modeles import MODELES
from janova.conversation import Conversation
from janova.mains import Contexte
from janova.noyau import Janova

APPLI_BONNE = '''def euros_en_dollars(euros, taux=1.1):
    return round(euros * taux, 2)


def main():
    import tkinter as tk
    fenetre = tk.Tk()
    fenetre.mainloop()


def tester():
    assert euros_en_dollars(10) == 11.0
    assert euros_en_dollars(0) == 0
    assert euros_en_dollars(2, 2) == 4


if __name__ == "__main__":
    main()
'''

APPLI_FAUSSE = APPLI_BONNE.replace("round(euros * taux, 2)", "round(euros + taux, 2)")


def reponse(code, nom="Convertisseur"):
    return json.dumps({"nom": nom, "description": "Convertit des euros en dollars", "fenetre": True, "code": code})


class FauxProfesseur:
    nom = "aide extérieure"
    modele = "faux"
    indisponible = ""

    def __init__(self, *reponses):
        self.reponses = list(reponses)
        self.questions = []

    def demander(self, question, en_json=False):
        self.questions.append(question)
        return self.reponses.pop(0) if self.reponses else None


class BaseTest(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.TemporaryDirectory()
        self.racine = Path(self.dossier.name)
        self.maison = self.racine / "maison"
        self.maison.mkdir()

    def tearDown(self):
        self.dossier.cleanup()


class TestVerification(BaseTest):
    def test_les_modeles_passent(self):
        for modele in MODELES.values():
            self.assertIsNone(essayer(modele["code"]), modele["nom"])

    def test_refuse_le_dangereux(self):
        dangereux = {
            "import subprocess": "module interdit : subprocess",
            "import os": "module interdit : os",
            "from urllib import request": "module interdit : urllib",
            "eval('1')": "nom interdit : eval",
            "from pathlib import Path\nPath('x').unlink()": "geste interdit : .unlink",
            "import tkinter": "importe tkinter dans main()",
        }
        for morceau, attendu in dangereux.items():
            code = morceau + "\ndef main(): pass\ndef tester(): pass\nif __name__ == '__main__': main()"
            self.assertIn(attendu, " ".join(verifier_application(code)), morceau)

    def test_l_essai_trouve_les_erreurs(self):
        self.assertIn("Un test échoue", essayer(APPLI_FAUSSE))

    def test_l_essai_ne_touche_pas_au_vrai_dossier_personnel(self):
        self.assertIsNone(essayer(MODELES["bloc-notes"]["code"]))  # écrit dans un faux dossier personnel
        self.assertFalse((Path.home() / ".local/share/janova-apps/bloc-notes.txt").exists()
                         and "essai de Janova" in (Path.home() / ".local/share/janova-apps/bloc-notes.txt").read_text())


class TestAtelier(BaseTest):
    def test_calculatrice_par_reflexe_sans_professeur(self):
        atelier = Atelier(self.racine / "atelier")
        resultat = atelier.creer(self.maison, "crée-moi une calculatrice")
        self.assertIn("sans professeur", resultat.texte)
        self.assertTrue((self.maison / "Applications-Janova/calculatrice/application.py").exists())
        lanceur = (self.maison / ".local/share/applications/janova-calculatrice.desktop").read_text()
        self.assertIn("Name=Calculatrice", lanceur)
        self.assertIn("déjà codé", atelier.creer(self.maison, "fais-moi une calculette").texte)

    def test_sans_professeur_pour_le_nouveau(self):
        resultat = Atelier(self.racine / "atelier").creer(self.maison, "code un jeu de morpion")
        self.assertFalse(resultat.reussi)
        self.assertIn("Ollama", resultat.texte)

    def test_le_professeur_se_corrige_apres_une_erreur(self):
        professeur = FauxProfesseur(reponse(APPLI_FAUSSE), reponse(APPLI_BONNE))
        atelier = Atelier(self.racine / "atelier", professeur)
        resultat = atelier.creer(self.maison, "fais-moi un convertisseur euros dollars")
        self.assertTrue(resultat.reussi, resultat.texte)
        self.assertIn("2 essai(s)", resultat.texte)
        self.assertIn("Un test échoue", professeur.questions[1])  # l'erreur a été renvoyée au professeur

    def test_abandonne_proprement_apres_trop_d_essais(self):
        professeur = FauxProfesseur(*[reponse(APPLI_FAUSSE)] * 4)
        resultat = Atelier(self.racine / "atelier", professeur).creer(self.maison, "fais un convertisseur")
        self.assertFalse(resultat.reussi)
        self.assertFalse((self.maison / "Applications-Janova").exists())  # rien d'installé

    def test_professeur_specialise_puis_general(self):
        absent = FauxProfesseur()  # le modèle de code n'est pas installé : il ne répond rien
        general = FauxProfesseur(reponse(APPLI_BONNE))
        resultat = Atelier(self.racine / "atelier", general, absent).creer(self.maison, "fais un convertisseur")
        self.assertTrue(resultat.reussi)

    def test_modifier_puis_annuler(self):
        nouvelle = APPLI_BONNE.replace("taux=1.1", "taux=1.2").replace("== 11.0", "== 12.0")
        professeur = FauxProfesseur(reponse(APPLI_BONNE), reponse(nouvelle))
        atelier = Atelier(self.racine / "atelier", professeur)
        atelier.creer(self.maison, "fais un convertisseur")
        resultat = atelier.modifier(self.maison, "convertisseur", "mets le taux à 1.2")
        self.assertIn("version 2", resultat.texte)
        fichier = self.maison / "Applications-Janova/convertisseur/application.py"
        self.assertIn("taux=1.2", fichier.read_text())
        self.assertIn("version 1", resultat.annulation())
        self.assertIn("taux=1.1", fichier.read_text())

    def test_annuler_la_creation(self):
        atelier = Atelier(self.racine / "atelier")
        resultat = atelier.creer(self.maison, "crée-moi un minuteur")
        resultat.annulation()
        self.assertFalse((self.maison / "Applications-Janova/minuteur").exists())
        self.assertEqual(atelier.bibliotheque, {})


class TestCodeurDansJanova(BaseTest):
    def test_conversation_complete(self):
        janova = Janova(self.racine / "donnees", aide=None, contexte_systeme=Contexte(self.maison, bureau="gnome"))
        conversation = Conversation(janova)
        self.assertIn("Je propose : coder une application", conversation.recevoir("crée-moi une calculatrice"))
        self.assertIn("J'ai codé et testé « Calculatrice »", conversation.recevoir("oui"))
        self.assertIn("Calculatrice (version 1, réflexe)", conversation.recevoir("/applications"))


if __name__ == "__main__":
    unittest.main()
