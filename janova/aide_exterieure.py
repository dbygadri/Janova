"""L'aide extérieure (niveau 4) : un modèle d'IA local, appelé en tout dernier recours.

Janova reste une IA **locale** : l'aide extérieure est un modèle qui tourne sur ta propre machine,
grâce au logiciel gratuit Ollama (https://ollama.com). Rien ne part sur Internet.

C'est de loin la partie la plus gourmande : un modèle d'IA consomme beaucoup d'électricité,
de mémoire, et souvent la carte graphique. Janova ne l'appelle donc que si ni ses réflexes,
ni ses organes, ni son raisonnement n'ont suffi. Et elle en profite pour apprendre (voir l'auto-extension),
afin de ne plus en avoir besoin la fois suivante.

Réglages (facultatifs), par variables d'environnement :
    JANOVA_MODELE      le modèle à utiliser (par défaut qwen2.5:1.5b, petit et économe)
    JANOVA_OLLAMA_URL  l'adresse d'Ollama (par défaut http://127.0.0.1:11434)
"""

import json
import os
import urllib.error
import urllib.request

MODELE_PAR_DEFAUT = "qwen2.5:1.5b"  # environ 1 Go : un des plus petits modèles capables d'écrire du code
URL_PAR_DEFAUT = "http://127.0.0.1:11434"


class AideExterieure:
    nom = "aide extérieure"
    # On ne peut pas savoir à coup sûr si Ollama utilise la carte graphique ; il le fait dès qu'il en trouve
    # une compatible. Par prudence, on la compte comme utilisée.
    besoin_gpu = True

    def __init__(self, modele: str | None = None, url: str | None = None, delai_secondes: float = 120.0) -> None:
        self.modele = modele or os.environ.get("JANOVA_MODELE", MODELE_PAR_DEFAUT)
        self.url = (url or os.environ.get("JANOVA_OLLAMA_URL", URL_PAR_DEFAUT)).rstrip("/")
        self.delai_secondes = delai_secondes
        # Si Ollama ne répond pas une fois, on ne réessaie plus pendant cette session :
        # attendre une réponse qui ne viendra pas, c'est aussi gaspiller de l'énergie.
        self.indisponible = ""

    def demander(self, question: str, en_json: bool = False) -> str | None:
        """Pose une question au modèle. Renvoie sa réponse, ou None s'il est injoignable."""
        if self.indisponible:
            return None
        donnees = {"model": self.modele, "prompt": question, "stream": False}
        if en_json:
            donnees["format"] = "json"  # Ollama oblige alors le modèle à répondre en JSON valide
        requete = urllib.request.Request(
            f"{self.url}/api/generate",
            data=json.dumps(donnees).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(requete, timeout=self.delai_secondes) as reponse:
                texte = json.loads(reponse.read().decode("utf-8")).get("response", "").strip()
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as erreur:
            self.indisponible = f"Ollama injoignable ({erreur})"
            return None
        return texte or None
