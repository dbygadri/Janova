"""Les mains de Janova : comprendre une demande sur l'ordinateur et la réaliser avec des gestes sûrs.

Comment Janova comprend ce que tu veux faire, du moins cher au plus cher :
1. **réflexe des mains** : des formules connues (« range mes téléchargements », « mets le thème sombre »…) ;
2. **recette apprise** : une demande qu'un professeur lui a déjà appris à faire ;
3. **professeur** : sinon, l'aide extérieure traduit ta demande en une suite de gestes connus.
   Cette traduction devient une recette, gardée pour toujours si tu l'acceptes.

Avant d'agir, Janova te montre ce qu'elle va faire, sauf si tu lui as déjà fait confiance pour ce geste
(voir confiance.py). Tout ce qui peut s'annuler est noté : /annuler remet comme avant.
"""

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

from janova.decision import Decideur, mots
from janova.mains.confiance import Confiance
from janova.mains.primitives import PRIMITIVES, Contexte, Primitive, sans_accents
from janova.reflexes.memoire import cle

MEMOIRE_ANNULATION = 20  # on garde de quoi annuler les 20 dernières actions


@dataclass
class Geste:
    primitive: Primitive
    parametres: dict[str, str]

    def decrire(self) -> str:
        valeurs = [v for v in self.parametres.values() if v]
        return self.primitive.description + (f" ({' → '.join(valeurs)})" if valeurs else "")


@dataclass
class Proposition:
    """Ce que Janova propose de faire pour une demande."""

    demande: str
    gestes: list[Geste]
    origine: str  # « réflexe des mains », « recette apprise » ou « professeur »
    recette: str | None = None  # l'identifiant de la recette utilisée, s'il y en a une

    def decrire(self) -> str:
        return " ; puis ".join(geste.decrire() for geste in self.gestes)


@dataclass
class Action:
    """Une action réalisée, avec de quoi l'annuler."""

    description: str
    annulations: list[Callable[[], str]] = field(default_factory=list)


# --- 1. Le réflexe des mains : des formules connues ------------------------------------------------

ARTICLES = r"^(?:l'|le |la |les |mon |ma |mes |un |une |des |du )?(?:(?:application|appli|logiciel|fichier|dossier)(?:\s+|$))?"


def _apres(original: str, simplifie: str, motif: str) -> str | None:
    """Trouve le motif dans le texte simplifié et renvoie la suite, prise dans le texte original (avec accents)."""
    trouve = re.search(motif, simplifie)
    if not trouve:
        return None
    reste = original[trouve.end():].strip(" :,.!")
    return re.sub(ARTICLES, "", reste, flags=re.IGNORECASE).strip()


def comprendre(etape: str) -> list[tuple[str, dict[str, str]]] | None:
    """Traduit une demande courante en gestes, sans IA. None si la formule n'est pas connue."""
    s = sans_accents(etape).strip()  # même longueur que l'original : les positions correspondent
    o = etape.strip()

    if "fond d'ecran" in s or "fond d ecran" in s or "fond-d-ecran" in s or "wallpaper" in s:
        image = re.search(r"(~?/\S+\.(?:jpe?g|png|webp))", o, re.IGNORECASE)
        return [("fond_ecran", {"image": image.group(1) if image else ""})]
    if re.search(r"\btheme\b|\bmode (sombre|clair|nuit|jour)\b", s):
        mode = "sombre" if re.search(r"sombre|nuit|noir", s) else "clair" if re.search(r"clair|jour|blanc", s) else "inverse"
        return [("theme", {"mode": mode})]
    if re.search(r"\b(supprime|efface|jette)\w*\b|\bcorbeille\b", s):
        cible = _apres(o, s, r"\b(supprime|efface|jette)\w*\b|\b(mets?|met)\b")
        cible = re.sub(r"\s*(a|à) la corbeille$", "", cible or "", flags=re.IGNORECASE).strip()
        return [("corbeille", {"chemin": cible})] if cible else None
    deplace = re.search(r"\b(deplace|bouge|mets?|met|range)\s+(.+?)\s+(dans|vers)\s+(.+)$", s)
    if deplace:
        source = re.sub(ARTICLES, "", o[deplace.start(2):deplace.end(2)], flags=re.IGNORECASE)
        destination = re.sub(ARTICLES, "", o[deplace.start(4):].strip(" .!"), flags=re.IGNORECASE)
        return [("deplacer", {"source": source.strip(), "destination": destination.strip()})]
    dossier = re.search(r"\bcree\w*\s+(?:un |le )?(?:nouveau )?dossier\s+(.+?)(?:\s+dans\s+(.+))?$", s)
    if dossier:
        nom = o[dossier.start(1):dossier.end(1)].strip(" «»\"'")
        parent = o[dossier.start(2):].strip(" .!") if dossier.group(2) else ""
        return [("creer_dossier", {"chemin": f"{re.sub(ARTICLES, '', parent, flags=re.IGNORECASE)}/{nom}" if parent else nom})]
    if re.search(r"\b(range|trie|organise|classe|nettoie|tri)\w*\b", s):
        cible = _apres(o, s, r"\b(range|trie|organise|classe|nettoie|tri)\w*\b") or ""
        if not cible or sans_accents(cible).startswith(("dossier", "fichier")):
            cible = "téléchargements"  # « trie mes dossiers » : le dossier qui déborde le plus souvent
        return [("ranger_dossier", {"dossier": cible})]
    if re.match(r"(ouvre|lance|demarre|affiche)\b", s):
        cible = _apres(o, s, r"^(ouvre|lance|demarre|affiche)\w*\b")
        return [("ouvrir", {"cible": cible})] if cible else None
    if re.match(r"(notifie|previens|rappelle)[- ]?moi\b", s):
        texte = _apres(o, s, r"^(notifie|previens|rappelle)[- ]?moi\b\s*(de |que |d'|:)?")
        return [("notifier", {"texte": texte})] if texte else None
    return None


