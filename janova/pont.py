"""Le pont entre le bureau de Janova et le noyau.

Le bureau envoie une question ; le noyau répond seulement s'il sait déjà la traiter tout seul,
par un réflexe ou un organe. Sinon il répond « je ne sais pas », et le bureau demande à Claude.

    echo '{"message": "calcule 2 + 3"}' | python3 -m janova.pont

Le bureau peut aussi lui faire retenir une réponse de Claude, sur demande de l'utilisateur :
la même question sera ensuite servie par un réflexe, sans réveiller Claude.

    echo '{"apprendre": {"question": "c'est quoi un DNS ?", "reponse": "..."}}' | python3 -m janova.pont

Depuis le chat, les mains (les actions sur l'ordinateur) restent coupées : Janova ne doit jamais agir
par surprise pendant une discussion. L'aide extérieure aussi : c'est le bureau qui appelle Claude.
"""

import json
import os
import sys
from pathlib import Path

from janova.noyau import Janova, decouper_en_etapes
from janova.noyau.coordination import DOSSIER_DONNEES
from janova.reflexes import MemoireReflexes

QUESTION_MAX = 120  # au-delà, la question est trop particulière pour être retenue telle quelle
REPONSE_MAX = 1500


def repondre(janova: Janova, message: str) -> dict:
    rapport = janova.traiter(message)
    etapes = rapport.etapes
    if not etapes or any(r.reponse is None for r in etapes):
        return {"reponse": None}
    return {"reponse": "\n".join(r.reponse for r in etapes), "niveaux": [r.niveau for r in etapes]}


def apprendre(dossier: Path, question: str, reponse: str) -> dict:
    """Retient une réponse de Claude comme réflexe : la même question n'ira plus jusqu'à Claude."""
    question, reponse = question.strip(), reponse.strip()
    if not question or not reponse:
        return {"appris": False, "erreur": "La question et la réponse ne doivent pas être vides."}
    if len(question) > QUESTION_MAX or len(reponse) > REPONSE_MAX:
        return {"appris": False, "erreur": "La question ou la réponse est trop longue pour devenir un réflexe."}
    # Le noyau découpe chaque message en étapes et cherche un réflexe par étape :
    # une question en plusieurs étapes ne retomberait jamais sur ce réflexe.
    if len(decouper_en_etapes(question)) != 1:
        return {"appris": False, "erreur": "La question a plusieurs étapes : Janova ne pourrait pas la reconnaître."}
    reflexes = MemoireReflexes(dossier / "reflexes.json")
    reflexes.apprendre(question, reponse, "claude", 0.0)
    reflexes.sauvegarder()
    return {"appris": True}


def main() -> None:
    memoire = os.environ.get("JANOVA_MEMOIRE")
    dossier = Path(memoire) / "noyau" if memoire else DOSSIER_DONNEES
    demande = json.loads(sys.stdin.read() or "{}")
    if isinstance(demande.get("apprendre"), dict):
        paire = demande["apprendre"]
        try:
            resultat = apprendre(dossier, str(paire.get("question", "")), str(paire.get("reponse", "")))
        except Exception as erreur:
            resultat = {"appris": False, "erreur": str(erreur)}
        print(json.dumps(resultat, ensure_ascii=False))
        return
    janova = Janova(dossier, aide=None)
    janova._par_mains = lambda *args, **kwargs: None  # pas d'action sur l'ordinateur depuis le chat
    try:
        resultat = repondre(janova, str(demande.get("message", "")))
    except Exception as erreur:  # le noyau ne doit jamais bloquer le chat : on passe la main à Claude
        resultat = {"reponse": None, "erreur": str(erreur)}
    print(json.dumps(resultat, ensure_ascii=False))


if __name__ == "__main__":
    main()
