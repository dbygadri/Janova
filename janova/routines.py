"""Les routines : ce que Janova fait toute seule, à heure fixe.

Tu peux les demander en français : « tous les matins, change mon thème », « chaque lundi à 9h, range mes
téléchargements », « tous les soirs à 22h30 mets le thème sombre ». Les yeux de Janova peuvent aussi en
proposer quand ils remarquent une habitude.

Une routine est vérifiée chaque minute par la fenêtre de Janova (voir conversation.py : vivre()).
"""

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from janova.mains.primitives import sans_accents

HEURES_PAR_MOMENT = {"matin": "08:00", "midi": "12:00", "apres-midi": "15:00", "soir": "20:00", "nuit": "23:00"}
JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
TOUS_LES_JOURS = list(range(7))

QUAND = re.compile(
    r"\b(?:tous les|toutes les|chaque|le|les)\s+"
    r"(matins?|midis?|apres-midis?|soirs?|soirees?|nuits?|jours?|week-ends?|"
    + "|".join(f"{j}s?" for j in JOURS) + r")\b"
    r"|\ben semaine\b"
)
HEURE = re.compile(r"\b(?:a|vers)\s+(\d{1,2})\s*(?:h|:|heures?)\s*(\d{2})?\b")


@dataclass
class Routine:
    numero: int
    heure: str  # « 08:00 »
    jours: list[int]  # 0 = lundi … 6 = dimanche
    tache: str
    derniere: str = ""  # la date (AAAA-MM-JJ) de la dernière exécution

    def decrire(self) -> str:
        if sorted(self.jours) == TOUS_LES_JOURS:
            quand = "tous les jours"
        elif sorted(self.jours) == [0, 1, 2, 3, 4]:
            quand = "en semaine"
        elif sorted(self.jours) == [5, 6]:
            quand = "le week-end"
        else:
            quand = "chaque " + ", ".join(JOURS[j] for j in sorted(self.jours))
        return f"{quand} à {self.heure} : {self.tache}"


def extraire_routine(texte: str) -> tuple[str, list[int], str] | None:
    """« tous les matins, change mon thème » → (« 08:00 », tous les jours, « change mon thème »).

    None si la phrase ne parle pas d'une répétition.
    """
    s = sans_accents(texte)  # même longueur que le texte : les positions correspondent
    quand = QUAND.search(s)
    if not quand:
        return None
    mot = (quand.group(1) or "en semaine").rstrip("s")
    heure_trouvee = HEURE.search(s)
    if heure_trouvee:
        heure = f"{int(heure_trouvee.group(1)):02d}:{heure_trouvee.group(2) or '00'}"
    else:
        moment = "soir" if mot.startswith("soiree") else mot
        heure = HEURES_PAR_MOMENT.get(moment, "09:00")
    if mot in JOURS:
        jours = [JOURS.index(mot)]
    elif mot.startswith("week-end"):
        jours = [5, 6]
    elif mot == "en semaine":
        jours = [0, 1, 2, 3, 4]
    else:
        jours = TOUS_LES_JOURS
    # La tâche = la phrase sans les mots qui disent « quand ».
    a_retirer = sorted([quand.span()] + ([heure_trouvee.span()] if heure_trouvee else []), reverse=True)
    tache = texte
    for debut, fin in a_retirer:
        tache = tache[:debut] + " " + tache[fin:]
    tache = " ".join(tache.split()).strip(" ,.:;")
    tache = re.sub(r"^(et|puis|alors)\s+", "", tache, flags=re.IGNORECASE)
    return (heure, jours, tache) if tache else None


class Routines:
    def __init__(self, chemin: Path) -> None:
        self.chemin = Path(chemin)
        self.routines: list[Routine] = []
        if self.chemin.exists():
            try:
                self.routines = [Routine(**r) for r in json.loads(self.chemin.read_text(encoding="utf-8"))]
            except (ValueError, TypeError):
                self.chemin.replace(self.chemin.with_suffix(".abime"))

    def ajouter(self, heure: str, jours: list[int], tache: str, maintenant: datetime | None = None) -> Routine:
        maintenant = maintenant or datetime.now()
        numero = max((r.numero for r in self.routines), default=0) + 1
        routine = Routine(numero, heure, sorted(jours), tache)
        # Créée après l'heure du jour : elle commence demain, au lieu de partir tout de suite.
        if maintenant.strftime("%H:%M") >= heure:
            routine.derniere = maintenant.date().isoformat()
        self.routines.append(routine)
        self.sauvegarder()
        return routine

    def dues(self, maintenant: datetime | None = None) -> list[Routine]:
        """Les routines à lancer maintenant. Chacune n'est lancée qu'une fois par jour."""
        maintenant = maintenant or datetime.now()
        aujourd_hui = maintenant.date().isoformat()
        dues = [r for r in self.routines if maintenant.weekday() in r.jours
                and maintenant.strftime("%H:%M") >= r.heure and r.derniere != aujourd_hui]
        for routine in dues:
            routine.derniere = aujourd_hui
        if dues:
            self.sauvegarder()
        return dues

    def existe(self, tache: str) -> bool:
        return any(sans_accents(r.tache) == sans_accents(tache) for r in self.routines)

    def supprimer(self, numero: int) -> str:
        avant = len(self.routines)
        self.routines = [r for r in self.routines if r.numero != numero]
        self.sauvegarder()
        return f"Routine n°{numero} supprimée." if len(self.routines) < avant else f"Pas de routine n°{numero}."

    def lister(self) -> str:
        if not self.routines:
            return "Aucune routine. Exemple : tous les matins, change mon thème"
        return "Routines :\n" + "\n".join(f"  n°{r.numero} {r.decrire()}" for r in self.routines)

    def sauvegarder(self) -> None:
        self.chemin.parent.mkdir(parents=True, exist_ok=True)
        temporaire = self.chemin.with_suffix(".tmp")
        temporaire.write_text(json.dumps([r.__dict__ for r in self.routines], ensure_ascii=False, indent=2),
                              encoding="utf-8")
        temporaire.replace(self.chemin)
