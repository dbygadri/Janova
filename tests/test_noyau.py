from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from janova.config import load_config
from janova.core import Janova
from janova.meaning import EmbedderError
from janova.sandbox import check_code, run_skill
from janova.store import Store
from janova.teachers import Entourage, TeacherError, extract_json

CELSIUS_CODE = '''import re

def run(demande):
    valeur = float(re.findall(r"-?\\d+(?:[.,]\\d+)?", demande)[0].replace(",", "."))
    return f"{valeur * 9 / 5 + 32:g} °F"
'''

CELSIUS_LESSON = {
    "nom": "celsius_vers_fahrenheit",
    "description": "Convertit des degrés Celsius en Fahrenheit",
    "code": CELSIUS_CODE,
    "tests": [
        {"entree": "convertis 0 celsius en fahrenheit", "attendu": "32 °F"},
        {"entree": "100 degrés celsius en fahrenheit ?", "attendu": "212 °F"},
        {"entree": "combien font -40 celsius en fahrenheit", "attendu": "-40 °F"},
    ],
}


class FakeTeacher:
    """Professeur scripté : renvoie des réponses selon le type de question posée."""

    def __init__(self, name="faux", kind="competence", lessons=None, fact="Paris est la capitale de la France."):
        self.name = name
        self.kind = kind
        self.lessons = list(lessons or [CELSIUS_LESSON])
        self.fact = fact
        self.calls = 0

    def ask(self, prompt, system=""):
        self.calls += 1
        if prompt.startswith("Classe la demande"):
            return json.dumps({"type": self.kind})
        if prompt.startswith("Écris une compétence"):
            lesson = self.lessons.pop(0) if len(self.lessons) > 1 else self.lessons[0]
            return "Voici :\n```json\n" + json.dumps(lesson) + "\n```"
        if prompt.startswith("Réponds à cette question factuelle"):
            return self.fact
        return "Bonjour !"


class DeadTeacher:
    name = "mort"

    def ask(self, prompt, system=""):
        raise TeacherError("injoignable")


class BaseCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.config = load_config(self.tmp.name)

    def tearDown(self):
        for janova in getattr(self, "_janovas", []):
            janova.close()
        self.tmp.cleanup()

    def make(self, *teachers, embedder=None):
        janova = Janova(self.config, entourage=Entourage(list(teachers)), embedder=embedder)
        self._janovas = getattr(self, "_janovas", []) + [janova]
        return janova


class SandboxTest(unittest.TestCase):
    def test_refuse_dangerous_code(self):
        self.assertTrue(check_code("import os\ndef run(d):\n    return os.getcwd()"))
        self.assertTrue(check_code("def run(d):\n    return open('x').read()"))
        self.assertTrue(check_code("def run(d):\n    return ().__class__.__bases__"))
        self.assertTrue(check_code("def autre(d):\n    return d"))

    def test_runs_good_code(self):
        results = run_skill(CELSIUS_CODE, ["20 celsius", "rien"], timeout=10)
        self.assertEqual((results[0].ok, results[0].output), (True, "68 °F"))
        self.assertFalse(results[1].ok)

    def test_timeout(self):
        results = run_skill("def run(d):\n    while True:\n        pass", ["x"], timeout=1)
        self.assertFalse(results[0].ok)
        self.assertIn("Temps", results[0].output)

    def test_print_does_not_break_output(self):
        results = run_skill("def run(d):\n    print('bruit')\n    return 'ok'", ["x"], timeout=10)
        self.assertEqual(results[0].output, "ok")


class JournalTest(unittest.TestCase):
    def test_chain_detects_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / "j.db")
            skill = store.add_skill("s", "d", CELSIUS_CODE, ["ex"], teacher="t")
            store.add_fact("q", "r", sources=2, agreement=1.0)
            self.assertEqual(store.verify(), [])

            store.db.execute("UPDATE skills SET code = 'def run(d): return 1' WHERE id = ?", (skill.id,))
            self.assertTrue(any("Compétence" in p for p in store.verify()))
            store.db.execute("UPDATE skills SET code = ? WHERE id = ?", (CELSIUS_CODE, skill.id))

            store.db.execute("UPDATE journal SET payload = '{}' WHERE id = 1")
            self.assertTrue(any("modifiée" in p for p in store.verify()))
            store.close()


