"""La coordination : le cœur du noyau de Janova.

Pour chaque tâche, le noyau :
1. la découpe en étapes (voir decoupage.py) ;
2. traite chaque étape en essayant toujours **le moins cher d'abord** (règle 1) :
     niveau 1 : un réflexe déjà appris                          → presque gratuit
     niveau 2 : un organe spécialisé, du moins coûteux au plus coûteux
     niveau 3 : le raisonnement du noyau (relier une étape au résultat précédent)
     niveau 4 : l'aide extérieure, un modèle d'IA local         → très coûteux, en dernier recours ;
                elle en profite pour créer un nouvel organe (auto-extension)
3. mesure l'énergie dépensée à chaque niveau (règle 5) : électricité (temps de calcul), mémoire vive,
   carte graphique et stockage.

Les organes restent endormis tant qu'on n'a pas besoin d'eux (règle 2), et chaque réussite
d'un organe devient un réflexe (règle 3). La méthode dormir() endort les organes et fait le tri
dans les réflexes (règle 4).
"""

from dataclasses import dataclass
from pathlib import Path

from janova.aide_exterieure import AideExterieure
from janova.energie import CompteurEnergie
from janova.extension import CreateurOrganes
from janova.noyau.decoupage import decouper_en_etapes
from janova.noyau.raisonnement import resoudre_references
from janova.organes import TOUS_LES_ORGANES, Organe
from janova.reflexes import MemoireReflexes

# Le dossier où Janova garde ce qu'elle apprend : « donnees/ », à la racine du projet.
# __file__ est le chemin de ce fichier ; parents[2] remonte de noyau/ → janova/ → racine du projet.
DOSSIER_DONNEES = Path(__file__).resolve().parents[2] / "donnees"

