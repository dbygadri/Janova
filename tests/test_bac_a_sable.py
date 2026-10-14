"""Tests du bac à sable : le code dangereux doit être refusé, le code correct exécuté, les boucles infinies arrêtées."""

import unittest

from janova.extension.bac_a_sable import executer, verifier_code

BON_CODE = '''
def reconnait(etape):
    return "bonjour" in etape

def traiter(etape):
    return etape.upper() + " °"
'''


class TestBacASable(unittest.TestCase):
    def test_refuse_le_code_dangereux(self):
        dangereux = [
            "import os\ndef reconnait(e): return True\ndef traiter(e): return os.getcwd()",
            "def reconnait(e): return True\ndef traiter(e): return open('x').read()",
            "def reconnait(e): return True\ndef traiter(e): return ().__class__.__bases__",
            "def reconnait(e): return True\ndef traiter(e): return eval('1+1')",
            "def reconnait(e): return True",  # il manque traiter()
        ]
        for code in dangereux:
            self.assertTrue(verifier_code(code), code)
            self.assertFalse(executer(code, ["x"])[0][0], code)

    def test_accepte_le_code_correct_et_les_accents(self):
        self.assertEqual(verifier_code(BON_CODE), [])
        self.assertEqual(executer(BON_CODE, ["bonjour éléphant", "rien"]),
                         [(True, "BONJOUR ÉLÉPHANT °"), (False, "étape non reconnue")])

    def test_arrete_les_boucles_infinies(self):
        code = "def reconnait(e): return True\ndef traiter(e):\n    while True:\n        pass"
        ok, explication = executer(code, ["x"], delai_secondes=1)[0]
        self.assertFalse(ok)
        self.assertIn("trop long", explication)


if __name__ == "__main__":
    unittest.main()
