"""Le pont entre le bureau de Janova et le noyau.

Le bureau envoie une question ; le noyau répond seulement s'il sait déjà la traiter tout seul,
par un réflexe ou un organe. Sinon il répond « je ne sais pas », et le bureau demande à Claude.

    echo '{"message": "calcule 2 + 3"}' | python3 -m janova.pont

Depuis le chat, les mains (les actions sur l'ordinateur) restent coupées : Janova ne doit jamais agir
par surprise pendant une discussion. L'aide extérieure aussi : c'est le bureau qui appelle Claude.
"""

import json
import os
import sys
from pathlib import Path

from janova.noyau import Janova


def repondre(janova: Janova, message: str) -> dict:
    rapport = janova.traiter(message)
    etapes = rapport.etapes
    if not etapes or any(r.reponse is None for r in etapes):
        return {"reponse": None}
    return {"reponse": "\n".join(r.reponse for r in etapes), "niveaux": [r.niveau for r in etapes]}


def main() -> None:
    memoire = os.environ.get("JANOVA_MEMOIRE")
    dossier = Path(memoire) / "noyau" if memoire else None
    janova = Janova(dossier, aide=None) if dossier else Janova(aide=None)
    janova._par_mains = lambda *args, **kwargs: None  # pas d'action sur l'ordinateur depuis le chat
    demande = json.loads(sys.stdin.read() or "{}")
    try:
        resultat = repondre(janova, str(demande.get("message", "")))
    except Exception as erreur:  # le noyau ne doit jamais bloquer le chat : on passe la main à Claude
        resultat = {"reponse": None, "erreur": str(erreur)}
    print(json.dumps(resultat, ensure_ascii=False))


if __name__ == "__main__":
    main()
