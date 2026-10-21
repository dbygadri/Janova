"""Le carnet d'idées : Janova range tes idées toute seule, dans un graphe façon Obsidian.

Chaque idée devient une note Markdown dans « donnees/idees/ ». Ce dossier s'ouvre tel quel dans Obsidian :
les liens [[…]] entre idées proches dessinent un graphe de connaissances.

Pour chaque idée, les réflexes de décision (decision.py, inspirés de Jev) répondent à trois questions :
- **catégorie** : à quel projet ou thème elle appartient (alkestore, janova, immobilier…) ;
- **importance** : basse, moyenne ou haute ;
- **action** : à faire, à creuser ou à archiver.

L'échelle d'escalade, du moins cher au plus cher :
1. **toi** : si tu écris « alkestore : ajouter le paiement mobile », la catégorie est donnée, et Janova apprend ;
2. **réflexe** : la décision rapide, si elle est sûre d'elle (confiance au-dessus du seuil) ;
3. **professeur** : sinon, l'aide extérieure (un modèle d'IA local) choisit la catégorie… et Janova retient sa leçon :
   la prochaine idée du même genre sera rangée par réflexe, sans professeur (c'est la distillation) ;
4. **à trier** : sans professeur, l'idée attend que tu la classes avec « /classer ». Ta correction est aussi une leçon.
"""

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from janova.decision import Decideur, mots

A_TRIER = "à trier"
SEUIL_LIEN = 0.25  # deux idées qui partagent au moins 25 % de leurs mots sont reliées dans le graphe

IMPORTANCE = ["basse", "moyenne", "haute"]
ACTIONS = ["à faire", "à creuser", "à archiver"]

# Les premiers exemples, pour que les décisions marchent dès le premier jour. Tes corrections les complètent.
EXEMPLES_DE_DEPART = {
    "importance": {
        "haute": "urgent important vite absolument priorité crucial essentiel indispensable aujourd'hui demain",
        "moyenne": "améliorer bien serait utile ajouter prévoir penser semaine mois",
        "basse": "peut-être un jour éventuellement plus tard pourquoi pas rêve idée lointaine",
    },
    "action": {
        "à faire": "faire acheter appeler envoyer créer installer réserver payer écrire réparer contacter",
        "à creuser": "et si pourrait rechercher comprendre explorer étudier tester imaginer concept question",
        "à archiver": "noté info souvenir citation lu vu appris remarque fait savoir",
    },
}


def nettoyer_categorie(texte: str) -> str:
    """Une catégorie propre : minuscules, lettres, chiffres, espaces et tirets, 40 caractères au plus."""
    texte = re.sub(r"[^a-zà-ÿœæ0-9 \-]", "", texte.lower())
    return " ".join(texte.split())[:40].strip()


@dataclass
class IdeeRangee:
    """Ce que Janova a fait d'une idée."""

    numero: int
    texte: str
    categorie: str
    rangee_par: str  # « toi », « réflexe », « professeur » ou « aucun »
    confiance: float
    importance: str
    action: str
    liens: list[int]
    temps: float = 0.0  # électricité dépensée, en µs (rempli par le noyau)

    def texte_affiche(self) -> str:
        liens = f", reliée aux idées {', '.join(f'n°{n}' for n in self.liens)}" if self.liens else ""
        if self.categorie == A_TRIER:
            rangement = "à trier : je ne suis pas sûre de la catégorie. Classe-la avec /classer"
        else:
            rangement = f"rangée dans « {self.categorie} » [{self.rangee_par}, {self.confiance:.0%}]"
        return (f"Idée n°{self.numero} {rangement}\n"
                f"  importance {self.importance}, action « {self.action} »{liens}   [{self.temps:.0f} µs]")


