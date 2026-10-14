"""La coordination : le cœur du noyau de Janova.

Pour chaque tâche, le noyau :
1. la découpe en étapes (voir decoupage.py) ;
2. traite chaque étape en essayant toujours **le moins cher d'abord** (règle 1) :
     niveau 1 : un réflexe déjà appris          → presque gratuit
     niveau 2 : un organe spécialisé, du moins coûteux au plus coûteux
     niveau 3 : le raisonnement du noyau        → pas encore construit
     niveau 4 : une aide extérieure (grand modèle d'IA) → pas encore construite
3. mesure l'énergie dépensée à chaque niveau (règle 5) : électricité (temps de calcul), mémoire vive,
   carte graphique et stockage.

Les organes restent endormis tant qu'on n'a pas besoin d'eux (règle 2), et chaque réussite
d'un organe devient un réflexe (règle 3). La méthode dormir() endort les organes et fait le tri
dans les réflexes (règle 4).
"""

from dataclasses import dataclass
from pathlib import Path

from janova.energie import CompteurEnergie
from janova.noyau.decoupage import decouper_en_etapes
from janova.organes import TOUS_LES_ORGANES, Organe
from janova.reflexes import MemoireReflexes

# Le dossier où Janova garde ce qu'elle apprend : « donnees/ », à la racine du projet.
# __file__ est le chemin de ce fichier ; parents[2] remonte de noyau/ → janova/ → racine du projet.
DOSSIER_DONNEES = Path(__file__).resolve().parents[2] / "donnees"


@dataclass
class ResultatEtape:
    """Ce qui s'est passé pour une étape."""

    etape: str
    reponse: str | None  # None si aucune partie de Janova n'a su la traiter
    niveau: str  # qui a répondu : « réflexe », « organe calcul »… ou « aucun »
    temps: float  # électricité : temps de calcul, en microsecondes (µs)
    memoire: float  # mémoire vive : pic utilisé, en kilo-octets (Ko)


@dataclass
class Rapport:
    """Le compte rendu d'une tâche complète."""

    tache: str
    etapes: list[ResultatEtape]

    @property
    def temps(self) -> float:
        return sum(resultat.temps for resultat in self.etapes)

    @property
    def memoire(self) -> float:
        return max((resultat.memoire for resultat in self.etapes), default=0.0)

    def texte(self) -> str:
        """Le rapport sous forme de texte, prêt à afficher."""
        if not self.etapes:
            return "Je n'ai reçu aucune tâche."
        lignes = []
        for numero, resultat in enumerate(self.etapes, start=1):
            if resultat.reponse is None:
                lignes.append(f"  {numero}. {resultat.etape} → je ne sais pas encore faire cette étape")
            else:
                lignes.append(
                    f"  {numero}. {resultat.etape} → {resultat.reponse}"
                    f"   [{resultat.niveau}, {resultat.temps:.0f} µs, {resultat.memoire:.1f} Ko]"
                )
        lignes.append(f"Énergie dépensée : {self.temps:.0f} µs de calcul, pic de {self.memoire:.1f} Ko de mémoire")
        return "\n".join(lignes)


