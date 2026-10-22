"""Les gestes de base des mains de Janova : ce qu'elle sait faire sur ton Linux.

Chaque geste (une « primitive ») est petit, connu à l'avance et contrôlé :
- il dit ce qu'il va faire avant de le faire ;
- il a un **niveau de risque** : faible, moyen ou élevé ;
- quand c'est possible, il sait **s'annuler** (/annuler remet tout comme avant).

Janova ne lance jamais de commande inventée. Même quand un professeur lui apprend une nouvelle tâche,
il ne peut que combiner ces gestes : c'est le système immunitaire des mains.
Et il n'existe aucun geste qui efface définitivement : au pire, un fichier va à la corbeille.
"""

import os
import random
import re
import shutil
import subprocess
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

FAIBLE, MOYEN, ELEVE = "faible", "moyen", "élevé"


# --- Parler au système ------------------------------------------------------------------------------


class Executeur:
    """Lance les programmes du système. Les tests le remplacent par un faux, pour ne rien toucher."""

    def lancer(self, commande: list[str]) -> tuple[int, str]:
        """Lance une commande et attend sa fin. Renvoie (code de retour, ce qu'elle a écrit)."""
        try:
            fini = subprocess.run(commande, capture_output=True, text=True, timeout=20)
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return 127, ""
        return fini.returncode, fini.stdout.strip()

    def detacher(self, commande: list[str]) -> bool:
        """Lance un programme qui continue de vivre seul (une appli qu'on ouvre)."""
        try:
            subprocess.Popen(commande, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        except OSError:
            return False
        return True

    def trouver(self, programme: str) -> str | None:
        return shutil.which(programme)


def bureau_actuel() -> str:
    """L'environnement de bureau : gnome, kde, cinnamon, mate, xfce, ou inconnu."""
    nom = (os.environ.get("XDG_CURRENT_DESKTOP", "") + " " + os.environ.get("DESKTOP_SESSION", "")).lower()
    for cle, bureau in (("kde", "kde"), ("plasma", "kde"), ("cinnamon", "cinnamon"), ("mate", "mate"),
                        ("xfce", "xfce"), ("gnome", "gnome"), ("ubuntu", "gnome"), ("unity", "gnome"),
                        ("pop", "gnome"), ("budgie", "gnome")):
        if cle in nom:
            return bureau
    return "inconnu"


@dataclass
class Contexte:
    """Où et comment les mains agissent. Les tests donnent un dossier personnel temporaire."""

    maison: Path = field(default_factory=Path.home)
    executeur: Executeur = field(default_factory=Executeur)
    bureau: str = field(default_factory=bureau_actuel)
    atelier: object = None  # l'atelier de code (codeur/atelier.py), branché par le noyau


def sans_accents(texte: str) -> str:
    decompose = unicodedata.normalize("NFKD", texte.lower())
    return "".join(c for c in decompose if not unicodedata.combining(c))


# --- Retrouver les dossiers de l'utilisateur --------------------------------------------------------

# Les mots que tu peux employer → le nom officiel du dossier sous Linux (norme « XDG »).
DOSSIERS_CONNUS = {
    "telechargement": "DOWNLOAD", "download": "DOWNLOAD",
    "document": "DOCUMENTS",
    "image": "PICTURES", "photo": "PICTURES", "picture": "PICTURES",
    "musique": "MUSIC", "music": "MUSIC",
    "video": "VIDEOS",
    "bureau": "DESKTOP", "desktop": "DESKTOP",
    "modele": "TEMPLATES",
}
NOMS_PAR_DEFAUT = {
    "DOWNLOAD": ["Téléchargements", "Downloads"], "DOCUMENTS": ["Documents"], "PICTURES": ["Images", "Pictures"],
    "MUSIC": ["Musique", "Music"], "VIDEOS": ["Vidéos", "Videos"], "DESKTOP": ["Bureau", "Desktop"],
    "TEMPLATES": ["Modèles", "Templates"],
}


def dossier_xdg(contexte: Contexte, cle: str) -> Path:
    """Le vrai chemin d'un dossier personnel (Téléchargements, Images…), lu dans ~/.config/user-dirs.dirs."""
    reglages = contexte.maison / ".config" / "user-dirs.dirs"
    if reglages.exists():
        for ligne in reglages.read_text(encoding="utf-8", errors="ignore").splitlines():
            trouve = re.match(rf'XDG_{cle}_DIR="(.+)"', ligne.strip())
            if trouve:
                return Path(trouve.group(1).replace("$HOME", str(contexte.maison)))
    for nom in NOMS_PAR_DEFAUT[cle]:
        if (contexte.maison / nom).exists():
            return contexte.maison / nom
    return contexte.maison / NOMS_PAR_DEFAUT[cle][0]


def resoudre_chemin(contexte: Contexte, texte: str) -> Path:
    """« téléchargements », « ~/notes », « Documents/factures » → un vrai chemin."""
    texte = texte.strip().strip("«»\"' ")
    if texte.startswith("~"):
        return contexte.maison / texte[1:].lstrip("/")
    if texte.startswith("/"):
        return Path(texte)
    premier, _, reste = texte.replace("\\", "/").partition("/")
    simple = re.sub(r"^(mes|mon|ma|le|la|les|dossier|du|des)\s+", "", sans_accents(premier)).rstrip("s")
    for mot, cle in DOSSIERS_CONNUS.items():
        if simple == mot:
            base = dossier_xdg(contexte, cle)
            return base / reste if reste else base
    if simple in ("maison", "home", "dossier personnel", "perso"):
        return contexte.maison / reste if reste else contexte.maison
    return contexte.maison / texte


# --- Le résultat d'un geste --------------------------------------------------------------------------


@dataclass
class Resultat:
    texte: str
    reussi: bool = True
    annulation: Callable[[], str] | None = None  # appeler cette fonction remet tout comme avant


def _deplacer_sans_ecraser(source: Path, dossier: Path) -> Path:
    """Déplace un fichier dans un dossier. Si le nom existe déjà, ajoute « (2) », « (3) »… : rien n'est écrasé."""
    dossier.mkdir(parents=True, exist_ok=True)
    cible = dossier / source.name
    numero = 2
    while cible.exists():
        cible = dossier / f"{source.stem} ({numero}){source.suffix}"
        numero += 1
    shutil.move(str(source), str(cible))
    return cible


def _annuler_deplacements(deplacements: list[tuple[Path, Path]], crees: list[Path]) -> Callable[[], str]:
    def annuler() -> str:
        remis = 0
        for origine, arrivee in reversed(deplacements):
            if arrivee.exists() and not origine.exists():
                origine.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(arrivee), str(origine))
                remis += 1
        for dossier in reversed(crees):  # on retire les dossiers créés, seulement s'ils sont restés vides
            if dossier.is_dir() and not any(dossier.iterdir()):
                dossier.rmdir()
        return f"{remis} élément(s) remis à leur place."
    return annuler


