"""La confiance graduelle : l'autonomie des mains grandit avec ton accord.

Au début, Janova te demande avant chaque geste. Chaque fois que tu dis oui à un même genre de geste,
elle gagne ta confiance pour ce geste-là. Au bout de 3 accords sans refus, elle le fait seule.
Un refus remet le compteur à zéro : elle redemandera.

Certains gestes ne deviennent jamais automatiques : ceux à risque élevé (mettre à la corbeille).
Pour eux, elle demande toujours.
"""

import json
from pathlib import Path

from janova.mains.primitives import ELEVE, PRIMITIVES

ACCORDS_POUR_AUTONOMIE = 3


class Confiance:
    def __init__(self, chemin: Path | None = None) -> None:
        self.chemin = Path(chemin) if chemin else None
        self.niveaux: dict[str, dict] = {}  # {"theme": {"accords": 2, "refus": 0}, …}
        if self.chemin and self.chemin.exists():
            try:
                self.niveaux = json.loads(self.chemin.read_text(encoding="utf-8"))
            except ValueError:
                self.chemin.replace(self.chemin.with_suffix(".abime"))

    def _fiche(self, geste: str) -> dict:
        return self.niveaux.setdefault(geste, {"accords": 0, "refus": 0})

    def accord(self, geste: str) -> None:
        self._fiche(geste)["accords"] += 1
        self.sauvegarder()

    def refus(self, geste: str) -> None:
        fiche = self._fiche(geste)
        fiche["refus"] += 1
        fiche["accords"] = 0  # la confiance se reconstruit à partir de zéro
        self.sauvegarder()

    def autonome(self, geste: str) -> bool:
        """Vrai si Janova peut faire ce geste sans te demander."""
        primitive = PRIMITIVES.get(geste)
        if primitive is None or primitive.risque == ELEVE:
            return False
        return self.niveaux.get(geste, {}).get("accords", 0) >= ACCORDS_POUR_AUTONOMIE

    def resume(self) -> str:
        lignes = []
        for nom, primitive in PRIMITIVES.items():
            accords = self.niveaux.get(nom, {}).get("accords", 0)
            if self.autonome(nom):
                etat = "je le fais seule"
            elif primitive.risque == ELEVE:
                etat = "je demande toujours (risque élevé)"
            else:
                etat = f"je demande encore ({accords}/{ACCORDS_POUR_AUTONOMIE} accords)"
            lignes.append(f"  - {primitive.description} : {etat}")
        return "Confiance de mes mains :\n" + "\n".join(lignes)

    def sauvegarder(self) -> None:
        if self.chemin is None:
            return
        self.chemin.parent.mkdir(parents=True, exist_ok=True)
        temporaire = self.chemin.with_suffix(".tmp")
        temporaire.write_text(json.dumps(self.niveaux, ensure_ascii=False, indent=2), encoding="utf-8")
        temporaire.replace(self.chemin)
