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
d'un organe devient un réflexe (règle 3). La méthode dormir() endort les organes, laisse les réflexes
inutiles s'effacer et fait évoluer les organes appris (règle 4).

Les mécanismes bio-inspirés qui entourent tout ça :
- l'attention (attention.py) : une tâche répétée reçoit une réponse de mémoire immédiate (habituation),
  une tâche urgente a droit à plus de ressources (adrénaline) ;
- l'homéostasie (homeostasie.py) : selon la batterie, la mémoire et la température, Janova passe en mode
  économie (plus d'aide extérieure, sauf urgence) ou survie (seulement réflexes et organes de base).

Et autour de l'architecture « corps vivant » :
- les décisions rapides (decision.py), inspirées de Jev : choisir parmi des options, avec un % de confiance ;
- le carnet d'idées (idees.py) : chaque idée est rangée par ces décisions dans un graphe façon Obsidian ;
- la croissance (croissance.py) : le journal de qui a résolu chaque étape, le taux d'autonomie et le stade de vie ;
- les mains (mains/) : agir sur l'ordinateur avec des gestes sûrs ; Janova demande ton accord tant qu'elle
  n'a pas gagné ta confiance pour un geste (niveau 2 bis, juste après les organes) ;
- les yeux (yeux.py) et les routines (routines.py) : remarquer tes habitudes et les faire à ta place.
"""

import zlib
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from janova.aide_exterieure import AideExterieure
from janova.attention import Attention
from janova.croissance import Croissance
from janova.decision import Decideur
from janova.energie import CompteurEnergie
from janova.extension import CreateurOrganes
from janova.homeostasie import ECONOMIE, NORMAL, SURVIE, Homeostasie
from janova.idees import CarnetIdees
from janova.mains import Contexte, Mains, Proposition
from janova.noyau.decoupage import decouper_en_etapes
from janova.noyau.raisonnement import resoudre_references
from janova.organes import TOUS_LES_ORGANES, Organe
from janova.reflexes import MemoireReflexes
from janova.routines import Routines, extraire_routine
from janova.yeux import Habitude, Yeux

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
class PropositionRoutine:
    """Une habitude repérée par les yeux, que Janova propose de transformer en routine."""

    habitude: Habitude

    def decrire(self) -> str:
        h = self.habitude
        return (f"j'ai remarqué que tu fais « {h.quoi} » le {h.moment} ({h.jours} jours différents). "
                f"Je le fais pour toi chaque jour à {h.heure} ?")


@dataclass
class Rapport:
    """Le compte rendu d'une tâche complète."""

    tache: str
    etapes: list[ResultatEtape]
    note: str = ""  # un message de l'attention ou de l'homéostasie (habituation, mode économie…)

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
        lignes = [self.note] if self.note else []
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
        homeostasie: Homeostasie | None = None,
        attention: Attention | None = None,
        contexte_systeme: Contexte | None = None,
    ) -> None:
        dossier_donnees = Path(dossier_donnees)
        self.compteur = CompteurEnergie()
        self.homeostasie = homeostasie or Homeostasie()
        self.attention = attention or Attention()
        self.reflexes = MemoireReflexes(dossier_donnees / "reflexes.json")
        self.croissance = Croissance(dossier_donnees / "croissance.json")
        self.decideur = Decideur(dossier_donnees / "decisions.json")
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
        self.idees = CarnetIdees(dossier_donnees / "idees", self.decideur, aide)
        self.yeux = Yeux(dossier_donnees / "yeux", contexte_systeme.maison if contexte_systeme else None)
        self.routines = Routines(dossier_donnees / "routines.json")
        self.mains = Mains(dossier_donnees / "mains", self.decideur, contexte_systeme, aide, self.yeux.noter)
        # Ce qui attend ton accord (oui / non) : des gestes des mains ou des routines proposées par les yeux.
        self.en_attente: list[Proposition | PropositionRoutine] = []
        self._derniere_proposition_d_habitude = datetime.min

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
        # --- L'attention : habituation ------------------------------------------------------------
        # Tâche répétée plusieurs fois en une minute : réponse de mémoire immédiate, sans rien recalculer.
        if self.attention.remarquer(tache):
            with self.compteur.mesurer("habituation") as mesure:
                souvenir = self.attention.souvenir(tache)
            # La dépense mesurée est partagée entre les étapes, pour ne pas la compter plusieurs fois.
            part = mesure["temps"] / max(len(souvenir.etapes), 1)
            etapes = [ResultatEtape(r.etape, r.reponse, "habituation", part, mesure["memoire"])
                      for r in souvenir.etapes]
            self._compter(etapes)
            for resultat in etapes:
                self.croissance.noter(resultat.niveau if resultat.reponse is not None else "aucun")
            self.croissance.sauvegarder()
            return Rapport(tache, etapes, "Tâche répétée : réponse de mémoire immédiate (habituation).")

        # --- L'homéostasie et l'urgence : quelles ressources sont permises ? -------------------------
        mode, raison = self.homeostasie.mode()
        urgente = self.attention.est_urgente(tache)
        aide_permise = self._aide_permise(mode, urgente)
        appris_permis = mode != SURVIE  # en survie, pas de bac à sable : seulement l'essentiel
        note = ""
        if mode != NORMAL:
            note = f"Mode {mode} ({raison})"
            note += " : urgence, ressources débloquées." if urgente and aide_permise else " : aide extérieure coupée."
            if not appris_permis:
                note = note[:-1] + ", organes appris en pause."

        resultats = []
        reponse_precedente = None  # la mémoire de travail : le résultat de l'étape d'avant (niveau 3)
        for etape in decouper_en_etapes(tache):
            resultat = self._traiter_etape(etape, reponse_precedente, aide_permise, appris_permis)
            resultats.append(resultat)
            if resultat.reponse is not None:
                reponse_precedente = resultat.reponse
        rapport = Rapport(tache, resultats, note)
        if resultats:
            self._compter(resultats)
            for resultat in resultats:
                self.croissance.noter(resultat.niveau)
            self.croissance.sauvegarder()
            self.reflexes.sauvegarder()  # on garde les nouveaux réflexes, même si Janova est fermée ensuite
            # Une tâche qui agit sur l'ordinateur ne doit jamais être « répondue de mémoire » : on ne la retient pas.
            if not any(r.niveau.startswith("mains") or "recette" in r.niveau for r in resultats):
                self.attention.retenir(tache, rapport)
        return rapport

    @staticmethod
    def _aide_permise(mode: str, urgente: bool) -> bool:
        """L'aide extérieure est permise en mode normal, ou en mode économie si c'est urgent (l'adrénaline)."""
        return mode == NORMAL or (mode == ECONOMIE and urgente)

    def ranger_idee(self, saisie: str):
        """Range une idée dans le carnet : toi, puis réflexe de décision, puis professeur (voir idees.py)."""
        mode, _ = self.homeostasie.mode()
        aide_permise = self.createur is not None and self._aide_permise(mode, self.attention.est_urgente(saisie))
        with self.compteur.mesurer("idées") as mesure:
            idee = self.idees.ranger(saisie, aide_permise)
        idee.temps = mesure["temps"]
        if idee.rangee_par == "professeur":
            self.compteur.organes_gpu.add(self.createur.aide.nom)
        self.croissance.noter(idee.rangee_par)
        self.croissance.sauvegarder()
        return idee

    def etat_croissance(self) -> str:
        """Le stade de vie, le taux d'autonomie et ce que Janova a appris."""
        appris = sum(1 for classe in self.organes_disponibles if hasattr(classe, "fiche"))
        return self.croissance.resume(len(self.reflexes), appris, len(self.idees))

    def _compter(self, resultats: list[ResultatEtape]) -> None:
        self.compteur.taches += 1
        self.compteur.etapes += len(resultats)

    def _traiter_etape(
        self, etape: str, reponse_precedente: str | None, aide_permise: bool = True, appris_permis: bool = True
    ) -> ResultatEtape:
        # --- Niveaux 1 et 2 : un réflexe, sinon un organe ------------------------------------------
        resultat = self._par_reflexe(etape) or self._par_organes(etape, appris_permis)
        if resultat is not None:
            return resultat

        # --- Niveau 2 bis : les mains (une action sur l'ordinateur, par réflexe ou recette apprise) -------
        resultat = self._par_mains(etape, aide_permise=False)
        if resultat is not None:
            return resultat

        # --- Niveau 3 : le raisonnement du noyau --------------------------------------------------
        # « multiplie le résultat par 4 » → « multiplie « 5 » par 4 », redonnée aux réflexes et aux organes.
        etape_reecrite = resoudre_references(etape, reponse_precedente)
        if etape_reecrite is not None:
            resultat = self._par_reflexe(etape_reecrite) or self._par_organes(etape_reecrite, appris_permis)
            if resultat is not None:
                resultat.etape = etape
                resultat.niveau = f"raisonnement + {resultat.niveau}"
                return resultat

        # --- Niveau 4 : l'aide extérieure, et l'auto-extension ------------------------------------
        # Une action sur l'ordinateur : le professeur l'apprend aux mains (une recette de gestes sûrs).
        if self.createur is not None and aide_permise and self.mains.semble_une_action(etape):
            resultat = self._par_mains(etape, aide_permise=True)
            if resultat is not None:
                return resultat
        if self.createur is not None and aide_permise:
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

    def _par_organes(self, etape: str, appris_permis: bool = True) -> ResultatEtape | None:
        """Niveau 2 (règles 1 et 2) : confie l'étape au moins cher des organes qui la reconnaissent."""
        for classe in self.organes_disponibles:
            appris = hasattr(classe, "fiche")
            if appris and not appris_permis:
                continue  # mode survie : les organes appris (et leur bac à sable) restent au repos
            # On demande d'abord à l'organe endormi s'il reconnaît l'étape : ça ne coûte presque rien.
            if not classe.reconnait(etape):
                continue
            with self.compteur.mesurer(f"organe {classe.nom}") as mesure:
                organe = self._reveiller(classe)
                reponse = organe.traiter(etape)
            if reponse is None and appris and self.createur is not None:
                # Fausse alerte : réveillé pour rien. On la note pour que l'organe évolue pendant le sommeil.
                self.createur.noter_fausse_alerte(classe, etape)
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

    def _par_mains(self, etape: str, aide_permise: bool) -> ResultatEtape | None:
        """Niveau 2 bis : une action sur l'ordinateur. Faite tout de suite si Janova a ta confiance, sinon proposée."""
        with self.compteur.mesurer("mains") as mesure:
            proposition = self.mains.preparer(etape, aide_permise)
            if proposition is None:
                return None
            if self.mains.peut_agir_seule(proposition):
                reponse = self.mains.executer(proposition, avec_accord=False)
                attente = False
            else:
                self.en_attente.append(proposition)
                reponse = f"Je propose : {proposition.decrire()}. D'accord ? (oui / non)"
                attente = True
        if proposition.origine == "professeur":
            self.compteur.organes_gpu.add(self.createur.aide.nom)
            niveau = "aide extérieure → recette pour les mains"
        else:
            niveau = f"mains, {proposition.origine}"
        if attente:
            niveau += ", attend ton accord"
        return ResultatEtape(etape, reponse, niveau, mesure["temps"], mesure["memoire"])

    def valider(self, oui: bool) -> str:
        """Ta réponse (oui / non) à la plus ancienne proposition en attente."""
        if not self.en_attente:
            return "Je n'attends aucune réponse de ta part."
        proposition = self.en_attente.pop(0)
        if isinstance(proposition, PropositionRoutine):
            habitude = proposition.habitude
            if oui:
                self.yeux.proposee(habitude)
                routine = self.routines.ajouter(habitude.heure, list(range(7)), habitude.quoi)
                texte = f"C'est noté : {routine.decrire()}."
            else:
                self.yeux.refusee(habitude)
                texte = "D'accord, je ne te le proposerai plus."
        elif oui:
            texte = self.mains.executer(proposition)
        else:
            texte = self.mains.refuser(proposition)
        if self.en_attente:
            texte += f"\nEnsuite : {self.en_attente[0].decrire()} (oui / non)"
        return texte

    def creer_routine(self, phrase: str) -> str | None:
        """« tous les matins, change mon thème » → une routine. None si la phrase n'en décrit pas une."""
        trouvee = extraire_routine(phrase)
        if trouvee is None:
            return None
        heure, jours, tache = trouvee
        routine = self.routines.ajouter(heure, jours, tache)
        return f"C'est noté : {routine.decrire()}. (/routines pour les voir)"

    def vivre(self, maintenant: datetime | None = None) -> list[str]:
        """Appelée chaque minute par la fenêtre : lancer les routines, regarder, proposer des habitudes."""
        maintenant = maintenant or datetime.now()
        messages = []
        for routine in self.routines.dues(maintenant):
            messages.append(f"Routine ({routine.decrire()}) :\n{self.traiter(routine.tache).texte()}")
        self.yeux.regarder()
        # Au plus une proposition d'habitude par heure, et jamais deux à la fois : Janova ne harcèle pas.
        deja = any(isinstance(p, PropositionRoutine) for p in self.en_attente)
        if not deja and maintenant - self._derniere_proposition_d_habitude >= timedelta(hours=1):
            for habitude in self.yeux.habitudes(maintenant):
                if not self.routines.existe(habitude.quoi):
                    proposition = PropositionRoutine(habitude)
                    self.en_attente.append(proposition)
                    self._derniere_proposition_d_habitude = maintenant
                    messages.append(proposition.decrire()[0].upper() + proposition.decrire()[1:] + " (oui / non)")
                    break
                self.yeux.proposee(habitude)  # déjà une routine : inutile de la proposer
        return messages

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
            appris = ""
            if hasattr(classe, "fiche"):
                appris = (f" (appris, génération {classe.fiche.get('generation', 1)},"
                          f" mots-clés : {', '.join(classe.mots_cles)})")
            lignes.append(f"  - {classe.nom}{appris} : coût {classe.cout}{gpu}, {etat}")
        if self.createur is None:
            lignes.append("Aide extérieure : désactivée")
        elif self.createur.aide.indisponible:
            lignes.append(f"Aide extérieure : {self.createur.aide.indisponible}")
        else:
            lignes.append(f"Aide extérieure : {self.createur.aide.modele} via Ollama (en dernier recours)")
        return "\n".join(lignes)

    def etat(self) -> str:
        """Les signes vitaux et le mode choisi par l'homéostasie."""
        return self.homeostasie.etat()

    def bilan(self) -> str:
        """Le bilan de toutes les ressources dépensées depuis le démarrage."""
        return self.compteur.bilan(stockage_ko=self._stockage_ko())

    def _stockage_ko(self) -> float:
        """La place occupée sur le disque par tout ce que Janova a appris (réflexes et organes appris)."""
        taille = self.reflexes.taille_ko()
        if self.createur is not None and self.createur.dossier.exists():
            taille += sum(f.stat().st_size for f in self.createur.dossier.glob("*.json")) / 1024
        return taille

    def dormir(self) -> str:
        """Le sommeil (règle 4) : endormir les organes, faire évoluer les organes appris, oublier ce qui ne sert pas."""
        endormis = len(self.organes_eveilles)
        self.organes_eveilles.clear()

        # Évolution : les organes appris qui ont eu des fausses alertes essaient de meilleurs mots-clés.
        # Leurs étapes réussies (retrouvées dans les réflexes) servent de référence à ne jamais perdre.
        evolues = 0
        if self.createur is not None:
            for classe in self.organes_disponibles:
                if hasattr(classe, "fiche"):
                    reussies = [cle for cle, r in self.reflexes.reflexes.items() if r["organe"] == classe.nom]
                    # crc32 donne un nombre fixe pour chaque nom : la même nuit donne toujours le même résultat.
                    if self.createur.faire_evoluer(classe, reussies, graine=zlib.crc32(classe.nom.encode())):
                        evolues += 1

        oublies = self.reflexes.consolider()  # la courbe de l'oubli : les réflexes trop faibles s'effacent
        self.reflexes.sauvegarder()
        self.croissance.sauvegarder()
        self.idees.sauvegarder()
        return (
            f"Bonne nuit. {endormis} organe(s) endormi(s), {evolues} organe(s) appris amélioré(s) par évolution, "
            f"{oublies} réflexe(s) effacé(s), {len(self.reflexes)} réflexe(s) gardé(s)."
        )