class CarnetIdees:
    def __init__(self, dossier: Path, decideur: Decideur, aide=None) -> None:
        self.dossier = Path(dossier)
        self.decideur = decideur
        self.aide = aide  # le professeur (aide extérieure), ou None
        self.chemin_index = self.dossier / "index.json"
        self.idees: list[dict] = []
        if self.chemin_index.exists():
            try:
                self.idees = json.loads(self.chemin_index.read_text(encoding="utf-8"))
            except ValueError:
                self.chemin_index.replace(self.chemin_index.with_suffix(".abime"))
        for question, exemples in EXEMPLES_DE_DEPART.items():
            if not self.decideur.options(question):
                for option, texte in exemples.items():
                    self.decideur.enseigner(question, texte, option)

    # --- Ranger une idée ------------------------------------------------------------------------------

    def ranger(self, saisie: str, aide_permise: bool = True) -> IdeeRangee:
        """Range une idée. « alkestore : ajouter le paiement » donne directement la catégorie « alkestore »."""
        categorie, texte = self._categorie_donnee(saisie)
        if categorie:
            rangee_par, confiance = "toi", 1.0
        else:
            categorie, rangee_par, confiance = self._deviner_categorie(texte, aide_permise)
        if categorie != A_TRIER:
            self.decideur.enseigner("categorie", texte, categorie)  # chaque idée rangée enrichit les réflexes

        importance = self.decideur.noter("importance", texte, IMPORTANCE)
        action = self.decideur.choisir("action", texte, ACTIONS)
        numero = max((i["numero"] for i in self.idees), default=0) + 1
        liens = self._idees_proches(texte)
        idee = {
            "numero": numero,
            "texte": texte,
            "categorie": categorie,
            "rangee_par": rangee_par,
            "confiance": round(confiance, 3),
            "importance": importance.choix,
            "action": action.choix,
            "liens": liens,
            "date": datetime.now().isoformat(timespec="seconds"),
        }
        self.idees.append(idee)
        self._ecrire_note(idee)
        for autre in liens:  # le lien va dans les deux sens : on réécrit aussi les notes reliées
            fiche = self._fiche(autre)
            if numero not in fiche["liens"]:
                fiche["liens"].append(numero)
                self._ecrire_note(fiche)
        self.sauvegarder()
        return IdeeRangee(numero, texte, categorie, rangee_par, confiance, importance.choix, action.choix, liens)

    def _categorie_donnee(self, saisie: str) -> tuple[str, str]:
        """« alkestore : ajouter le paiement » → (« alkestore », « ajouter le paiement »)."""
        avant, deux_points, apres = saisie.partition(":")
        categorie = nettoyer_categorie(avant)
        if deux_points and apres.strip() and categorie and len(avant.split()) <= 3:
            return categorie, apres.strip()
        return "", saisie.strip()

    def _deviner_categorie(self, texte: str, aide_permise: bool) -> tuple[str, str, float]:
        """Réflexe d'abord ; s'il n'est pas sûr, le professeur ; sinon, « à trier »."""
        decision = self.decideur.choisir("categorie", texte)
        # Une idée sans aucun mot déjà vu serait rangée « au hasard » dans la catégorie la plus fréquente :
        # on exige donc au moins un mot connu avant de faire confiance au réflexe.
        if decision and decision.sure and self._mots_connus(texte):
            return decision.choix, "réflexe", decision.confiance
        if self.aide is not None and aide_permise:
            categorie = self._demander_au_professeur(texte)
            if categorie:
                return categorie, "professeur", 1.0
        return A_TRIER, "aucun", decision.confiance if decision else 0.0

    def _mots_connus(self, texte: str) -> bool:
        connus = {m for fiche in self.decideur.connaissances.get("categorie", {}).values() for m in fiche["mots"]}
        return any(m in connus for m in mots(texte))

    def _demander_au_professeur(self, texte: str) -> str:
        existantes = self.decideur.options("categorie")
        question = (
            "Range cette idée dans une catégorie courte (1 à 3 mots, en minuscules), comme un nom de projet "
            "ou de thème. "
            + (f"Catégories existantes : {', '.join(existantes)}. Réutilise-en une si elle convient. " if existantes else "")
            + 'Réponds seulement en JSON : {"categorie": "..."}\nIdée : ' + texte
        )
        reponse = self.aide.demander(question, en_json=True)
        if not reponse:
            return ""
        try:
            categorie = json.loads(reponse).get("categorie", "")
        except (ValueError, AttributeError):
            return ""
        return nettoyer_categorie(str(categorie))

    def _idees_proches(self, texte: str) -> list[int]:
        """Les idées qui partagent assez de mots avec celle-ci (indice de Jaccard)."""
        les_miens = set(mots(texte))
        proches = []
        for idee in self.idees:
            les_siens = set(mots(idee["texte"]))
            if les_miens and les_siens and len(les_miens & les_siens) / len(les_miens | les_siens) >= SEUIL_LIEN:
                proches.append(idee["numero"])
        return proches

    # --- Corriger, lister -----------------------------------------------------------------------------

    def classer(self, numero: int, categorie: str) -> str:
        """Tu corriges la catégorie d'une idée : Janova range l'idée et retient la leçon."""
        fiche = self._fiche(numero)
        categorie = nettoyer_categorie(categorie)
        if fiche is None:
            return f"Je ne trouve pas l'idée n°{numero}."
        if not categorie:
            return "Donne une catégorie, par exemple : /classer 3 alkestore"
        fiche.update(categorie=categorie, rangee_par="toi", confiance=1.0)
        self.decideur.enseigner("categorie", fiche["texte"], categorie, poids=2)  # une correction compte double
        self._ecrire_note(fiche)
        self.sauvegarder()
        return f"Idée n°{numero} rangée dans « {categorie} ». Leçon retenue pour les prochaines."

    def lister(self) -> str:
        """Toutes les idées, groupées par catégorie, les plus importantes d'abord."""
        if not self.idees:
            return "Aucune idée pour l'instant. Écris par exemple : /idee alkestore : ajouter le paiement mobile"
        lignes = []
        for categorie in sorted({i["categorie"] for i in self.idees}, key=lambda c: (c == A_TRIER, c)):
            lignes.append(f"{categorie} :")
            groupe = [i for i in self.idees if i["categorie"] == categorie]
            for idee in sorted(groupe, key=lambda i: -IMPORTANCE.index(i["importance"])):
                lignes.append(f"  n°{idee['numero']} {idee['texte']}   [{idee['importance']}, {idee['action']}]")
        lignes.append(f"Les notes sont dans {self.dossier} (ouvrable dans Obsidian).")
        return "\n".join(lignes)

    def _fiche(self, numero: int) -> dict | None:
        return next((i for i in self.idees if i["numero"] == numero), None)

    # --- Garder sur le disque -------------------------------------------------------------------------

    def _nom_note(self, idee: dict) -> str:
        debut = "-".join(mots(idee["texte"])[:5]) or "idee"
        return f"{idee['numero']:04d}-{debut[:50]}"

    def _ecrire_note(self, idee: dict) -> None:
        """La note Markdown d'une idée, avec ses liens [[…]] vers les idées proches (le graphe d'Obsidian)."""
        self.dossier.mkdir(parents=True, exist_ok=True)
        for ancienne in self.dossier.glob(f"{idee['numero']:04d}-*.md"):
            ancienne.unlink()  # le nom peut changer si le texte change : on retire l'ancienne version
        liens = [self._nom_note(f) for n in idee["liens"] if (f := self._fiche(n))]
        contenu = (
            f"---\ncategorie: {idee['categorie']}\nimportance: {idee['importance']}\naction: {idee['action']}\n"
            f"rangee_par: {idee['rangee_par']}\ndate: {idee['date']}\n---\n\n# {idee['texte']}\n\n"
            f"Catégorie : [[{idee['categorie']}]]\n"
        )
        if liens:
            contenu += "\nIdées proches : " + ", ".join(f"[[{nom}]]" for nom in liens) + "\n"
        (self.dossier / f"{self._nom_note(idee)}.md").write_text(contenu, encoding="utf-8")

    def sauvegarder(self) -> None:
        self.dossier.mkdir(parents=True, exist_ok=True)
        temporaire = self.chemin_index.with_suffix(".tmp")
        temporaire.write_text(json.dumps(self.idees, ensure_ascii=False, indent=2), encoding="utf-8")
        temporaire.replace(self.chemin_index)
        self.decideur.sauvegarder()

    def __len__(self) -> int:
        return len(self.idees)
