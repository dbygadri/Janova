"""Découpage d'une tâche en étapes.

C'est la toute première fonction du noyau de Janova. Elle reçoit une tâche écrite en français
et la découpe en petites étapes, dans l'ordre.

Pour l'instant, il n'y a aucune intelligence artificielle : on coupe simplement le texte
là où il y a des mots de liaison (« puis », « ensuite »…) ou de la ponctuation.
Plus tard, le noyau pourra demander de l'aide à ses organes pour découper plus finement.

Exemple :
    >>> decouper_en_etapes("Ouvre le fichier, puis lis la première ligne. Enfin, affiche-la.")
    ['Ouvre le fichier', 'lis la première ligne', 'affiche-la']
"""

# « re » est le module des expressions régulières de Python : il sert à chercher des motifs
# dans un texte (par exemple « le mot puis, entouré d'espaces »). Il est fourni avec Python,
# il n'y a rien à installer.
import re

# Les mots qui annoncent une nouvelle étape. On pourra en ajouter facilement plus tard.
# Attention à l'ordre : les expressions longues (« et puis ») doivent venir avant les courtes (« puis »),
# sinon le « et » resterait collé à l'étape précédente.
MOTS_DE_LIAISON = [
    "et puis",
    "et ensuite",
    "et enfin",
    "puis",
    "ensuite",
    "après ça",
    "après cela",
    "enfin",
    "pour finir",
]

# Les signes de ponctuation qui terminent une étape :
# le point, le point-virgule, le point d'exclamation, le point d'interrogation, le retour à la ligne.
PONCTUATION_DE_FIN = r"[.;!?\n]"

# On fabrique une seule expression régulière qui reconnaît n'importe quel séparateur :
# - soit une ponctuation de fin,
# - soit un mot de liaison entier (\b = « début ou fin de mot »), éventuellement précédé d'une virgule.
# re.IGNORECASE permet de reconnaître « Puis » comme « puis ».
SEPARATEUR = re.compile(
    PONCTUATION_DE_FIN + r"|,?\s*\b(?:" + "|".join(MOTS_DE_LIAISON) + r")\b,?",
    re.IGNORECASE,
)


def decouper_en_etapes(tache: str) -> list[str]:
    """Découpe une tâche en une liste d'étapes, dans l'ordre où elles apparaissent.

    Paramètre :
        tache : la tâche à découper, écrite en texte libre.

    Renvoie :
        la liste des étapes. Elle est vide si la tâche est vide.
    """
    # 1. On coupe le texte à chaque séparateur trouvé.
    morceaux = SEPARATEUR.split(tache)

    # 2. On nettoie chaque morceau :
    #    - strip() enlève les espaces en trop au début et à la fin ;
    #    - strip(" ,") enlève aussi les virgules qui traînent ;
    #    - on garde seulement les morceaux qui contiennent encore du texte.
    etapes = []
    for morceau in morceaux:
        propre = morceau.strip().strip(" ,")
        if propre:
            etapes.append(propre)

    # 3. On renvoie la liste des étapes.
    return etapes

