"""La croissance : Janova mesure son autonomie et passe par des stades de vie.

Le but de Janova est d'apprendre de ses professeurs (les modèles d'IA extérieurs) pour s'en passer peu à peu.
Pour savoir si elle y arrive, elle tient un journal de chaque étape : qui l'a résolue ?

- **seule** : un réflexe, un organe, le raisonnement du noyau, ou toi qui as donné la réponse ;
- **avec un professeur** : l'aide extérieure a dû intervenir ;
- **échec** : personne n'a su faire.

Le **taux d'autonomie** = étapes résolues seule ÷ toutes les étapes. Il doit monter avec le temps.

Les stades de vie, comme un enfant qui grandit :
- **bébé** : moins de la moitié des étapes résolues seule (ou trop peu d'expérience pour juger) ;
- **enfant** : au moins la moitié ;
- **adulte** : au moins 90 %.
Ces seuils sont provisoires : on les ajustera avec les premières vraies mesures.
"""

import json
from datetime import datetime
from pathlib import Path

EXPERIENCE_MINIMUM = 20  # en dessous de 20 étapes, Janova reste « bébé » : trop tôt pour juger
SEUIL_ENFANT = 0.50
SEUIL_ADULTE = 0.90


def qui_a_resolu(niveau: str) -> str:
    """Classe le niveau d'une étape (« réflexe », « organe calcul », « aide extérieure → … »…)."""
    if niveau == "aucun":
        return "echec"
    if niveau.startswith("aide extérieure") or niveau == "professeur":
        return "professeur"
    return "seule"


class Croissance:
    def __init__(self, chemin: Path) -> None:
        self.chemin = Path(chemin)
        self.compteurs = {"seule": 0, "professeur": 0, "echec": 0}
        self.depuis = datetime.now().isoformat(timespec="seconds")
        if self.chemin.exists():
            try:
                donnees = json.loads(self.chemin.read_text(encoding="utf-8"))
                self.compteurs.update(donnees.get("compteurs", {}))
                self.depuis = donnees.get("depuis", self.depuis)
            except ValueError:
                self.chemin.replace(self.chemin.with_suffix(".abime"))

    def noter(self, niveau: str) -> None:
        """Ajoute une étape au journal."""
        self.compteurs[qui_a_resolu(niveau)] += 1

    @property
    def total(self) -> int:
        return sum(self.compteurs.values())

    @property
    def taux_autonomie(self) -> float:
        return self.compteurs["seule"] / self.total if self.total else 0.0

    @property
    def stade(self) -> str:
        if self.total < EXPERIENCE_MINIMUM or self.taux_autonomie < SEUIL_ENFANT:
            return "bébé"
        return "adulte" if self.taux_autonomie >= SEUIL_ADULTE else "enfant"

    def resume(self, reflexes: int, organes_appris: int, idees: int) -> str:
        c = self.compteurs
        lignes = [
            f"Stade : {self.stade}   (autonomie {self.taux_autonomie:.0%} sur {self.total} étape(s),"
            f" depuis le {self.depuis[:10]})",
            f"  résolues seule : {c['seule']}   avec un professeur : {c['professeur']}   échecs : {c['echec']}",
            f"  réflexes : {reflexes}   organes appris : {organes_appris}   idées rangées : {idees}",
        ]
        if self.total < EXPERIENCE_MINIMUM:
            lignes.append(f"  Encore {EXPERIENCE_MINIMUM - self.total} étape(s) avant de pouvoir juger le stade.")
        elif self.stade == "bébé":
            lignes.append(f"  Prochain stade (enfant) : {SEUIL_ENFANT:.0%} d'autonomie.")
        elif self.stade == "enfant":
            lignes.append(f"  Prochain stade (adulte) : {SEUIL_ADULTE:.0%} d'autonomie.")
        return "\n".join(lignes)

    def sauvegarder(self) -> None:
        self.chemin.parent.mkdir(parents=True, exist_ok=True)
        temporaire = self.chemin.with_suffix(".tmp")
        donnees = {"compteurs": self.compteurs, "depuis": self.depuis}
        temporaire.write_text(json.dumps(donnees, ensure_ascii=False, indent=2), encoding="utf-8")
        temporaire.replace(self.chemin)
