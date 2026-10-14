"""Le compteur d'énergie de Janova (règle 5 : mesurer pour progresser).

Pour Janova, « l'énergie », ce sont **toutes les ressources de la machine** :

- l'**électricité** : un programme ne peut pas lire directement les watts qu'il consomme, alors on
  mesure le **temps de calcul**, qui lui est proportionnel. Unité : la microseconde (µs), un millionième de seconde ;
- la **mémoire vive (RAM)** : on mesure le **pic** de mémoire utilisé par chaque action. Unité : le kilo-octet (Ko) ;
- la **carte graphique** : on compte les organes qui en ont besoin. L'objectif de Janova est de s'en passer ;
- le **stockage** : la place occupée sur le disque par ce que Janova a appris (calculée par le noyau).

Limite à connaître : le compteur ne voit que Janova elle-même. L'aide extérieure (Ollama) et le bac à sable
des organes appris tournent dans des programmes séparés : leur électricité et leur mémoire ne sont pas comptées.
Leur vrai coût est donc plus élevé que ce qui s'affiche, surtout pour l'aide extérieure.
"""

# Ces trois modules sont fournis avec Python, il n'y a rien à installer :
# - time : un chronomètre très précis ;
# - tracemalloc : il surveille la mémoire utilisée par Python ;
# - contextlib : il permet d'écrire « with compteur.mesurer(...) : » (voir plus bas).
import time
import tracemalloc
from contextlib import contextmanager


class CompteurEnergie:
    def __init__(self) -> None:
        self.temps_par_niveau: dict[str, float] = {}  # électricité : temps de calcul cumulé par niveau, en µs
        self.memoire_par_niveau: dict[str, float] = {}  # mémoire : le plus gros pic observé par niveau, en Ko
        self.organes_gpu: set[str] = set()  # carte graphique : organes réveillés qui en ont besoin
        self.temps_economise = 0.0  # temps de calcul évité grâce aux réflexes, en µs
        self.taches = 0  # nombre de tâches traitées
        self.etapes = 0  # nombre d'étapes traitées

    @contextmanager
    def mesurer(self, niveau: str):
        """Mesure le temps et la mémoire du bloc de code placé sous « with compteur.mesurer(...) as mesure : ».

        À la fin du bloc, le dictionnaire « mesure » contient :
            mesure["temps"]   : le temps de calcul, en µs ;
            mesure["memoire"] : le pic de mémoire supplémentaire utilisé, en Ko.
        """
        if not tracemalloc.is_tracing():
            tracemalloc.start()  # on allume la surveillance de la mémoire, une seule fois
        tracemalloc.reset_peak()  # on remet le compteur de pic à zéro pour cette mesure
        memoire_avant, _ = tracemalloc.get_traced_memory()
        debut = time.perf_counter_ns()

        mesure = {"temps": 0.0, "memoire": 0.0}
        try:
            yield mesure  # ici s'exécute le bloc de code mesuré
        finally:
            mesure["temps"] = (time.perf_counter_ns() - debut) / 1000  # nanosecondes → microsecondes
            _, pic = tracemalloc.get_traced_memory()
            mesure["memoire"] = max(pic - memoire_avant, 0) / 1024  # octets → kilo-octets

            self.temps_par_niveau[niveau] = self.temps_par_niveau.get(niveau, 0.0) + mesure["temps"]
            self.memoire_par_niveau[niveau] = max(self.memoire_par_niveau.get(niveau, 0.0), mesure["memoire"])

    @property
    def temps_total(self) -> float:
        return sum(self.temps_par_niveau.values())

    def bilan(self, stockage_ko: float) -> str:
        """Un résumé lisible de toutes les ressources dépensées depuis le démarrage."""
        if not self.etapes:
            return "Aucune énergie dépensée pour l'instant."
        lignes = [
            f"Bilan pour {self.taches} tâche(s), {self.etapes} étape(s) :",
            f"⚡ Électricité (temps de calcul) : {self.temps_total:.0f} µs au total,"
            f" {self.temps_total / self.etapes:.0f} µs en moyenne par étape",
        ]
        for niveau, temps in sorted(self.temps_par_niveau.items(), key=lambda paire: -paire[1]):
            lignes.append(f"     - {niveau} : {temps:.0f} µs")
        pic = max(self.memoire_par_niveau.values(), default=0.0)
        lignes.append(f"🧠 Mémoire vive : pic de {pic:.1f} Ko")
        if self.organes_gpu:
            lignes.append(f"🎮 Carte graphique : utilisée par {', '.join(sorted(self.organes_gpu))}")
        if "aide extérieure" in self.temps_par_niveau:
            lignes.append(
                "⚠️ L'aide extérieure tourne dans un programme séparé (Ollama) : sa propre électricité et sa"
                " mémoire (souvent plus d'1 Go) ne sont pas comptées ici. Son vrai coût est bien plus élevé."
            )
        else:
            lignes.append("🎮 Carte graphique : non utilisée")
        lignes.append(f"💾 Stockage : {stockage_ko:.1f} Ko d'apprentissages sur le disque (réflexes, organes appris)")
        lignes.append(f"♻️ Économisé grâce aux réflexes : {self.temps_economise:.0f} µs de calcul")
        return "\n".join(lignes)
