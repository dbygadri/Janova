"""L'attention : ce qui mérite de l'énergie, et ce qui n'en mérite pas.

Deux mécanismes du système nerveux :

- **L'habituation** : on finit par ne plus entendre le tic-tac d'une horloge. Le cerveau arrête de
  dépenser de l'énergie sur ce qui se répète sans rien apporter de nouveau. Pour Janova : si la même
  tâche revient plusieurs fois en peu de temps, elle répond de mémoire immédiate, sans même la redécouper.

- **L'urgence** : un cri nous met en alerte tout de suite (c'est l'adrénaline). Pour Janova : une tâche
  qui contient un mot d'urgence peut utiliser des ressources que le mode économie aurait refusées.
"""

import re
import time
from collections import deque

REPETITIONS_POUR_HABITUATION = 3  # à partir de la 3e fois…
FENETRE_SECONDES = 60  # …en moins d'une minute

MOTS_URGENTS = re.compile(r"\b(urgent|urgence|vite|immédiatement|immediatement|tout de suite|alerte|au secours)\b",
                          re.IGNORECASE)


def _cle(tache: str) -> str:
    return " ".join(tache.lower().split()).rstrip(" .!?")


class Attention:
    def __init__(self, horloge=time.monotonic) -> None:
        self.horloge = horloge  # la fonction qui donne l'heure (les tests en donnent une fausse)
        self.vues: dict[str, deque] = {}  # pour chaque tâche : les moments où elle a été reçue
        self.memoire_immediate: dict[str, object] = {}  # pour chaque tâche : le dernier rapport

    def est_urgente(self, tache: str) -> bool:
        return MOTS_URGENTS.search(tache) is not None

    def remarquer(self, tache: str) -> bool:
        """Note qu'on a reçu cette tâche. Renvoie True si Janova y est habituée (répétée trop souvent)."""
        maintenant = self.horloge()
        moments = self.vues.setdefault(_cle(tache), deque())
        moments.append(maintenant)
        # On oublie les passages trop anciens : seuls ceux de la dernière minute comptent.
        while moments and maintenant - moments[0] > FENETRE_SECONDES:
            moments.popleft()
        # On fait aussi le ménage dans les autres tâches, pour que cette mémoire ne grossisse pas sans fin.
        if len(self.vues) > 200:
            for cle in [c for c, m in self.vues.items() if maintenant - m[-1] > FENETRE_SECONDES]:
                self.vues.pop(cle, None)
                self.memoire_immediate.pop(cle, None)
        return len(moments) >= REPETITIONS_POUR_HABITUATION and _cle(tache) in self.memoire_immediate

    def souvenir(self, tache: str):
        return self.memoire_immediate.get(_cle(tache))

    def retenir(self, tache: str, rapport) -> None:
        self.memoire_immediate[_cle(tache)] = rapport
