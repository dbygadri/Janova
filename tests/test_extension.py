"""Tests du raisonnement (niveau 3), de l'aide extérieure (niveau 4) et de l'auto-extension.

On n'utilise pas une vraie IA : FausseAide renvoie des réponses écrites à l'avance.
"""

import json
import tempfile
import unittest
from pathlib import Path

from janova.aide_exterieure import AideExterieure
from janova.noyau import Janova

CODE_CELSIUS = '''import re

def reconnait(etape):
    return "celsius" in etape.lower() and re.search(r"-?\\d", etape) is not None

def traiter(etape):
    valeur = float(re.findall(r"-?\\d+(?:[.,]\\d+)?", etape)[0].replace(",", "."))
    return f"{valeur * 9 / 5 + 32:g} °F"
'''


def organe_json(code=CODE_CELSIUS):
    return json.dumps({"organe": {
        "nom": "Celsius → Fahrenheit",
        "description": "Convertit des degrés Celsius en Fahrenheit",
        "mots_cles": ["celsius"],
        "code": code,
        "tests": [
            {"etape": "convertis 0 celsius en fahrenheit", "attendu": "32 °F"},
            {"etape": "100 degrés celsius en fahrenheit", "attendu": "212 °F"},
            {"etape": "-40 celsius en fahrenheit", "attendu": "-40 °F"},
        ],
    }})


class FausseAide:
    """Une fausse IA : elle renvoie, dans l'ordre, les réponses qu'on lui a données."""

    nom = "aide extérieure"
    modele = "fausse"
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

    def tearDown(self):
        self.dossier.cleanup()

    def janova(self, aide):
        return Janova(dossier_donnees=self.dossier.name, aide=aide)


class TestRaisonnement(BaseTest):
    def test_relie_une_etape_au_resultat_precedent(self):
        rapport = self.janova(None).traiter(
            "calcule 2 + 3, puis multiplie le résultat par 4. Ensuite ajoute 10 au résultat"
        )
        self.assertEqual([r.reponse for r in rapport.etapes], ["2 + 3 = 5", "5 * 4 = 20", "20 + 10 = 30"])
        self.assertEqual(rapport.etapes[1].niveau, "raisonnement + organe calcul")
        self.assertEqual(rapport.etapes[1].etape, "multiplie le résultat par 4")

    def test_passe_un_resultat_a_un_autre_organe(self):
        rapport = self.janova(None).traiter("écris à l'envers : janova, puis mets ça en majuscules")
        self.assertEqual(rapport.etapes[1].reponse, "AVONAJ")


class TestAutoExtension(BaseTest):
    def test_cree_un_organe_puis_s_en_sert_sans_ia(self):
        aide = FausseAide(organe_json())
        janova = self.janova(aide)

        premier = janova.traiter("convertis 20 celsius en fahrenheit").etapes[0]
        self.assertEqual(premier.reponse, "68 °F")
        self.assertEqual(premier.niveau, "aide extérieure → nouvel organe « celsius_fahrenheit »")

        second = janova.traiter("convertis 37 celsius en fahrenheit").etapes[0]
        self.assertEqual((second.reponse, second.niveau), ("98.6 °F", "organe celsius_fahrenheit"))
        self.assertEqual(len(aide.questions), 1, "la deuxième fois, l'IA ne doit pas être appelée")
        self.assertIn("Carte graphique : utilisée par aide extérieure", janova.bilan())

    def test_l_organe_appris_survit_a_un_redemarrage(self):
        self.janova(FausseAide(organe_json())).traiter("convertis 20 celsius en fahrenheit")
        aide = FausseAide()
        redemarree = self.janova(aide)
        self.assertEqual(redemarree.traiter("50 celsius en fahrenheit").etapes[0].reponse, "122 °F")
        self.assertIn("celsius_fahrenheit (appris, génération 1", redemarree.organes())
        self.assertEqual(aide.questions, [])

    def test_corrige_un_organe_refuse(self):
        faux = organe_json('def reconnait(etape):\n    return True\n\ndef traiter(etape):\n    return "faux"\n')
        aide = FausseAide(faux, organe_json())
        resultat = self.janova(aide).traiter("convertis 20 celsius en fahrenheit").etapes[0]
        self.assertEqual(resultat.reponse, "68 °F")
        self.assertIn("a été refusé", aide.questions[1])  # l'IA a reçu ses erreurs pour corriger

    def test_refuse_le_code_dangereux_et_n_enregistre_rien(self):
        dangereux = organe_json("import os\n\ndef reconnait(etape):\n    return True\n\ndef traiter(etape):\n    return os.getcwd()\n")
        janova = self.janova(FausseAide(dangereux, dangereux, dangereux))
        self.assertEqual(janova.traiter("convertis 20 celsius en fahrenheit").etapes[0].niveau, "aucun")
        self.assertFalse(list(Path(self.dossier.name, "organes_appris").glob("*.json")))

    def test_un_fichier_d_organe_modifie_en_douce_n_est_pas_charge(self):
        self.janova(FausseAide(organe_json())).traiter("convertis 20 celsius en fahrenheit")
        fichier = next(Path(self.dossier.name, "organes_appris").glob("*.json"))
        fiche = json.loads(fichier.read_text(encoding="utf-8"))
        fiche["code"] = "import os\n" + fiche["code"]
        fichier.write_text(json.dumps(fiche), encoding="utf-8")
        self.assertNotIn("celsius_fahrenheit", self.janova(FausseAide()).organes())

    def test_reponse_directe_sans_organe(self):
        aide = FausseAide(json.dumps({"reponse": "Conakry"}), json.dumps({"reponse": "Conakry"}))
        janova = self.janova(aide)
        resultat = janova.traiter("quelle est la capitale de la Guinée ?").etapes[0]
        self.assertEqual((resultat.reponse, resultat.niveau), ("Conakry", "aide extérieure"))
        # Une réponse directe n'est pas vérifiable : elle ne devient pas un réflexe.
        self.assertEqual(janova.traiter("quelle est la capitale de la Guinée ?").etapes[0].niveau, "aide extérieure")

    def test_ia_injoignable(self):
        aide = AideExterieure(url="http://127.0.0.1:1", delai_secondes=2)
        janova = self.janova(aide)
        self.assertEqual(janova.traiter("dis bonjour").etapes[0].niveau, "aucun")
        self.assertIn("injoignable", janova.organes())
        self.assertEqual(janova.traiter("ouvre le fichier").etapes[0].niveau, "aucun")  # sans réessayer


if __name__ == "__main__":
    unittest.main()
