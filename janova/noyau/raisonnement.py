"""Le raisonnement du noyau (niveau 3) : combiner les organes entre eux.

Un organe seul ne connaît que l'étape qu'on lui donne. Mais une tâche forme un tout :
dans « calcule 2 + 3, puis multiplie le résultat par 4 », la deuxième étape dépend de la première.
Aucun organe ne sait ce que veut dire « le résultat » : c'est le noyau qui fait le lien.

Ce raisonnement reste volontairement simple et sans IA, donc presque gratuit en énergie :
il remplace les mots qui désignent le résultat précédent par sa valeur, puis l'étape réécrite
est redonnée aux organes.
"""

import re

# Les mots qui désignent le résultat de l'étape précédente.
# (?:le |la )? veut dire « éventuellement précédé de le ou la ».
REFERENCES = re.compile(
    r"\b(?:le |la )?(?:r[ée]sultat(?: pr[ée]c[ée]dent)?|r[ée]ponse(?: pr[ée]c[ée]dente)?)\b|\bça\b|\bcela\b",
    re.IGNORECASE,
)


def valeur_de(reponse: str) -> str:
    """Extrait la valeur utile d'une réponse : « 2 + 3 = 5 » → « 5 », « BONJOUR » → « BONJOUR »."""
    return reponse.rsplit("=", 1)[-1].strip()


def resoudre_references(etape: str, reponse_precedente: str | None) -> str | None:
    """Remplace « le résultat », « ça »… par la valeur de l'étape précédente.

    Renvoie l'étape réécrite, ou None s'il n'y a rien à remplacer (pas de référence, ou pas
    d'étape précédente). La valeur est mise entre guillemets « » pour que l'organe texte la retrouve.
    """
    if reponse_precedente is None or not REFERENCES.search(etape):
        return None
    return REFERENCES.sub(f"« {valeur_de(reponse_precedente)} »", etape)
