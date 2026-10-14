"""L'organe de calcul : il résout les opérations écrites dans une étape.

Exemples d'étapes reconnues :
    « calcule 12 * (3 + 4) »      → 84
    « combien font 7 fois 6 ? »   → 42
    « 2,5 plus 1,5 »              → 4

Sécurité : on n'utilise surtout PAS eval(), qui exécuterait n'importe quel code Python
caché dans le texte. On analyse l'opération avec le module « ast », et on n'accepte que
des nombres, des parenthèses et les opérations + - * / // % **.
"""

import ast
import operator
import re

from janova.organes.base import Organe

# Les mots qu'on remplace par leur symbole. L'ordre compte : « divisé par » avant « par ».
MOTS_OPERATIONS = [
    ("divisé par", "/"),
    ("divise par", "/"),
    ("multiplié par", "*"),
    ("multiplie par", "*"),
    ("fois", "*"),
    ("plus", "+"),
    ("moins", "-"),
    ("puissance", "**"),
    ("×", "*"),
    ("÷", "/"),
    ("^", "**"),
]

# Une opération : au moins un nombre, un opérateur, puis un autre nombre, avec des parenthèses possibles.
OPERATION = re.compile(r"[\d(][\d\s.()+\-*/%]*[+\-*/%][\d\s.()+\-*/%]*[\d)]")

# Les opérations autorisées, et la fonction Python qui fait le calcul pour chacune.
OPERATEURS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _preparer(etape: str) -> str:
    """Transforme les mots en symboles et les virgules décimales en points : « 2,5 fois 2 » → « 2.5 * 2 »."""
    texte = etape.lower()
    for mot, symbole in MOTS_OPERATIONS:
        texte = texte.replace(mot, f" {symbole} ")
    # Une virgule entre deux chiffres est une virgule décimale : 2,5 → 2.5
    return re.sub(r"(\d),(\d)", r"\1.\2", texte)


def _extraire_operation(etape: str) -> str | None:
    """Trouve l'opération dans l'étape. Renvoie None s'il n'y en a pas."""
    trouve = OPERATION.search(_preparer(etape))
    # " ".join(...split()) remplace les espaces multiples par un seul : « 7  *  6 » → « 7 * 6 ».
    return " ".join(trouve.group().split()) if trouve else None


def _evaluer(noeud: ast.AST) -> float:
    """Calcule la valeur d'une opération déjà analysée, en refusant tout ce qui n'est pas du calcul."""
    if isinstance(noeud, ast.Expression):
        return _evaluer(noeud.body)
    if isinstance(noeud, ast.Constant) and isinstance(noeud.value, (int, float)):
        return noeud.value
    if isinstance(noeud, ast.BinOp) and type(noeud.op) in OPERATEURS:
        gauche, droite = _evaluer(noeud.left), _evaluer(noeud.right)
        # Garde-fou d'énergie : on refuse les puissances énormes (9 ** 9999999 bloquerait la machine).
        if isinstance(noeud.op, ast.Pow) and abs(droite) > 1000:
            raise ValueError("puissance trop grande")
        return OPERATEURS[type(noeud.op)](gauche, droite)
    if isinstance(noeud, ast.UnaryOp) and type(noeud.op) in OPERATEURS:
        return OPERATEURS[type(noeud.op)](_evaluer(noeud.operand))
    raise ValueError("ce n'est pas un calcul")


def _formater(nombre: float) -> str:
    """Affiche 4.0 comme « 4 », et arrondit les nombres à virgule à 10 chiffres significatifs."""
    if isinstance(nombre, float) and nombre.is_integer():
        nombre = int(nombre)
    return f"{nombre:.10g}" if isinstance(nombre, float) else str(nombre)


class OrganeCalcul(Organe):
    nom = "calcul"
    cout = 2
    deterministe = True

    @classmethod
    def reconnait(cls, etape: str) -> bool:
        return _extraire_operation(etape) is not None

    def traiter(self, etape: str) -> str | None:
        operation = _extraire_operation(etape)
        if operation is None:
            return None
        try:
            resultat = _evaluer(ast.parse(operation, mode="eval"))
        except (SyntaxError, ValueError, ZeroDivisionError, OverflowError):
            return None
        return f"{operation} = {_formater(resultat)}"