class LearningTest(BaseCase):
    def test_learns_skill_then_works_without_teacher(self):
        teacher = FakeTeacher()
        janova = self.make(teacher)

        first = janova.handle("convertis 20 celsius en fahrenheit")
        self.assertEqual(first.route, "apprend-competence")
        self.assertIn("68 °F", first.text)

        calls = teacher.calls
        second = janova.handle("convertis 37 celsius en fahrenheit")
        self.assertEqual((second.route, second.text), ("competence", "98.6 °F"))
        self.assertEqual(teacher.calls, calls, "la compétence doit marcher sans professeur")
        self.assertIn("Taux d'autonomie : 50 %", janova.handle("/etat").text)
        self.assertIn("Intégrité vérifiée", janova.handle("/verifier").text)

    def test_retries_when_tests_fail(self):
        broken = dict(CELSIUS_LESSON, code="def run(demande):\n    return 'faux'")
        teacher = FakeTeacher(lessons=[broken, CELSIUS_LESSON])
        reply = self.make(teacher).handle("convertis 20 celsius en fahrenheit")
        self.assertEqual(reply.route, "apprend-competence")

    def test_gives_up_and_converses_when_skill_never_passes(self):
        broken = dict(CELSIUS_LESSON, code="def run(demande):\n    return 'faux'")
        reply = self.make(FakeTeacher(lessons=[broken])).handle("convertis 20 celsius en fahrenheit")
        self.assertEqual(reply.route, "professeur")

    def test_negative_feedback_disables_skill(self):
        janova = self.make(FakeTeacher())
        janova.handle("convertis 20 celsius en fahrenheit")
        janova.handle("convertis 30 celsius en fahrenheit")
        janova.handle("/mauvais")
        janova.handle("convertis 40 celsius en fahrenheit")
        self.assertIn("j'abandonne", janova.handle("/mauvais").text)
        self.assertIn("Aucune compétence", janova.handle("/competences").text)

    def test_fact_by_consensus(self):
        janova = self.make(FakeTeacher("a", kind="connaissance"), FakeTeacher("b", kind="connaissance"))
        first = janova.handle("Quelle est la capitale de la France ?")
        self.assertEqual(first.route, "apprend-connaissance")
        second = janova.handle("quelle est la capitale de la france")
        self.assertEqual(second.route, "memoire")
        self.assertIn("Paris", second.text)

    def test_disagreement_is_not_memorized(self):
        janova = self.make(
            FakeTeacher("a", kind="connaissance", fact="Le mont Blanc mesure 4806 mètres."),
            FakeTeacher("b", kind="connaissance", fact="JE NE SAIS PAS"),
            FakeTeacher("c", kind="connaissance", fact="Aucune idée, désolé."),
        )
        reply = janova.handle("Quelle est la hauteur du mont Blanc ?")
        self.assertEqual(reply.route, "professeur")
        self.assertIn("Aucune connaissance", janova.handle("/connaissances").text)

    def test_without_teachers(self):
        self.assertEqual(self.make().handle("bonjour").route, "inconnu")
        self.assertEqual(self.make(DeadTeacher()).handle("bonjour").route, "inconnu")

    def test_memory_persists_across_restarts(self):
        self.make(FakeTeacher()).handle("convertis 20 celsius en fahrenheit")
        reborn = self.make()
        self.assertEqual(reborn.handle("convertis 50 celsius en fahrenheit").text, "122 °F")


class FakeEmbedder:
    """Modèle de sens simulé : une dimension par thème, plus une dimension commune."""

    name = "faux-sens"
    THEMES = [("celsius", "fahrenheit", "°c", "temperature", "température", "degres", "degrés"), ("capitale",)]

    def __init__(self):
        self.embedded = []

    def embed(self, texts):
        self.embedded += texts
        return [[sum(w in t.lower() for w in theme) for theme in self.THEMES] + [0.3] for t in texts]


class BrokenEmbedder:
    name = "casse"

    def __init__(self):
        self.calls = 0

    def embed(self, texts):
        self.calls += 1
        raise EmbedderError("injoignable")


class MeaningTest(BaseCase):
    QUESTION = "Quelle température en Fahrenheit pour 25 °C ?"

    def test_words_alone_do_not_recognize_reformulation(self):
        teacher = FakeTeacher()
        janova = self.make(teacher)
        janova.handle("convertis 20 celsius en fahrenheit")
        self.assertNotEqual(janova.handle(self.QUESTION).route, "competence")

    def test_meaning_recognizes_reformulation(self):
        teacher, embedder = FakeTeacher(), FakeEmbedder()
        janova = self.make(teacher, embedder=embedder)
        janova.handle("convertis 20 celsius en fahrenheit")
        calls = teacher.calls
        reply = janova.handle(self.QUESTION)
        self.assertEqual((reply.route, reply.text), ("competence", "77 °F"))
        self.assertEqual(teacher.calls, calls)
        self.assertIn("par le sens (faux-sens)", janova.handle("/etat").text)

    def test_meaning_does_not_match_unrelated(self):
        janova = self.make(FakeTeacher(kind="conversation"), embedder=FakeEmbedder())
        janova.handle("convertis 20 celsius en fahrenheit")
        self.assertEqual(janova.handle("bonjour, comment vas-tu ?").route, "professeur")

    def test_vectors_are_cached(self):
        embedder = FakeEmbedder()
        janova = self.make(FakeTeacher(), embedder=embedder)
        janova.handle("convertis 20 celsius en fahrenheit")
        janova.handle(self.QUESTION)
        before = len(embedder.embedded)
        janova.handle(self.QUESTION)
        self.assertEqual(len(embedder.embedded), before)

    def test_falls_back_to_words_when_model_is_down(self):
        embedder = BrokenEmbedder()
        janova = self.make(FakeTeacher(), embedder=embedder)
        janova.handle("convertis 20 celsius en fahrenheit")
        self.assertEqual(janova.handle("convertis 30 celsius en fahrenheit").route, "competence")
        self.assertEqual(embedder.calls, 1)
        self.assertIn("par les mots seulement (injoignable)", janova.handle("/etat").text)


class JsonTest(unittest.TestCase):
    def test_extract_json(self):
        self.assertEqual(extract_json('bla {"type": "competence"} bla'), {"type": "competence"})
        with self.assertRaises(TeacherError):
            extract_json("pas de json")


if __name__ == "__main__":
    unittest.main()
