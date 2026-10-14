"""Le bac à sable : exécuter sans danger un organe écrit par une IA.

Un organe créé par auto-extension, c'est du code que personne n'a relu. Il pourrait, par erreur
ou par malveillance, effacer des fichiers, envoyer des données sur Internet ou bloquer la machine.
On met donc deux barrières :

1. **Lire le code avant de l'accepter** (fonction verifier_code) : on n'autorise que des modules
   sans danger (math, re, datetime…), et on refuse les fichiers, le réseau, eval/exec, et les accès
   qui commencent par « _ » ou « __ » (ce sont les « portes dérobées » de Python).
2. **L'exécuter dans un programme séparé et surveillé** (fonction executer) : il tourne dans un
   dossier temporaire vide, sans accès aux variables de l'ordinateur, avec une limite de temps,
   et une limite de mémoire sous Linux, Android et macOS.

Ce n'est pas une prison parfaite, mais c'est un garde-fou sérieux pour du code écrit par une IA.
"""

import ast
import json
import os
import subprocess
import sys
import tempfile

# Les seuls modules qu'un organe appris a le droit d'utiliser.
MODULES_AUTORISES = {
    "math", "re", "datetime", "calendar", "json", "statistics", "fractions", "decimal", "random",
    "string", "itertools", "functools", "collections", "unicodedata", "textwrap", "operator",
}

# Les noms interdits : ils donnent accès aux fichiers, à l'exécution de code ou aux entrailles de Python.
NOMS_INTERDITS = {
    "open", "exec", "eval", "compile", "__import__", "globals", "locals", "vars", "input", "breakpoint",
    "getattr", "setattr", "delattr", "help", "exit", "quit", "memoryview", "type", "object", "super",
}

MEMOIRE_MAX_OCTETS = 256 * 1024 * 1024  # 256 Mo : largement assez pour un petit organe

# Le petit programme qui tourne dans le processus séparé. Il reçoit le code de l'organe et les étapes
# à traiter, exécute reconnait() puis traiter() sur chacune, et renvoie les résultats en JSON.
_PROGRAMME = r"""
import io, json, sys
travail = json.loads(sys.stdin.read())
sortie, sys.stdout = sys.stdout, io.StringIO()   # les print() de l'organe ne doivent pas tout mélanger
espace = {"__name__": "organe_appris"}
exec(compile(travail["code"], "organe_appris", "exec"), espace)
resultats = []
for etape in travail["etapes"]:
    try:
        if not espace["reconnait"](etape):
            resultats.append([False, "étape non reconnue"])
        else:
            resultats.append([True, str(espace["traiter"](etape))])
    except Exception as erreur:
        resultats.append([False, f"{type(erreur).__name__} : {erreur}"])
sortie.write(json.dumps(resultats))
"""


def verifier_code(code: str) -> list[str]:
    """Lit le code sans l'exécuter. Renvoie la liste des problèmes (vide si le code est accepté)."""
    try:
        arbre = ast.parse(code)  # ast transforme le texte du code en « arbre » qu'on peut inspecter
    except SyntaxError as erreur:
        return [f"code invalide : {erreur}"]

    problemes = []
    for noeud in ast.walk(arbre):  # on visite chaque morceau du code
        if isinstance(noeud, ast.Import):
            modules = [alias.name.split(".")[0] for alias in noeud.names]
        elif isinstance(noeud, ast.ImportFrom):
            modules = [(noeud.module or "").split(".")[0]]
        else:
            modules = []
        problemes += [f"module interdit : {m}" for m in modules if m not in MODULES_AUTORISES]

        # Un nom qui commence par « __ » (comme __builtins__) ouvre les entrailles de Python.
        # Un seul « _ » (comme dans « for _ in ... ») est sans danger.
        if isinstance(noeud, ast.Name) and (noeud.id in NOMS_INTERDITS or noeud.id.startswith("__")):
            problemes.append(f"nom interdit : {noeud.id}")
        if isinstance(noeud, ast.Attribute) and noeud.attr.startswith("_"):
            problemes.append(f"accès interdit : .{noeud.attr}")
        if isinstance(noeud, (ast.Global, ast.Nonlocal)):
            problemes.append("global/nonlocal interdit")

    fonctions = {n.name for n in arbre.body if isinstance(n, ast.FunctionDef)}
    for obligatoire in ("reconnait", "traiter"):
        if obligatoire not in fonctions:
            problemes.append(f"il manque la fonction {obligatoire}(etape)")
    return problemes


def _limiter_memoire() -> None:
    """Exécuté dans le processus séparé, juste avant le lancement (Linux, Android, macOS seulement)."""
    import resource

    resource.setrlimit(resource.RLIMIT_AS, (MEMOIRE_MAX_OCTETS, MEMOIRE_MAX_OCTETS))


def executer(code: str, etapes: list[str], delai_secondes: float = 5.0) -> list[tuple[bool, str]]:
    """Exécute l'organe sur chaque étape, dans un processus séparé.

    Renvoie, pour chaque étape, (True, réponse) si tout s'est bien passé, sinon (False, explication).
    """
    problemes = verifier_code(code)
    if problemes:
        return [(False, "; ".join(problemes)) for _ in etapes]

    # Aucune variable d'environnement n'est transmise, sauf celle dont Windows a besoin pour démarrer Python.
    environnement = {cle: os.environ[cle] for cle in ("SYSTEMROOT",) if cle in os.environ}
    with tempfile.TemporaryDirectory(prefix="janova-bac-a-sable-") as dossier_vide:
        try:
            processus = subprocess.run(
                # -I : Python isolé (ignore les réglages de l'utilisateur) ; -X utf8 : accents corrects partout
                [sys.executable, "-I", "-X", "utf8", "-c", _PROGRAMME],
                input=json.dumps({"code": code, "etapes": etapes}),
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=delai_secondes,
                cwd=dossier_vide,
                env=environnement,
                preexec_fn=_limiter_memoire if os.name == "posix" else None,
            )
        except subprocess.TimeoutExpired:
            return [(False, f"trop long (plus de {delai_secondes:g} s)") for _ in etapes]

    if processus.returncode != 0:
        erreur = (processus.stderr.strip().splitlines() or ["échec inconnu"])[-1]
        return [(False, erreur) for _ in etapes]
    try:
        return [(bool(ok), str(texte)) for ok, texte in json.loads(processus.stdout)]
    except (ValueError, TypeError):
        return [(False, "réponse illisible") for _ in etapes]