# --- Les gestes ---------------------------------------------------------------------------------------

FAMILLES = {
    "Images": "jpg jpeg png gif webp svg heic bmp tif tiff",
    "Documents": "pdf doc docx odt txt md rtf xls xlsx ods csv ppt pptx odp epub",
    "Vidéos": "mp4 mkv avi mov webm",
    "Musique": "mp3 wav flac ogg m4a opus",
    "Archives": "zip tar gz tgz rar 7z xz bz2 deb rpm iso",
    "Programmes": "appimage sh exe msi run",
}
FAMILLE_DE = {extension: famille for famille, liste in FAMILLES.items() for extension in liste.split()}
EN_COURS = {".part", ".crdownload", ".tmp", ".download"}  # téléchargements pas finis : on n'y touche pas


def ranger_dossier(contexte: Contexte, dossier: str = "téléchargements") -> Resultat:
    """Range les fichiers d'un dossier dans des sous-dossiers par type (Images, Documents, Vidéos…)."""
    racine = resoudre_chemin(contexte, dossier)
    if not racine.is_dir():
        return Resultat(f"Je ne trouve pas le dossier {racine}.", False)
    deplacements, crees, compte = [], [], {}
    for fichier in sorted(racine.iterdir()):
        if not fichier.is_file() or fichier.name.startswith(".") or fichier.suffix.lower() in EN_COURS:
            continue
        famille = FAMILLE_DE.get(fichier.suffix.lower().lstrip("."), "Autres")
        destination = racine / famille
        if not destination.exists():
            crees.append(destination)
        deplacements.append((fichier, _deplacer_sans_ecraser(fichier, destination)))
        compte[famille] = compte.get(famille, 0) + 1
    if not deplacements:
        return Resultat(f"Rien à ranger dans {racine.name}.")
    detail = ", ".join(f"{n} {famille}" for famille, n in sorted(compte.items(), key=lambda p: -p[1]))
    return Resultat(f"{len(deplacements)} fichier(s) rangé(s) dans {racine.name} : {detail}.", True,
                    _annuler_deplacements(deplacements, crees))


