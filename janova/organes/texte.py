"""L'organe du texte : il transforme un morceau de texte.

Il sait :
    mettre en majuscules  « mets en majuscules : bonjour »        → BONJOUR
    mettre en minuscules  « écris en minuscules : SALUT »          → salut
    compter les mots      « compte les mots : le chat dort »       → 3 mots
    écrire à l'envers     « écris à l'envers : janova »            → avonaj

Le texte à transformer est ce qui suit les deux-points « : », ou ce qui est entre guillemets.
"""

import re
import unicodedata

from janova.organes.base import Organe

# Le texte visé : entre guillemets (« », " ") ou après deux-points.
ENTRE_GUILLEMETS = re.compile(r"[«\"“]\s*(.+?)\s*[»\"”]")
APRES_DEUX_POINTS = re.compile(r":\s*(.+)$")


def _sans_accents(texte: str) -> str:
    """« à l'envers » → « a l'envers », pour reconnaître les mots avec ou sans accents."""
    decompose = unicodedata.normalize("NFKD", texte.lower())
    return "".join(c for c in decompose if not unicodedata.combining(c))


def _texte_vise(etape: str) -> str | None:
    """Trouve le texte sur lequel travailler. Renvoie None s'il n'y en a pas."""
    for motif in (ENTRE_GUILLEMETS, APRES_DEUX_POINTS):
        trouve = motif.search(etape)
        if trouve and trouve.group(1).strip():
            return trouve.group(1).strip()
    return None


def _action(etape: str) -> str | None:
    """Trouve ce qu'il faut faire, à partir des mots de l'étape."""
    mots = _sans_accents(etape)
    if "majuscule" in mots:
        return "majuscules"
    if "minuscule" in mots:
        return "minuscules"
    if "mots" in mots and ("compte" in mots or "combien" in mots):
        return "compter"
    if "envers" in mots or "inverse" in mots:
        return "envers"
    return None


class OrganeTexte(Organe):
    nom = "texte"
    cout = 1
    deterministe = True

    @classmethod
    def reconnait(cls, etape: str) -> bool:
        return _action(etape) is not None and _texte_vise(etape) is not None

    def traiter(self, etape: str) -> str | None:
        action, texte = _action(etape), _texte_vise(etape)
        if action is None or texte is None:
            return None
        if action == "majuscules":
            return texte.upper()
        if action == "minuscules":
            return texte.lower()
        if action == "compter":
            nombre = len(texte.split())
            return f"{nombre} mot" + ("s" if nombre > 1 else "")
        return texte[::-1]  # [::-1] parcourt le texte de la fin vers le début
