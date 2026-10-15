"""L'évolution : les organes appris s'améliorent pendant le sommeil, par variation et sélection.

Un organe appris décide s'il se réveille grâce à ses **mots-clés**. S'ils sont mal choisis :
- trop larges, il se réveille pour rien (« fausse alerte ») : le bac à sable démarre, consomme
  de l'énergie, puis l'organe répond « ce n'est pas pour moi » ;
- trop étroits, il rate des étapes qu'il saurait traiter.

Comme l'évolution des espèces, Janova essaie des **variations** de mots-clés au hasard, puis
**sélectionne** la meilleure, sur ce que l'organe a réellement vécu :
- les étapes qu'il a réussies (ses « positifs ») : il doit continuer à les reconnaître ;
- ses fausses alertes (ses « négatifs ») : il doit apprendre à les ignorer.

Règle d'or : une variante qui reconnaît moins d'étapes réussies est toujours rejetée.
L'organe ne peut que s'améliorer, jamais perdre une capacité.
"""

import random
import re
import unicodedata

GENERATIONS = 30  # nombre de tours d'évolution par nuit
DESCENDANTS = 8  # nombre de variantes essayées à chaque tour
MOTS_CLES_MAX = 5


def _sans_accents(texte: str) -> str:
    decompose = unicodedata.normalize("NFKD", texte.lower())
    return "".join(c for c in decompose if not unicodedata.combining(c))


def _mots(etape: str) -> list[str]:
    """Les mots d'au moins 4 lettres d'une étape : les plus petits (« de », « le »…) ne distinguent rien."""
    return [mot for mot in re.findall(r"[a-z]+", _sans_accents(etape)) if len(mot) >= 4]


def _reconnait(mots_cles: list[str], etape: str) -> bool:
    texte = _sans_accents(etape)
    return any(mot in texte for mot in mots_cles)


def note(mots_cles: list[str], positifs: list[str], negatifs: list[str]) -> tuple[int, float]:
    """La note d'un jeu de mots-clés : (étapes réussies reconnues, score).

    score = 2 points par étape réussie reconnue, - 3 points par fausse alerte,
            - 0,2 point par mot-clé (à efficacité égale, le plus simple est le meilleur).
    """
    reconnus = sum(_reconnait(mots_cles, e) for e in positifs)
    fausses_alertes = sum(_reconnait(mots_cles, e) for e in negatifs)
    return reconnus, 2 * reconnus - 3 * fausses_alertes - 0.2 * len(mots_cles)


def muter(mots_cles: list[str], positifs: list[str], hasard: random.Random) -> list[str]:
    """Crée une variante : retirer, ajouter ou remplacer un mot-clé."""
    variante = list(mots_cles)
    candidats = sorted({mot for etape in positifs for mot in _mots(etape)} - set(variante))
    choix = hasard.choice(["retirer", "ajouter", "remplacer"])
    if choix == "retirer" and len(variante) > 1:
        variante.remove(hasard.choice(variante))
    elif choix == "ajouter" and candidats and len(variante) < MOTS_CLES_MAX:
        variante.append(hasard.choice(candidats))
    elif choix == "remplacer" and candidats:
        variante[hasard.randrange(len(variante))] = hasard.choice(candidats)
    return variante


def evoluer(mots_cles: list[str], positifs: list[str], negatifs: list[str], graine: int = 0) -> list[str] | None:
    """Fait évoluer les mots-clés. Renvoie les nouveaux s'ils sont meilleurs, sinon None."""
    if not negatifs:
        return None  # aucune fausse alerte : rien à corriger, on n'use pas d'énergie pour rien
    hasard = random.Random(graine)  # graine fixe : la même nuit donne toujours le même résultat
    meilleurs = [_sans_accents(m) for m in mots_cles]
    reconnus_depart, meilleur_score = note(meilleurs, positifs, negatifs)

    for _ in range(GENERATIONS):
        for _ in range(DESCENDANTS):
            variante = muter(meilleurs, positifs, hasard)
            reconnus, score = note(variante, positifs, negatifs)
            # Sélection : meilleur score, ET aucune étape réussie perdue.
            if reconnus >= reconnus_depart and score > meilleur_score:
                meilleurs, meilleur_score = variante, score

    depart = [_sans_accents(m) for m in mots_cles]
    return meilleurs if sorted(meilleurs) != sorted(depart) else None
