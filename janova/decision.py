"""Les décisions rapides : la moelle épinière de Janova, inspirée de Jev (TypeSafe AI, 2026).

Un grand modèle d'IA répond en écrivant, mot après mot : c'est lent et coûteux. Jev a montré une autre voie :
au lieu d'écrire, on **choisit**. On donne un texte, une question et les réponses permises, comme un QCM ;
le modèle en choisit une et dit à quel point il est sûr de lui.

    « Cet email est-il urgent ? »   → un grand modèle : « Oui, car le client parle d'une date limite… »
                                    → une décision     : « oui, 91 % »

Janova recrée ce principe **en local, sans aucune bibliothèque** :
- trois primitives, comme Jev : choisir une option, donner une note sur une échelle, répondre oui ou non ;
- la réponse est toujours l'une des options permises : Janova ne peut rien inventer, au pire elle se trompe d'option ;
- chaque décision vient avec un **pourcentage de confiance**. Sous le seuil, Janova sait qu'elle ne sait pas
  et passe la main à un étage plus cher (le noyau, puis un professeur) au lieu de deviner.

Comment ça marche, en simple (méthode dite « bayésienne naïve », connue depuis les années 1960) :
Janova compte quels mots reviennent dans les exemples de chaque option. Face à un nouveau texte, elle regarde
quelle option a le plus souvent vu ces mots-là. Chaque correction ou leçon d'un professeur ajoute un exemple :
les décisions s'améliorent avec l'expérience, et ce qui demandait un professeur devient un réflexe.
"""

import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path

SEUIL_CONFIANCE = 0.60  # sous 60 % de confiance, la décision n'est pas assez sûre : on monte d'un étage

# Petits mots trop fréquents pour aider à décider (« le », « de »…) : on les ignore.
MOTS_VIDES = set(
    "le la les un une des du de d l au aux et ou en à a dans sur pour par avec sans ce cet cette ces "
    "mon ma mes ton ta tes son sa ses notre nos votre vos leur leurs je tu il elle on nous vous ils elles "
    "me te se qui que quoi dont est sont être avoir ai as ont fait plus moins très pas ne n y c s qu".split()
)


def mots(texte: str) -> list[str]:
    """Découpe un texte en mots utiles : minuscules, sans ponctuation ni petits mots vides."""
    return [m for m in re.findall(r"[a-zà-ÿœæ0-9]+", texte.lower()) if len(m) > 1 and m not in MOTS_VIDES]


@dataclass
class Decision:
    """Le résultat d'une décision : l'option choisie et la confiance, entre 0 et 1."""

    question: str
    choix: str
    confiance: float
    probabilites: dict[str, float] = field(default_factory=dict)

    @property
    def sure(self) -> bool:
        """Vrai si la confiance dépasse le seuil : Janova peut agir sans demander plus haut."""
        return self.confiance >= SEUIL_CONFIANCE

    def __str__(self) -> str:
        return f"{self.choix} ({self.confiance:.0%})"


class Decideur:
    """Prend des décisions rapides et apprend de chaque exemple. Tout est gardé dans un fichier JSON."""

    def __init__(self, chemin: Path | None = None) -> None:
        self.chemin = Path(chemin) if chemin else None
        # Pour chaque question, pour chaque option : le nombre d'exemples et le compte de chaque mot vu.
        # {"importance": {"haute": {"exemples": 3, "mots": {"urgent": 2, …}}, …}, …}
        self.connaissances: dict[str, dict[str, dict]] = {}
        if self.chemin and self.chemin.exists():
            try:
                self.connaissances = json.loads(self.chemin.read_text(encoding="utf-8"))
            except ValueError:
                self.chemin.replace(self.chemin.with_suffix(".abime"))  # fichier abîmé : on repart à vide

    # --- Apprendre ------------------------------------------------------------------------------------

    def enseigner(self, question: str, texte: str, option: str, poids: int = 1) -> None:
        """Ajoute un exemple : « ce texte-là, pour cette question, c'est cette option ».

        Les exemples viennent de toi (une correction) ou d'un professeur (une leçon) : c'est la distillation.
        """
        fiche = self.connaissances.setdefault(question, {}).setdefault(option, {"exemples": 0, "mots": {}})
        fiche["exemples"] += poids
        for mot in mots(texte):
            fiche["mots"][mot] = fiche["mots"].get(mot, 0) + poids

    def options(self, question: str) -> list[str]:
        """Les options déjà rencontrées pour une question."""
        return list(self.connaissances.get(question, {}))

    # --- Les trois primitives -------------------------------------------------------------------------

    def choisir(self, question: str, texte: str, options: list[str] | None = None) -> Decision | None:
        """Choisit une option parmi celles permises. None s'il n'y a aucune option possible."""
        options = list(dict.fromkeys(options or self.options(question)))  # sans doublons, ordre gardé
        if not options:
            return None
        fiches = self.connaissances.get(question, {})
        vides = {"exemples": 0, "mots": {}}
        total_exemples = sum(fiches.get(o, vides)["exemples"] for o in options)
        vocabulaire = {m for o in options for m in fiches.get(o, vides)["mots"]}
        taille_vocabulaire = len(vocabulaire) + 1
        # Un mot jamais vu dans aucun exemple n'apprend rien sur le choix : on l'ignore. Sinon il pénaliserait
        # les options qui ont beaucoup d'exemples et favoriserait, au hasard, celle qui en a le moins.
        mots_du_texte = [m for m in mots(texte) if m in vocabulaire]

        # Pour chaque option, un score : plus il est grand, plus l'option est probable.
        # On additionne des logarithmes au lieu de multiplier des probabilités minuscules (plus stable).
        # Le « + 1 » (lissage de Laplace) évite qu'un seul mot jamais vu rende une option impossible.
        scores = {}
        for option in options:
            fiche = fiches.get(option, vides)
            total_mots = sum(fiche["mots"].values())
            score = math.log((fiche["exemples"] + 1) / (total_exemples + len(options)))
            for mot in mots_du_texte:
                score += math.log((fiche["mots"].get(mot, 0) + 1) / (total_mots + taille_vocabulaire))
            scores[option] = score

        # On transforme les scores en probabilités qui font 100 % au total (la fonction « softmax »).
        plus_grand = max(scores.values())
        exponentielles = {o: math.exp(s - plus_grand) for o, s in scores.items()}
        somme = sum(exponentielles.values())
        probabilites = {o: e / somme for o, e in exponentielles.items()}
        choix = max(probabilites, key=probabilites.get)
        return Decision(question, choix, probabilites[choix], probabilites)

    def noter(self, question: str, texte: str, echelle: list[str]) -> Decision | None:
        """Donne une note sur une échelle rangée du plus bas au plus haut (ex. basse, moyenne, haute)."""
        return self.choisir(question, texte, echelle)

    def oui_non(self, question: str, texte: str) -> Decision | None:
        """Répond oui ou non, avec la confiance."""
        return self.choisir(question, texte, ["oui", "non"])

    # --- Garder sur le disque -------------------------------------------------------------------------

    def sauvegarder(self) -> None:
        """Écrit les connaissances dans le fichier (via un fichier temporaire, pour ne jamais l'abîmer)."""
        if self.chemin is None:
            return
        self.chemin.parent.mkdir(parents=True, exist_ok=True)
        temporaire = self.chemin.with_suffix(".tmp")
        temporaire.write_text(json.dumps(self.connaissances, ensure_ascii=False, indent=2), encoding="utf-8")
        temporaire.replace(self.chemin)