def deplacer(contexte: Contexte, source: str, destination: str) -> Resultat:
    """Déplace un fichier ou un dossier vers un autre dossier."""
    origine, arrivee = resoudre_chemin(contexte, source), resoudre_chemin(contexte, destination)
    if not origine.exists():
        return Resultat(f"Je ne trouve pas {origine}.", False)
    crees = [] if arrivee.exists() else [arrivee]
    nouvelle_place = _deplacer_sans_ecraser(origine, arrivee)
    return Resultat(f"{origine.name} déplacé dans {arrivee}.", True, _annuler_deplacements([(origine, nouvelle_place)], crees))


def creer_dossier(contexte: Contexte, chemin: str) -> Resultat:
    dossier = resoudre_chemin(contexte, chemin)
    if dossier.exists():
        return Resultat(f"Le dossier {dossier} existe déjà.")
    dossier.mkdir(parents=True)
    return Resultat(f"Dossier {dossier} créé.", True, _annuler_deplacements([], [dossier]))


def corbeille(contexte: Contexte, chemin: str) -> Resultat:
    """Met à la corbeille (jamais d'effacement définitif). On peut le récupérer depuis la corbeille."""
    cible = resoudre_chemin(contexte, chemin)
    if not cible.exists():
        return Resultat(f"Je ne trouve pas {cible}.", False)
    code, _ = contexte.executeur.lancer(["gio", "trash", str(cible)])
    if code != 0:
        return Resultat("Je n'ai pas pu mettre à la corbeille (programme « gio » introuvable).", False)
    return Resultat(f"{cible.name} mis à la corbeille. Tu peux le récupérer depuis la corbeille.")


def ouvrir(contexte: Contexte, cible: str) -> Resultat:
    """Ouvre un fichier, un dossier, un site web ou une application."""
    ex = contexte.executeur
    if re.match(r"https?://", cible):
        return Resultat(f"J'ouvre {cible}.", ex.detacher(["xdg-open", cible]))
    chemin = resoudre_chemin(contexte, cible)
    if chemin.exists():
        return Resultat(f"J'ouvre {chemin}.", ex.detacher(["xdg-open", str(chemin)]))
    # Une application : d'abord par son nom de programme, puis par son nom affiché (fichiers .desktop).
    programme = ex.trouver(cible.strip().lower().replace(" ", "-"))
    if programme:
        return Resultat(f"J'ouvre {cible}.", ex.detacher([programme]))
    lanceur = _trouver_lanceur(contexte, cible)
    if lanceur and ex.trouver("gtk-launch"):
        return Resultat(f"J'ouvre {cible}.", ex.detacher(["gtk-launch", lanceur.stem]))
    if lanceur:
        return Resultat(f"J'ouvre {cible}.", ex.detacher(["gio", "launch", str(lanceur)]))
    return Resultat(f"Je ne trouve pas « {cible} » (ni fichier, ni dossier, ni application).", False)