# --- Les mains ------------------------------------------------------------------------------------


class Mains:
    def __init__(self, dossier: Path, decideur: Decideur, contexte: Contexte | None = None,
                 aide=None, quand_action: Callable[[str], None] | None = None) -> None:
        self.dossier = Path(dossier)
        self.decideur = decideur
        self.contexte = contexte or Contexte()
        self.aide = aide
        self.confiance = Confiance(self.dossier / "confiance.json")
        self.quand_action = quand_action  # les yeux s'abonnent ici pour remarquer les habitudes
        self.historique: list[Action] = []
        self.chemin_recettes = self.dossier / "recettes.json"
        self.recettes: dict[str, dict] = {}
        if self.chemin_recettes.exists():
            try:
                self.recettes = json.loads(self.chemin_recettes.read_text(encoding="utf-8"))
            except ValueError:
                self.chemin_recettes.replace(self.chemin_recettes.with_suffix(".abime"))

    # --- Comprendre ---------------------------------------------------------------------------------

    def preparer(self, etape: str, aide_permise: bool = False) -> Proposition | None:
        """Traduit une demande en gestes : réflexe, puis recette apprise, puis professeur."""
        gestes = comprendre(etape)
        if gestes:
            return self._proposition(etape, gestes, "réflexe des mains")
        recette = self._chercher_recette(etape)
        if recette:
            return self._proposition(etape, self.recettes[recette]["gestes"], "recette apprise", recette)
        if aide_permise and self.aide is not None and self.semble_une_action(etape):
            return self._demander_au_professeur(etape)
        return None

    def semble_une_action(self, etape: str) -> bool:
        """Décision rapide : cette demande concerne-t-elle l'ordinateur (et pas un calcul, une question…) ?"""
        if not self.decideur.options("action sur l'ordinateur"):
            self.decideur.enseigner("action sur l'ordinateur", "ouvre lance ferme fichier dossier fond écran thème "
                                    "range trie déplace application fenêtre bureau wifi volume son luminosité "
                                    "installe imprime capture écran sauvegarde copie renomme", "oui")
            self.decideur.enseigner("action sur l'ordinateur", "calcule convertis combien traduis explique résume "
                                    "définition capitale pourquoi qui raconte poème histoire", "non")
        decision = self.decideur.oui_non("action sur l'ordinateur", etape)
        return decision is not None and decision.choix == "oui" and decision.sure

    def _proposition(self, etape, gestes, origine, recette=None) -> Proposition | None:
        valides = []
        for geste in gestes:
            nom, parametres = (geste["primitive"], geste["parametres"]) if isinstance(geste, dict) else geste
            primitive = PRIMITIVES.get(nom)
            if primitive is None:
                return None
            valides.append(Geste(primitive, {k: str(v) for k, v in parametres.items() if k in primitive.parametres}))
        return Proposition(etape, valides, origine, recette) if valides else None

    def _chercher_recette(self, etape: str) -> str | None:
        if cle(etape) in self.recettes:
            return cle(etape)
        validees = [r for r, fiche in self.recettes.items() if fiche.get("validee")]
        decision = self.decideur.choisir("recette", etape, validees) if validees else None
        connus = {m for f in self.decideur.connaissances.get("recette", {}).values() for m in f["mots"]}
        if decision and decision.sure and len(set(mots(etape)) & connus) >= 2:
            return decision.choix
        return None

    def _demander_au_professeur(self, etape: str) -> Proposition | None:
        catalogue = "\n".join(f'- {p.nom}({", ".join(p.parametres)}) : {p.description}' for p in PRIMITIVES.values())
        question = (
            "Tu aides une IA locale à agir sur un ordinateur Linux. Elle ne peut utiliser QUE ces gestes :\n"
            f"{catalogue}\n"
            "Traduis la demande en une liste de gestes. Si c'est impossible avec ces gestes, renvoie une liste vide.\n"
            'Réponds seulement en JSON : {"gestes": [{"primitive": "...", "parametres": {"...": "..."}}]}\n'
            f"Demande : {etape}"
        )
        reponse = self.aide.demander(question, en_json=True)
        try:
            gestes = json.loads(reponse or "").get("gestes", [])
        except (ValueError, AttributeError):
            return None
        if not isinstance(gestes, list) or not all(isinstance(g, dict) and isinstance(g.get("parametres", {}), dict)
                                                   for g in gestes):
            return None
        gestes = [{"primitive": g.get("primitive"), "parametres": g.get("parametres", {})} for g in gestes]
        proposition = self._proposition(etape, gestes, "professeur")
        if proposition is None:
            return None
        # La leçon devient une recette, gardée pour de bon seulement si tu l'acceptes (voir executer).
        identifiant = cle(etape)
        self.recettes[identifiant] = {
            "demande": etape,
            "gestes": [{"primitive": g.primitive.nom, "parametres": g.parametres} for g in proposition.gestes],
            "validee": False,
            "creee_le": datetime.now().isoformat(timespec="seconds"),
        }
        proposition.recette = identifiant
        self._sauvegarder_recettes()
        return proposition

    # --- Agir ---------------------------------------------------------------------------------------

    def peut_agir_seule(self, proposition: Proposition) -> bool:
        return all(self.confiance.autonome(g.primitive.nom) for g in proposition.gestes)

    def executer(self, proposition: Proposition, avec_accord: bool = True) -> str:
        """Réalise les gestes. avec_accord=True : tu viens de dire oui (la confiance grandit)."""
        textes, action = [], Action(proposition.decrire())
        reussi = True
        for geste in proposition.gestes:
            try:
                resultat = geste.primitive.fonction(self.contexte, **geste.parametres)
            except (OSError, TypeError, ValueError) as erreur:
                textes.append(f"Échec : {erreur}")
                reussi = False
                break
            textes.append(resultat.texte)
            if resultat.annulation:
                action.annulations.append(resultat.annulation)
            if not resultat.reussi:
                reussi = False
                break
            if avec_accord:
                self.confiance.accord(geste.primitive.nom)
        if reussi and self.quand_action:
            self.quand_action(proposition.demande)  # les yeux notent ce que tu fais faire, pour repérer les habitudes
        if action.annulations:
            self.historique = (self.historique + [action])[-MEMOIRE_ANNULATION:]
        if proposition.recette and proposition.recette in self.recettes and reussi:
            fiche = self.recettes[proposition.recette]
            if not fiche["validee"]:
                fiche["validee"] = True
                self.decideur.enseigner("recette", fiche["demande"], proposition.recette)
                self.decideur.enseigner("action sur l'ordinateur", fiche["demande"], "oui")
                self.decideur.sauvegarder()
                self._sauvegarder_recettes()
        return " ".join(textes)

    def refuser(self, proposition: Proposition) -> str:
        for geste in proposition.gestes:
            self.confiance.refus(geste.primitive.nom)
        if proposition.recette and not self.recettes.get(proposition.recette, {}).get("validee", True):
            del self.recettes[proposition.recette]  # une leçon refusée n'est pas gardée
            self._sauvegarder_recettes()
        return "D'accord, je ne fais rien. Je te redemanderai la prochaine fois."

    def annuler(self) -> str:
        if not self.historique:
            return "Rien à annuler."
        action = self.historique.pop()
        textes = [annulation() for annulation in reversed(action.annulations)]
        return f"Annulé : {action.description}. " + " ".join(textes)

    def _sauvegarder_recettes(self) -> None:
        self.dossier.mkdir(parents=True, exist_ok=True)
        temporaire = self.chemin_recettes.with_suffix(".tmp")
        temporaire.write_text(json.dumps(self.recettes, ensure_ascii=False, indent=2), encoding="utf-8")
        temporaire.replace(self.chemin_recettes)
