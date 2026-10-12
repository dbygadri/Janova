from __future__ import annotations

import unittest

from bench.__main__ import CountingTeacher, is_correct, markdown, run_request, summarize
from janova.teachers import Entourage
from tests.test_noyau import BaseCase, FakeTeacher


class IsCorrectTest(unittest.TestCase):
    def test_numbers_accents_and_decimal_comma(self):
        self.assertTrue(is_correct("Cela fait 26,1 miles.", ["26.1"]))
        self.assertTrue(is_correct("enohpélét", ["enohpelet"]))
        self.assertFalse(is_correct("41 jours", ["40"]))

    def test_numbers_must_be_whole_numbers(self):
        self.assertFalse(is_correct("La racine vaut 250", ["25"]))
        self.assertFalse(is_correct("Cela fait 126.1 miles", ["26.1"]))
        self.assertFalse(is_correct("Résultat : 1.25", ["25"]))
        self.assertFalse(is_correct("Résultat : 25.5", ["25"]))
        self.assertTrue(is_correct("La racine carrée de 625 est 25.", ["25"]))
        self.assertTrue(is_correct("95.0 °F", ["95"]))
        self.assertTrue(is_correct("26.10 miles", ["26.1"]))
        self.assertTrue(is_correct("-40 °F", ["-40"]))

    def test_short_words_must_be_whole_words(self):
        self.assertTrue(is_correct("Le symbole de l'or est Au.", ["au"]))
        self.assertFalse(is_correct("Il fait beau aujourd'hui", ["au"]))


class BenchRunTest(BaseCase):
    def test_learning_then_variant_is_counted_as_autonomous(self):
        teachers = [CountingTeacher(FakeTeacher())]
        janova = self.make(*teachers)
        janova.entourage = Entourage(teachers)
        item = {
            "categorie": "competence",
            "apprentissage": "convertis 20 celsius en fahrenheit",
            "variante": "convertis 35 celsius en fahrenheit",
            "contient": ["95"],
        }
        results = [run_request(janova, teachers, item, phase) for phase in ("apprentissage", "variante")]
        self.assertEqual(results[0]["route"], "apprend-competence")
        self.assertGreater(results[0]["appels_professeurs"], 0)
        self.assertIn("acceptée", results[0]["trace"][-1])
        self.assertEqual((results[1]["route"], results[1]["juste"], results[1]["appels_professeurs"]), ("competence", True, 0))

        summary = summarize(results)
        self.assertEqual(results[0]["classement"], "competence")
        self.assertEqual(summary["classement_correct"], (1, 1))
        self.assertEqual(summary["autonomie_variantes"], (1, 1))
        self.assertEqual(summary["competences_apprises"], (1, 1))
        info = {"date": "d", "professeurs": ["faux"], "sens": "aucun", "demandes": 1, "duree_minutes": 0}
        self.assertIn("**1/1 (100 %)**", markdown(info, summary, results))


class ClassificationTest(BaseCase):
    def test_good_classification_with_failed_learning_is_not_a_misclassification(self):
        broken = {"nom": "x", "description": "", "code": "def run(demande):\n    return 'faux'",
                  "tests": [{"entree": "a", "attendu": "b"}] * 3}
        teachers = [CountingTeacher(FakeTeacher(lessons=[broken]))]
        janova = self.make(*teachers)
        item = {"categorie": "competence", "apprentissage": "convertis 20 celsius en fahrenheit", "variante": "x"}
        result = run_request(janova, teachers, item, "apprentissage")
        self.assertEqual((result["route"], result["classement"]), ("professeur", "competence"))
        self.assertEqual(summarize([result])["classement_correct"], (1, 1))


if __name__ == "__main__":
    unittest.main()
