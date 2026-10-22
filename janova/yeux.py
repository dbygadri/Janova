"""Les yeux : Janova remarque tes habitudes et te propose de les faire à ta place.

**Les yeux sont fermés par défaut.** Ils ne s'ouvrent que si tu le demandes (/yeux oui), et tout reste
sur ta machine, dans « donnees/yeux/ ». Tu peux les refermer quand tu veux (/yeux non) et tout effacer
en supprimant ce dossier.

Ce que les yeux regardent :
- ce que tu demandes à Janova de faire sur l'ordinateur (« mets le thème sombre ») ;
- les fichiers que tu ouvres, lus dans la liste des « fichiers récents » que Linux tient déjà
  (~/.local/share/recently-used.xbel). Rien d'autre : ni ton écran, ni ton clavier, ni Internet.

Une habitude, c'est la même chose faite au même moment de la journée (matin, après-midi, soir, nuit),
au moins 3 jours différents sur les 3 dernières semaines. Janova propose alors d'en faire une routine.
Si tu refuses, elle ne la proposera plus.
"""

import json
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import unquote, urlparse

from janova.mains.primitives import sans_accents

JOURS_MINIMUM = 3  # une chose faite au même moment 3 jours différents devient une habitude
FENETRE_JOURS = 21  # on ne regarde que les 3 dernières semaines
MAX_EVENEMENTS = 3000
MOMENTS = [("nuit", 0, 5), ("matin", 5, 12), ("après-midi", 12, 18), ("soir", 18, 23), ("nuit", 23, 24)]
HEURE_PAR_MOMENT = {"matin": "08:00", "après-midi": "14:00", "soir": "19:00", "nuit": "23:00"}


def moment_de(quand: datetime) -> str:
    return next(nom for nom, debut, fin in MOMENTS if debut <= quand.hour < fin)


@dataclass
class Habitude:
    quoi: str  # ce que tu fais, sous forme de demande à Janova (« ouvre ~/Documents/compta.ods »)
    moment: str
    jours: int  # nombre de jours différents où c'est arrivé

    @property
    def cle(self) -> str:
        return f"{sans_accents(self.quoi)}|{self.moment}"

    @property
    def heure(self) -> str:
        return HEURE_PAR_MOMENT[self.moment]


class Yeux:
    def __init__(self, dossier: Path, maison: Path | None = None) -> None:
        self.dossier = Path(dossier)
        self.maison = Path(maison) if maison else Path.home()
        self.chemin = self.dossier / "yeux.json"
        self.etat = {"actifs": False, "evenements": [], "refusees": [], "proposees": [], "vu_jusqu_a": ""}
        if self.chemin.exists():
            try:
                self.etat.update(json.loads(self.chemin.read_text(encoding="utf-8")))
            except ValueError:
                self.chemin.replace(self.chemin.with_suffix(".abime"))

    @property
    def actifs(self) -> bool:
        return self.etat["actifs"]

    def ouvrir(self, oui: bool) -> str:
        self.etat["actifs"] = oui
        if oui and not self.etat["vu_jusqu_a"]:
            # On commence à regarder à partir de maintenant : pas de fouille dans le passé.
            self.etat["vu_jusqu_a"] = datetime.now().isoformat(timespec="seconds")
        self.sauvegarder()
        if oui:
            return ("Mes yeux sont ouverts. Je remarque ce que tu me demandes et les fichiers que tu ouvres, "
                    "tout reste sur ta machine. /yeux non pour les fermer.")
        return "Mes yeux sont fermés. Je ne remarque plus rien."

    def noter(self, quoi: str, quand: datetime | None = None) -> None:
        if not self.actifs or not quoi.strip():
            return
        quand = quand or datetime.now()
        self.etat["evenements"].append({"quoi": quoi.strip(), "quand": quand.isoformat(timespec="seconds")})
        self.etat["evenements"] = self.etat["evenements"][-MAX_EVENEMENTS:]
        self.sauvegarder()

    def regarder(self) -> int:
        """Lit les fichiers ouverts récemment (liste tenue par Linux). Renvoie le nombre de nouveautés."""
        if not self.actifs:
            return 0
        liste = self.maison / ".local" / "share" / "recently-used.xbel"
        if not liste.exists():
            return 0
        try:
            racine = ET.parse(liste).getroot()
        except (ET.ParseError, OSError):
            return 0
        depuis = self.etat["vu_jusqu_a"]
        nouveautes = []
        for marque in racine.iter("bookmark"):
            quand_texte = (marque.get("visited") or marque.get("modified") or "")[:19]
            adresse = marque.get("href", "")
            if not quand_texte or not adresse.startswith("file://") or quand_texte <= depuis[:19]:
                continue
            try:
                quand = datetime.fromisoformat(quand_texte)
            except ValueError:
                continue
            chemin = Path(unquote(urlparse(adresse).path))
            try:
                lisible = "~/" + str(chemin.relative_to(self.maison))
            except ValueError:
                lisible = str(chemin)
            nouveautes.append((quand, f"ouvre {lisible}"))
        for quand, quoi in sorted(nouveautes):
            self.noter(quoi, quand)
        if nouveautes:
            self.etat["vu_jusqu_a"] = max(q for q, _ in nouveautes).isoformat(timespec="seconds")
            self.sauvegarder()
        return len(nouveautes)

    def habitudes(self, maintenant: datetime | None = None) -> list[Habitude]:
        """Les habitudes repérées, pas encore proposées ni refusées, les plus régulières d'abord."""
        maintenant = maintenant or datetime.now()
        limite = maintenant - timedelta(days=FENETRE_JOURS)
        jours_par_habitude: dict[tuple[str, str], set] = defaultdict(set)
        exemples: dict[tuple[str, str], str] = {}
        for evenement in self.etat["evenements"]:
            quand = datetime.fromisoformat(evenement["quand"])
            if quand < limite:
                continue
            cle = (sans_accents(evenement["quoi"]), moment_de(quand))
            jours_par_habitude[cle].add(quand.date())
            exemples[cle] = evenement["quoi"]
        deja = set(self.etat["refusees"]) | set(self.etat["proposees"])
        trouvees = [Habitude(exemples[cle], cle[1], len(jours)) for cle, jours in jours_par_habitude.items()
                    if len(jours) >= JOURS_MINIMUM]
        return sorted((h for h in trouvees if h.cle not in deja), key=lambda h: -h.jours)

    def proposee(self, habitude: Habitude) -> None:
        self.etat["proposees"].append(habitude.cle)
        self.sauvegarder()

    def refusee(self, habitude: Habitude) -> None:
        self.etat["refusees"].append(habitude.cle)
        self.sauvegarder()

    def sauvegarder(self) -> None:
        self.dossier.mkdir(parents=True, exist_ok=True)
        temporaire = self.chemin.with_suffix(".tmp")
        temporaire.write_text(json.dumps(self.etat, ensure_ascii=False, indent=2), encoding="utf-8")
        temporaire.replace(self.chemin)
