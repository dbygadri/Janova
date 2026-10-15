"""La mémoire des réflexes (règle 3 : apprendre pour économiser ; règle 4 : se reposer pour se réorganiser).

Un réflexe, c'est une étape que Janova a déjà réussie, avec sa réponse. Quand la même étape
revient, Janova répond tout de suite, sans réveiller aucun organe : c'est presque gratuit.

Les réflexes sont enregistrés dans un fichier JSON (un format texte simple, lisible par un humain),
pour être conservés d'une utilisation à l'autre.

Comme les souvenirs humains, un réflexe se renforce quand il sert et s'efface quand il ne sert plus
(la « courbe de l'oubli » d'Ebbinghaus) :
- sa **force** diminue avec le temps : elle perd la moitié de sa valeur à chaque « demi-vie » ;
- la demi-vie vaut 7 jours au départ, et s'allonge de 7 jours à chaque réutilisation : un réflexe
  souvent utilisé tient des mois, un réflexe jamais réutilisé disparaît en trois semaines environ ;
- pendant le sommeil, les réflexes dont la force tombe sous 10 % sont oubliés.
"""

import json
from datetime import datetime
from pathlib import Path

DEMI_VIE_JOURS = 7  # demi-vie d'un réflexe jamais réutilisé
SEUIL_OUBLI = 0.10  # sous 10 % de force, le réflexe est oublié pendant le sommeil


def cle(etape: str) -> str:
    """Transforme une étape en « clé » de mémoire : minuscules, espaces simples, sans ponctuation finale.

    Ainsi « Calcule 2 + 2 ! » et « calcule  2 + 2 » sont reconnues comme la même étape.
    """
    return " ".join(etape.lower().split()).rstrip(" .!?")


class MemoireReflexes:
    def __init__(self, chemin: Path) -> None:
        self.chemin = Path(chemin)
        self.reflexes: dict[str, dict] = {}
        # Si le fichier existe déjà, on recharge les réflexes appris lors des utilisations précédentes.
        if self.chemin.exists():
            try:
                self.reflexes = json.loads(self.chemin.read_text(encoding="utf-8"))
            except ValueError:
                # Fichier abîmé (illisible) : on le met de côté au lieu de planter, et on repart à vide.
                self.chemin.replace(self.chemin.with_suffix(".abime"))

    def chercher(self, etape: str) -> dict | None:
        """Renvoie le réflexe correspondant à l'étape, ou None si Janova ne l'a jamais apprise."""
        reflexe = self.reflexes.get(cle(etape))
        if reflexe is not None:
            reflexe["utilisations"] += 1
            reflexe["derniere_utilisation"] = datetime.now().isoformat(timespec="seconds")
        return reflexe

    def apprendre(self, etape: str, reponse: str, organe: str, temps: float) -> None:
        """Mémorise une étape réussie comme nouveau réflexe."""
        maintenant = datetime.now().isoformat(timespec="seconds")
        self.reflexes[cle(etape)] = {
            "reponse": reponse,
            "organe": organe,  # l'organe qui a trouvé la réponse la première fois
            "temps_initial": temps,  # temps de calcul de la 1re fois (µs) : sert à calculer ce qui est économisé
            "utilisations": 0,  # combien de fois le réflexe a resservi
            "cree_le": maintenant,
            "derniere_utilisation": maintenant,
        }

    @staticmethod
    def force(reflexe: dict, maintenant: datetime | None = None) -> float:
        """La force du réflexe, entre 0 et 1 : 1 juste après usage, puis elle diminue avec le temps."""
        maintenant = maintenant or datetime.now()
        jours = (maintenant - datetime.fromisoformat(reflexe["derniere_utilisation"])).total_seconds() / 86400
        demi_vie = DEMI_VIE_JOURS * (1 + reflexe["utilisations"])  # chaque réutilisation renforce le souvenir
        return 0.5 ** (max(jours, 0) / demi_vie)  # ** veut dire « puissance »

    def consolider(self, maintenant: datetime | None = None) -> int:
        """Le tri du sommeil : oublie les réflexes dont la force est tombée sous le seuil.

        Renvoie le nombre de réflexes oubliés.
        """
        a_oublier = [
            cle_reflexe
            for cle_reflexe, reflexe in self.reflexes.items()
            if self.force(reflexe, maintenant) < SEUIL_OUBLI
        ]
        for cle_reflexe in a_oublier:
            del self.reflexes[cle_reflexe]
        return len(a_oublier)

    def sauvegarder(self) -> None:
        """Écrit les réflexes dans le fichier.

        On écrit d'abord dans un fichier temporaire, puis on le renomme : si l'ordinateur s'éteint
        au mauvais moment, l'ancien fichier reste intact au lieu d'être à moitié écrit.
        """
        self.chemin.parent.mkdir(parents=True, exist_ok=True)
        temporaire = self.chemin.with_suffix(".tmp")
        temporaire.write_text(json.dumps(self.reflexes, ensure_ascii=False, indent=2), encoding="utf-8")
        temporaire.replace(self.chemin)

    def taille_ko(self) -> float:
        """La place occupée sur le disque par les réflexes, en kilo-octets (0 si rien n'est encore enregistré)."""
        return self.chemin.stat().st_size / 1024 if self.chemin.exists() else 0.0

    def __len__(self) -> int:
        return len(self.reflexes)
