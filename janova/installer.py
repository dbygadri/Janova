"""Installer Janova dans ton Linux : une entrée dans le menu des applications, et un démarrage automatique.

    python -m janova --installer      Janova démarre avec ta session et apparaît dans le menu
    python -m janova --desinstaller   retire les deux

Ce sont deux petits fichiers texte « .desktop », la façon standard de déclarer une application sous Linux.
"""

import sys
from pathlib import Path

RACINE_PROJET = Path(__file__).resolve().parents[1]


def _contenu(demarrage: bool) -> str:
    lignes = [
        "[Desktop Entry]",
        "Type=Application",
        "Name=Janova",
        "Comment=Ton IA locale : parle-lui, elle agit et apprend",
        f"Exec={sys.executable} -m janova --bureau",
        f"Path={RACINE_PROJET}",
        "Icon=utilities-terminal",
        "Terminal=false",
        "Categories=Utility;",
    ]
    if demarrage:
        lignes.append("X-GNOME-Autostart-enabled=true")
    return "\n".join(lignes) + "\n"


def _chemins(maison: Path) -> tuple[Path, Path]:
    return (maison / ".local/share/applications/janova.desktop", maison / ".config/autostart/janova.desktop")


def installer(maison: Path | None = None) -> str:
    menu, demarrage = _chemins(Path(maison) if maison else Path.home())
    for chemin, auto in ((menu, False), (demarrage, True)):
        chemin.parent.mkdir(parents=True, exist_ok=True)
        chemin.write_text(_contenu(auto), encoding="utf-8")
    return ("Janova est installée : elle démarrera avec ta session, et elle est dans le menu des applications.\n"
            "Pour la lancer tout de suite : python -m janova --bureau")


def desinstaller(maison: Path | None = None) -> str:
    retires = 0
    for chemin in _chemins(Path(maison) if maison else Path.home()):
        if chemin.exists():
            chemin.unlink()
            retires += 1
    return f"{retires} fichier(s) retiré(s). Janova ne démarrera plus toute seule (tes données sont gardées)."