class Janova:
    def __init__(self, dossier_donnees: Path = DOSSIER_DONNEES, organes: list[type[Organe]] | None = None) -> None:
        self.compteur = CompteurEnergie()
        self.reflexes = MemoireReflexes(Path(dossier_donnees) / "reflexes.json")

        # Règle 1 : on range les organes du moins cher au plus cher, une fois pour toutes.
        # sorted(..., key=...) trie selon deux critères, dans l'ordre :
        #   1. ceux qui ont besoin de la carte graphique passent après tous les autres (False avant True) ;
        #   2. puis du coût annoncé le plus petit au plus grand.
        self.organes_disponibles = sorted(
            organes or TOUS_LES_ORGANES, key=lambda organe: (organe.besoin_gpu, organe.cout)
        )

        # Règle 2 : au démarrage, aucun organe n'est réveillé. Ce dictionnaire contiendra
        # seulement ceux qu'on a dû réveiller, rangés par nom.
        self.organes_eveilles: dict[str, Organe] = {}

    def traiter(self, tache: str) -> Rapport:
        """Découpe la tâche en étapes, traite chacune, et renvoie le rapport."""
        resultats = [self._traiter_etape(etape) for etape in decouper_en_etapes(tache)]
        if resultats:
            self.compteur.taches += 1
            self.compteur.etapes += len(resultats)
            self.reflexes.sauvegarder()  # on garde les nouveaux réflexes, même si Janova est fermée ensuite
        return Rapport(tache, resultats)

    def _traiter_etape(self, etape: str) -> ResultatEtape:
        # --- Niveau 1 : un réflexe ? -------------------------------------------------------------
        with self.compteur.mesurer("réflexes") as mesure:
            reflexe = self.reflexes.chercher(etape)
        if reflexe is not None:
            # On note le calcul économisé : ce qu'avait coûté l'organe, moins ce qu'a coûté le réflexe.
            self.compteur.temps_economise += max(reflexe.get("temps_initial", 0.0) - mesure["temps"], 0)
            return ResultatEtape(etape, reflexe["reponse"], "réflexe", mesure["temps"], mesure["memoire"])

        # --- Niveau 2 : un organe, du moins cher au plus cher -------------------------------------
        for classe in self.organes_disponibles:
            # On demande d'abord à l'organe endormi s'il reconnaît l'étape : ça ne coûte presque rien.
            if not classe.reconnait(etape):
                continue
            with self.compteur.mesurer(f"organe {classe.nom}") as mesure:
                organe = self._reveiller(classe)
                reponse = organe.traiter(etape)
            if reponse is not None:
                # Règle 3 : une réussite devient un réflexe, si la réponse ne change jamais.
                if classe.deterministe:
                    self.reflexes.apprendre(etape, reponse, classe.nom, mesure["temps"])
                return ResultatEtape(etape, reponse, f"organe {classe.nom}", mesure["temps"], mesure["memoire"])

        # --- Niveau 3 : le raisonnement du noyau --------------------------------------------------
        # Pas encore construit. Plus tard, le noyau pourra combiner plusieurs organes
        # pour résoudre une étape qu'aucun ne sait traiter seul.

        # --- Niveau 4 : l'aide extérieure ---------------------------------------------------------
        # Pas encore construite. En tout dernier recours, Janova pourra demander à un grand modèle
        # d'IA, puis transformer ce qu'elle a appris en réflexe ou en nouvel organe.

        return ResultatEtape(etape, None, "aucun", 0.0, 0.0)

    def _reveiller(self, classe: type[Organe]) -> Organe:
        """Règle 2 : réveille un organe seulement la première fois qu'on en a besoin."""
        if classe.nom not in self.organes_eveilles:
            self.organes_eveilles[classe.nom] = classe()  # classe() crée l'organe : c'est son réveil
            if classe.besoin_gpu:
                self.compteur.organes_gpu.add(classe.nom)
        return self.organes_eveilles[classe.nom]

    def bilan(self) -> str:
        """Le bilan de toutes les ressources dépensées depuis le démarrage."""
        return self.compteur.bilan(stockage_ko=self.reflexes.taille_ko())

    def dormir(self, oubli_apres_jours: int = 30) -> str:
        """Le sommeil : endort tous les organes (règle 2) et fait le tri dans les réflexes (règle 4)."""
        endormis = len(self.organes_eveilles)
        self.organes_eveilles.clear()
        oublies = self.reflexes.consolider(oubli_apres_jours)
        self.reflexes.sauvegarder()
        return (
            f"Bonne nuit. {endormis} organe(s) endormi(s), {oublies} réflexe(s) inutile(s) oublié(s), "
            f"{len(self.reflexes)} réflexe(s) gardé(s)."
        )
