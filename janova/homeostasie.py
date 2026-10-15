"""L'homéostasie : Janova surveille ses ressources vitales et s'adapte.

Le corps humain régule en permanence sa température, son énergie, sa fatigue. Quand les ressources
manquent, il passe en économie : il ralentit, frissonne, réduit ce qui n'est pas vital.

Janova fait pareil avec ses « signes vitaux » :
    🔋 la batterie (pourcentage, et si l'appareil est branché)
    🧠 la mémoire vive encore libre sur la machine
    🌡️ la température du processeur

Selon ces signes, elle choisit un mode :
    normal   : tout est permis
    économie : plus d'aide extérieure (l'IA est trop gourmande), sauf urgence
    survie   : seulement les réflexes et les organes de base (pas de bac à sable, pas d'IA)

Chaque capteur est lu s'il existe. Sur un PC sans batterie, par exemple, la batterie est simplement ignorée.
"""

import ctypes
import os
import time
from dataclasses import dataclass
from pathlib import Path

NORMAL, ECONOMIE, SURVIE = "normal", "économie", "survie"

# Les seuils de chaque mode. Une valeur absente (capteur inexistant) ne déclenche jamais rien.
SEUILS = {
    SURVIE: {"batterie": 10, "memoire_mo": 200, "temperature": 90},
    ECONOMIE: {"batterie": 30, "memoire_mo": 500, "temperature": 80},
}

DUREE_CACHE_SECONDES = 30  # lire les capteurs coûte aussi de l'énergie : on garde la mesure 30 secondes


@dataclass
class SignesVitaux:
    batterie: float | None = None  # en %, None si pas de batterie
    sur_secteur: bool | None = None  # True si l'appareil est branché
    memoire_libre_mo: float | None = None  # mémoire vive libre sur la machine, en mégaoctets
    temperature: float | None = None  # en °C

    def texte(self) -> str:
        morceaux = []
        if self.batterie is not None:
            branche = " (branché)" if self.sur_secteur else ""
            morceaux.append(f"🔋 batterie {self.batterie:.0f} %{branche}")
        if self.memoire_libre_mo is not None:
            morceaux.append(f"🧠 {self.memoire_libre_mo:.0f} Mo de mémoire libre")
        if self.temperature is not None:
            morceaux.append(f"🌡️ processeur à {self.temperature:.0f} °C")
        return ", ".join(morceaux) or "aucun capteur disponible"


# --- Lecture des capteurs, selon le système ---------------------------------------------------------


def _lire_nombre(chemin: Path) -> float | None:
    try:
        return float(chemin.read_text().strip())
    except (OSError, ValueError):
        return None


def _capteurs_linux() -> SignesVitaux:
    """Linux, Android (Termux) et Raspberry Pi : tout se lit dans des fichiers spéciaux du système."""
    signes = SignesVitaux()
    for batterie in sorted(Path("/sys/class/power_supply").glob("BAT*")):
        signes.batterie = _lire_nombre(batterie / "capacity")
        try:
            signes.sur_secteur = (batterie / "status").read_text().strip() in ("Charging", "Full")
        except OSError:
            pass
        break
    try:
        for ligne in Path("/proc/meminfo").read_text().splitlines():
            if ligne.startswith("MemAvailable:"):
                signes.memoire_libre_mo = int(ligne.split()[1]) / 1024  # la valeur est en Ko
    except OSError:
        pass
    temperatures = [_lire_nombre(zone / "temp") for zone in Path("/sys/class/thermal").glob("thermal_zone*")]
    temperatures = [t / 1000 for t in temperatures if t is not None]  # la valeur est en millièmes de degré
    if temperatures:
        signes.temperature = max(temperatures)
    return signes


def _capteurs_windows() -> SignesVitaux:
    """Windows : on interroge le système grâce à ctypes, qui permet d'appeler les fonctions de Windows."""
    signes = SignesVitaux()

    class EtatAlimentation(ctypes.Structure):
        _fields_ = [("ACLineStatus", ctypes.c_byte), ("BatteryFlag", ctypes.c_byte),
                    ("BatteryLifePercent", ctypes.c_byte), ("SystemStatusFlag", ctypes.c_byte),
                    ("BatteryLifeTime", ctypes.c_ulong), ("BatteryFullLifeTime", ctypes.c_ulong)]

    class EtatMemoire(ctypes.Structure):
        _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

    alimentation = EtatAlimentation()
    if ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(alimentation)):
        pourcentage = alimentation.BatteryLifePercent & 0xFF
        if pourcentage != 255 and not alimentation.BatteryFlag & 128:  # 255 ou 128 = pas de batterie
            signes.batterie = float(pourcentage)
            signes.sur_secteur = alimentation.ACLineStatus == 1
    memoire = EtatMemoire()
    memoire.dwLength = ctypes.sizeof(EtatMemoire)
    if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memoire)):
        signes.memoire_libre_mo = memoire.ullAvailPhys / (1024 * 1024)
    return signes  # la température n'est pas lisible simplement sous Windows


def lire_capteurs() -> SignesVitaux:
    """Lit les signes vitaux de la machine. Ne plante jamais : en cas de souci, renvoie ce qu'il a pu lire."""
    try:
        if os.name == "nt":
            return _capteurs_windows()
        return _capteurs_linux()
    except Exception:
        return SignesVitaux()


# --- Le choix du mode ---------------------------------------------------------------------------------


def choisir_mode(signes: SignesVitaux) -> tuple[str, str]:
    """Renvoie (mode, raison). Branchée sur secteur, la batterie ne compte plus."""
    for mode in (SURVIE, ECONOMIE):
        seuils = SEUILS[mode]
        if signes.batterie is not None and not signes.sur_secteur and signes.batterie < seuils["batterie"]:
            return mode, f"batterie à {signes.batterie:.0f} %"
        if signes.memoire_libre_mo is not None and signes.memoire_libre_mo < seuils["memoire_mo"]:
            return mode, f"seulement {signes.memoire_libre_mo:.0f} Mo de mémoire libre"
        if signes.temperature is not None and signes.temperature > seuils["temperature"]:
            return mode, f"processeur à {signes.temperature:.0f} °C"
    return NORMAL, "ressources suffisantes"


class Homeostasie:
    def __init__(self, lecteur=lire_capteurs) -> None:
        # « lecteur » est la fonction qui lit les capteurs. Les tests en donnent une fausse.
        self.lecteur = lecteur
        self._signes: SignesVitaux | None = None
        self._lu_a = 0.0

    def signes(self) -> SignesVitaux:
        if self._signes is None or time.monotonic() - self._lu_a > DUREE_CACHE_SECONDES:
            self._signes = self.lecteur()
            self._lu_a = time.monotonic()
        return self._signes

    def mode(self) -> tuple[str, str]:
        return choisir_mode(self.signes())

    def etat(self) -> str:
        mode, raison = self.mode()
        return f"Mode {mode} ({raison}) — {self.signes().texte()}"