# Valeur spéciale qui veut dire « l'utilisateur n'a rien précisé » : on crée alors l'aide extérieure normale.
# (On ne peut pas utiliser None pour ça, car None veut dire « pas d'aide extérieure du tout ».)
_AIDE_PAR_DEFAUT = object()


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
    def __init__(
        self,
        dossier_donnees: Path = DOSSIER_DONNEES,
        organes: list[type[Organe]] | None = None,
        aide=_AIDE_PAR_DEFAUT,
    ) -> None:
        dossier_donnees = Path(dossier_donnees)
        self.compteur = CompteurEnergie()
        self.reflexes = MemoireReflexes(dossier_donnees / "reflexes.json")
        organes_de_base = list(organes or TOUS_LES_ORGANES)

        # Niveau 4 et auto-extension. aide=None : Janova se débrouille sans aucune IA.
        aide = AideExterieure() if aide is _AIDE_PAR_DEFAUT else aide
        self.createur = None
        organes_appris = []
        if aide is not None:
            self.createur = CreateurOrganes(
                aide, dossier_donnees / "organes_appris", noms_reserves={o.nom for o in organes_de_base}
            )
            organes_appris = self.createur.charger_tous()  # les organes créés lors des utilisations précédentes

        # Règle 1 : on range les organes du moins cher au plus cher.
        self.organes_disponibles = organes_de_base + organes_appris
        self._ranger_organes()

        # Règle 2 : au démarrage, aucun organe n'est réveillé. Ce dictionnaire contiendra
        # seulement ceux qu'on a dû réveiller, rangés par nom.
        self.organes_eveilles: dict[str, Organe] = {}

    def _ranger_organes(self) -> None:
        """Trie les organes. sorted(..., key=...) range selon deux critères, dans l'ordre :
        1. ceux qui ont besoin de la carte graphique passent après tous les autres (False avant True) ;
        2. puis du coût annoncé le plus petit au plus grand.
        """
        self.organes_disponibles = sorted(self.organes_disponibles, key=lambda organe: (organe.besoin_gpu, organe.cout))

    def traiter(self, tache: str) -> Rapport:
        """Découpe la tâche en étapes, traite chacune, et renvoie le rapport."""
        resultats = []
        reponse_precedente = None  # la mémoire de travail : le résultat de l'étape d'avant (niveau 3)
        for etape in decouper_en_etapes(tache):
            resultat = self._traiter_etape(etape, reponse_precedente)
            resultats.append(resultat)
            if resultat.reponse is not None:
                reponse_precedente = resultat.reponse
        if resultats:
            self.compteur.taches += 1
            self.compteur.etapes += len(resultats)
            self.reflexes.sauvegarder()  # on garde les nouveaux réflexes, même si Janova est fermée ensuite
        return Rapport(tache, resultats)

    def _traiter_etape(self, etape: str, reponse_precedente: str | None) -> ResultatEtape:
        # --- Niveaux 1 et 2 : un réflexe, sinon un organe ------------------------------------------
        resultat = self._par_reflexe(etape) or self._par_organes(etape)
        if resultat is not None:
            return resultat

        # --- Niveau 3 : le raisonnement du noyau --------------------------------------------------
        # « multiplie le résultat par 4 » → « multiplie « 5 » par 4 », redonnée aux réflexes et aux organes.
        etape_reecrite = resoudre_references(etape, reponse_precedente)
        if etape_reecrite is not None:
            resultat = self._par_reflexe(etape_reecrite) or self._par_organes(etape_reecrite)
            if resultat is not None:
                resultat.etape = etape
                resultat.niveau = f"raisonnement + {resultat.niveau}"
                return resultat

        # --- Niveau 4 : l'aide extérieure, et l'auto-extension ------------------------------------
        if self.createur is not None:
            resultat = self._par_aide_exterieure(etape, etape_reecrite or etape)
            if resultat is not None:
                return resultat

        return ResultatEtape(etape, None, "aucun", 0.0, 0.0)

    def _par_reflexe(self, etape: str) -> ResultatEtape | None:
        """Niveau 1 (règle 3) : répond tout de suite si l'étape est déjà un réflexe."""
        with self.compteur.mesurer("réflexes") as mesure:
            reflexe = self.reflexes.chercher(etape)
        if reflexe is None:
            return None
        # On note le calcul économisé : ce qu'avait coûté la 1re fois, moins ce qu'a coûté le réflexe.
        self.compteur.temps_economise += max(reflexe.get("temps_initial", 0.0) - mesure["temps"], 0)
        return ResultatEtape(etape, reflexe["reponse"], "réflexe", mesure["temps"], mesure["memoire"])

    def _par_organes(self, etape: str) -> ResultatEtape | None:
        """Niveau 2 (règles 1 et 2) : confie l'étape au moins cher des organes qui la reconnaissent."""
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
        return None

    def _par_aide_exterieure(self, etape: str, cible: str) -> ResultatEtape | None:
        """Niveau 4 : demande à l'IA locale. Si elle écrit un nouvel organe, Janova le garde (auto-extension)."""
        with self.compteur.mesurer("aide extérieure") as mesure:
            nouvel_organe, reponse = self.createur.resoudre(cible)
        if reponse is None:
            return None
        self.compteur.organes_gpu.add(self.createur.aide.nom)

        if nouvel_organe is None:
            # Réponse directe de l'IA : on ne la transforme pas en réflexe, car on ne peut pas la vérifier.
            return ResultatEtape(etape, reponse, "aide extérieure", mesure["temps"], mesure["memoire"])

        # Auto-extension : le nouvel organe rejoint les autres. Les étapes du même genre ne demanderont
        # plus l'IA. Sa réponse, vérifiée par ses tests, devient aussi un réflexe.
        self.organes_disponibles.append(nouvel_organe)
        self._ranger_organes()
        self.reflexes.apprendre(cible, reponse, nouvel_organe.nom, mesure["temps"])
        niveau = f"aide extérieure → nouvel organe « {nouvel_organe.nom} »"
        return ResultatEtape(etape, reponse, niveau, mesure["temps"], mesure["memoire"])

    def _reveiller(self, classe: type[Organe]) -> Organe:
        """Règle 2 : réveille un organe seulement la première fois qu'on en a besoin."""
        if classe.nom not in self.organes_eveilles:
            self.organes_eveilles[classe.nom] = classe()  # classe() crée l'organe : c'est son réveil
            if classe.besoin_gpu:
                self.compteur.organes_gpu.add(classe.nom)
        return self.organes_eveilles[classe.nom]

    def organes(self) -> str:
        """La liste des organes, du moins cher au plus cher."""
        lignes = []
        for classe in self.organes_disponibles:
            etat = "réveillé" if classe.nom in self.organes_eveilles else "endormi"
            gpu = ", carte graphique" if classe.besoin_gpu else ""
            appris = " (appris)" if hasattr(classe, "code") else ""
            lignes.append(f"  - {classe.nom}{appris} : coût {classe.cout}{gpu}, {etat}")
        if self.createur is None:
            lignes.append("Aide extérieure : désactivée")
        elif self.createur.aide.indisponible:
            lignes.append(f"Aide extérieure : {self.createur.aide.indisponible}")
        else:
            lignes.append(f"Aide extérieure : {self.createur.aide.modele} via Ollama (en dernier recours)")
        return "\n".join(lignes)

    def bilan(self) -> str:
        """Le bilan de toutes les ressources dépensées depuis le démarrage."""
        return self.compteur.bilan(stockage_ko=self._stockage_ko())

    def _stockage_ko(self) -> float:
        """La place occupée sur le disque par tout ce que Janova a appris (réflexes et organes appris)."""
        taille = self.reflexes.taille_ko()
        if self.createur is not None and self.createur.dossier.exists():
            taille += sum(f.stat().st_size for f in self.createur.dossier.glob("*.json")) / 1024
        return taille

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