def _trouver_lanceur(contexte: Contexte, nom: str) -> Path | None:
    """Cherche l'application dont le nom affiché ressemble à « nom » (ex. « calculatrice »)."""
    voulu = sans_accents(nom.strip())
    for dossier in (contexte.maison / ".local/share/applications", Path("/usr/share/applications"),
                    Path("/var/lib/flatpak/exports/share/applications")):
        if not dossier.is_dir():
            continue
        for fichier in sorted(dossier.glob("*.desktop")):
            for ligne in fichier.read_text(encoding="utf-8", errors="ignore").splitlines():
                if re.match(r"Name(\[fr\])?=", ligne) and voulu in sans_accents(ligne.split("=", 1)[1]):
                    return fichier
    return None


def _gsettings(contexte: Contexte, schema: str, cle: str, valeur: str | None = None) -> str | None:
    """Lit (ou écrit) un réglage du bureau GNOME, Cinnamon ou MATE."""
    if valeur is None:
        code, sortie = contexte.executeur.lancer(["gsettings", "get", schema, cle])
        return sortie.strip("'") if code == 0 else None
    code, _ = contexte.executeur.lancer(["gsettings", "set", schema, cle, valeur])
    return valeur if code == 0 else None


def fond_ecran(contexte: Contexte, image: str = "") -> Resultat:
    """Change le fond d'écran. Sans image précisée, en choisit une au hasard dans tes Images."""
    if image:
        chemin = resoudre_chemin(contexte, image)
    else:
        images = [p for p in dossier_xdg(contexte, "PICTURES").rglob("*")
                  if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp") and len(p.parts) < 64]
        if not images:
            return Resultat("Je n'ai trouvé aucune image dans ton dossier Images.", False)
        chemin = random.choice(images)
    if not chemin.is_file():
        return Resultat(f"Je ne trouve pas l'image {chemin}.", False)
    uri = chemin.resolve().as_uri()
    reglages = {"gnome": ("org.gnome.desktop.background", ["picture-uri", "picture-uri-dark"], uri),
                "cinnamon": ("org.cinnamon.desktop.background", ["picture-uri"], uri),
                "mate": ("org.mate.background", ["picture-filename"], str(chemin))}
    if contexte.bureau in reglages:
        schema, cles, valeur = reglages[contexte.bureau]
        anciens = {cle: _gsettings(contexte, schema, cle) for cle in cles}
        if any(_gsettings(contexte, schema, cle, valeur) is None for cle in cles):
            return Resultat("Je n'ai pas pu changer le fond d'écran.", False)

        def annuler() -> str:
            for cle, ancien in anciens.items():
                if ancien:
                    _gsettings(contexte, schema, cle, ancien)
            return "Ancien fond d'écran remis."
        return Resultat(f"Fond d'écran changé : {chemin.name}.", True, annuler)
    if contexte.bureau == "kde":
        code, _ = contexte.executeur.lancer(["plasma-apply-wallpaperimage", str(chemin)])
        return Resultat(f"Fond d'écran changé : {chemin.name}." if code == 0 else "Je n'ai pas pu changer le fond.", code == 0)
    return Resultat(f"Je ne sais pas encore changer le fond d'écran sur ce bureau ({contexte.bureau}).", False)


def theme(contexte: Contexte, mode: str = "inverse") -> Resultat:
    """Passe le bureau en thème sombre, clair, ou l'inverse de l'actuel."""
    mode = sans_accents(mode)
    if contexte.bureau == "gnome":
        schema, cle = "org.gnome.desktop.interface", "color-scheme"
        ancien = _gsettings(contexte, schema, cle) or "default"
        sombre = mode.startswith("sombre") or (mode.startswith("inverse") and ancien != "prefer-dark")
        if _gsettings(contexte, schema, cle, "prefer-dark" if sombre else "default") is None:
            return Resultat("Je n'ai pas pu changer le thème.", False)

        def annuler() -> str:
            _gsettings(contexte, schema, cle, ancien)
            return "Ancien thème remis."
        return Resultat(f"Thème {'sombre' if sombre else 'clair'} activé.", True, annuler)
    if contexte.bureau == "kde":
        reglages = contexte.maison / ".config" / "kdeglobals"
        actuel = reglages.read_text(errors="ignore") if reglages.exists() else ""
        sombre = mode.startswith("sombre") or (mode.startswith("inverse") and "Dark" not in actuel)
        nom = "BreezeDark" if sombre else "BreezeLight"
        code, _ = contexte.executeur.lancer(["plasma-apply-colorscheme", nom])
        return Resultat(f"Thème {'sombre' if sombre else 'clair'} activé." if code == 0 else "Je n'ai pas pu.", code == 0)
    if contexte.bureau == "xfce":
        sombre = not mode.startswith("clair")
        code, _ = contexte.executeur.lancer(["xfconf-query", "-c", "xsettings", "-p", "/Net/ThemeName",
                                             "-s", "Adwaita-dark" if sombre else "Adwaita"])
        return Resultat(f"Thème {'sombre' if sombre else 'clair'} activé." if code == 0 else "Je n'ai pas pu.", code == 0)
    return Resultat(f"Je ne sais pas encore changer le thème sur ce bureau ({contexte.bureau}).", False)


def notifier(contexte: Contexte, texte: str) -> Resultat:
    code, _ = contexte.executeur.lancer(["notify-send", "Janova", texte])
    return Resultat(f"Notification : {texte}", code == 0)


def creer_application(contexte: Contexte, demande: str) -> Resultat:
    """Code, teste et installe une application (voir codeur/atelier.py)."""
    if contexte.atelier is None:
        return Resultat("Mon atelier de code n'est pas branché.", False)
    return contexte.atelier.creer(contexte.maison, demande)


def modifier_application(contexte: Contexte, nom: str, demande: str) -> Resultat:
    if contexte.atelier is None:
        return Resultat("Mon atelier de code n'est pas branché.", False)
    return contexte.atelier.modifier(contexte.maison, nom, demande)


# --- Le catalogue ------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Primitive:
    nom: str
    description: str
    parametres: tuple[str, ...]
    risque: str
    fonction: Callable[..., Resultat]


PRIMITIVES = {p.nom: p for p in [
    Primitive("ranger_dossier", "ranger un dossier par type de fichier", ("dossier",), MOYEN, ranger_dossier),
    Primitive("deplacer", "déplacer un fichier ou un dossier", ("source", "destination"), MOYEN, deplacer),
    Primitive("creer_dossier", "créer un dossier", ("chemin",), FAIBLE, creer_dossier),
    Primitive("corbeille", "mettre à la corbeille", ("chemin",), ELEVE, corbeille),
    Primitive("ouvrir", "ouvrir un fichier, un dossier, un site ou une application", ("cible",), FAIBLE, ouvrir),
    Primitive("fond_ecran", "changer le fond d'écran", ("image",), FAIBLE, fond_ecran),
    Primitive("theme", "changer le thème", ("mode",), FAIBLE, theme),
    Primitive("notifier", "afficher une notification", ("texte",), FAIBLE, notifier),
    Primitive("creer_application", "coder une application, la tester et l'installer", ("demande",), MOYEN,
              creer_application),
    Primitive("modifier_application", "modifier une application que j'ai codée", ("nom", "demande"), MOYEN,
              modifier_application),
]}
