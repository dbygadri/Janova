"""Vérifier une application avant de l'installer : le contrôle qualité et le système immunitaire du codeur.

Deux étapes, comme pour les organes appris (extension/bac_a_sable.py), mais adaptées à de vraies applications :

1. **Lecture de sécurité** (verifier_application) : sans exécuter le code, on refuse le réseau, le lancement
   d'autres programmes, les modules système (os, sys, shutil…), eval/exec, les « portes dérobées » de Python
   (noms en __), et les gestes qui effacent ou cassent des fichiers. Les fichiers simples (lire, écrire une note)
   restent permis : une application en a souvent besoin.
2. **Essai réel** (essayer) : l'application est chargée dans un programme séparé, dans un dossier temporaire
   qui lui sert de faux dossier personnel, avec une limite de temps et de mémoire. On y lance sa fonction
   tester(), qui vérifie sa logique sans ouvrir de fenêtre.

Limite honnête : aucune lecture ne garantit à 100 % qu'un programme est sans danger. C'est pourquoi Janova
te demande ton accord avant d'installer une application, et pourquoi elle ne peut jamais toucher au système.
"""

import ast
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from janova.extension.bac_a_sable import MODULES_AUTORISES, _limiter_memoire

MODULES_APPLICATION = MODULES_AUTORISES | {"tkinter", "time", "ast", "pathlib", "csv", "dataclasses", "enum",
                                           "typing", "copy", "heapq", "bisect", "zoneinfo", "difflib"}
NOMS_INTERDITS = {"exec", "eval", "compile", "__import__", "globals", "locals", "vars", "breakpoint",
                  "getattr", "setattr", "delattr", "memoryview"}
GESTES_INTERDITS = {"unlink", "rmdir", "rmtree", "chmod", "chown", "rename", "symlink_to", "hardlink_to",
                    "system", "popen", "kill", "remove", "removedirs", "truncate"}
DELAI_ESSAI_SECONDES = 15

_ESSAI = r"""
import importlib.util, sys, traceback
try:
    spec = importlib.util.spec_from_file_location("application_janova", sys.argv[1])
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.tester()
    print("OK")
except AssertionError as erreur:
    print("Un test échoue : " + (str(erreur) or "assert sans message") + "\n" + traceback.format_exc()[-600:])
except Exception as erreur:
    print(f"Erreur {type(erreur).__name__} : {erreur}\n" + traceback.format_exc()[-600:])
"""


def verifier_application(code: str) -> list[str]:
    """Lit le code sans l'exécuter. Renvoie la liste des problèmes (vide si le code est accepté)."""
    try:
        arbre = ast.parse(code)
    except SyntaxError as erreur:
        return [f"code invalide, ligne {erreur.lineno} : {erreur.msg}"]

    problemes = []
    for noeud in arbre.body:  # tkinter seulement dans main(), pour que tester() marche sans écran
        if isinstance(noeud, (ast.Import, ast.ImportFrom)):
            noms = [a.name for a in noeud.names] if isinstance(noeud, ast.Import) else [noeud.module or ""]
            if any(n.split(".")[0] == "tkinter" for n in noms):
                problemes.append("importe tkinter dans main(), pas en haut du fichier")

    for noeud in ast.walk(arbre):
        if isinstance(noeud, ast.Import):
            modules = [alias.name.split(".")[0] for alias in noeud.names]
        elif isinstance(noeud, ast.ImportFrom):
            modules = [(noeud.module or "").split(".")[0]]
        else:
            modules = []
        problemes += [f"module interdit : {m}" for m in modules if m not in MODULES_APPLICATION]
        if isinstance(noeud, ast.Name) and (noeud.id in NOMS_INTERDITS
                                            or (noeud.id.startswith("__") and noeud.id != "__name__")):
            problemes.append(f"nom interdit : {noeud.id}")
        if isinstance(noeud, ast.Attribute) and (noeud.attr.startswith("__") or noeud.attr in GESTES_INTERDITS):
            problemes.append(f"geste interdit : .{noeud.attr}")

    fonctions = {n.name for n in arbre.body if isinstance(n, ast.FunctionDef)}
    for obligatoire in ("main", "tester"):
        if obligatoire not in fonctions:
            problemes.append(f"il manque la fonction {obligatoire}()")
    if "if __name__" not in code:
        problemes.append('il manque à la fin : if __name__ == "__main__": main()')
    return list(dict.fromkeys(problemes))  # sans doublons, dans l'ordre


def essayer(code: str) -> str | None:
    """Lit puis essaie l'application. Renvoie None si tout va bien, sinon l'explication du problème."""
    problemes = verifier_application(code)
    if problemes:
        return "Lecture de sécurité : " + " ; ".join(problemes)
    with tempfile.TemporaryDirectory(prefix="janova-essai-") as dossier:
        fichier = Path(dossier) / "application.py"
        fichier.write_text(code, encoding="utf-8")
        environnement = {"HOME": dossier, "PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"}
        try:
            essai = subprocess.run(
                [sys.executable, "-I", "-X", "utf8", "-c", _ESSAI, str(fichier)],
                capture_output=True, text=True, encoding="utf-8", timeout=DELAI_ESSAI_SECONDES,
                cwd=dossier, env=environnement, preexec_fn=_limiter_memoire if os.name == "posix" else None,
            )
        except subprocess.TimeoutExpired:
            return f"L'essai a duré plus de {DELAI_ESSAI_SECONDES} secondes (boucle sans fin ? fenêtre ouverte dans tester() ?)"
    sortie = essai.stdout.strip()
    if sortie == "OK":
        return None
    return sortie or (essai.stderr.strip()[-600:] or "l'essai n'a rien répondu")
