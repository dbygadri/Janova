"""Tests du pont : le bureau fait retenir une réponse de Claude, puis le noyau la sert seul."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]


class TestPontApprendre(unittest.TestCase):
    def setUp(self):
        # Une mémoire temporaire : les tests ne touchent pas à la vraie mémoire de Janova.
        self.dossier = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.dossier.cleanup()

    def pont(self, demande: dict) -> dict:
        """Appelle le pont comme le fait le bureau : du JSON en entrée, du JSON en sortie."""
        sortie = subprocess.run(
            [sys.executable, "-m", "janova.pont"],
            input=json.dumps(demande), capture_output=True, text=True, cwd=RACINE, timeout=30,
            env={**os.environ, "JANOVA_MEMOIRE": self.dossier.name},
        )
        self.assertEqual(sortie.returncode, 0, sortie.stderr)
        return json.loads(sortie.stdout)

    def test_question_inconnue_puis_apprise_puis_servie_par_le_noyau(self):
        question = "C'est quoi un serveur DNS ?"
        reponse = "Un annuaire d'Internet : il traduit un nom de site en adresse."
        self.assertIsNone(self.pont({"message": question})["reponse"])
        self.assertEqual(self.pont({"apprendre": {"question": question, "reponse": reponse}}), {"appris": True})
        # Même clé (minuscules, espaces et ponctuation finale ignorés) : le noyau répond seul.
        resultat = self.pont({"message": "c'est quoi un  serveur DNS"})
        self.assertEqual(resultat["reponse"], reponse)
        self.assertEqual(resultat["niveaux"], ["réflexe"])
        reflexes = json.loads((Path(self.dossier.name) / "noyau" / "reflexes.json").read_text(encoding="utf-8"))
        self.assertEqual(reflexes["c'est quoi un serveur dns"]["organe"], "claude")

    def test_message_vide_refuse(self):
        for paire in ({"question": "", "reponse": "r"}, {"question": "q", "reponse": "  "}, {}):
            resultat = self.pont({"apprendre": paire})
            self.assertFalse(resultat["appris"])
            self.assertIn("vide", resultat["erreur"])
        self.assertFalse((Path(self.dossier.name) / "noyau" / "reflexes.json").exists())

    def test_message_trop_long_refuse(self):
        for paire in ({"question": "q" * 121, "reponse": "r"}, {"question": "q", "reponse": "r" * 1501}):
            resultat = self.pont({"apprendre": paire})
            self.assertFalse(resultat["appris"])
            self.assertIn("trop longue", resultat["erreur"])
        self.assertFalse((Path(self.dossier.name) / "noyau" / "reflexes.json").exists())

    def test_question_en_plusieurs_etapes_refusee(self):
        resultat = self.pont({"apprendre": {"question": "Ouvre le fichier, puis lis-le", "reponse": "r"}})
        self.assertFalse(resultat["appris"])


if __name__ == "__main__":
    unittest.main()
