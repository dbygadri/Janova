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
        self.assertEqual(summary["autonomie_variantes"], (1, 1))
        self.assertEqual(summary["competences_apprises"], (1, 1))
        info = {"date": "d", "professeurs": ["faux"], "sens": "aucun", "demandes": 1, "duree_minutes": 0}
        self.assertIn("**1/1 (100 %)**", markdown(info, summary, results))


if __name__ == "__main__":
    unittest.main()
