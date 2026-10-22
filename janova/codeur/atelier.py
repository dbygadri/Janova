"""L'atelier : Janova code des applications, les teste, se corrige et les installe dans ton menu.

Quand tu demandes « crée-moi une calculatrice » ou « fais-moi un programme qui convertit des euros en dollars » :

1. **Déjà faite ?** Si une application de ce genre existe déjà, Janova te le dit au lieu de la refaire.
2. **Réflexe** : pour ce qu'elle sait déjà coder (modeles.py : calculatrice, minuteur, bloc-notes),
   pas besoin de professeur.
3. **Professeur** : sinon, l'aide extérieure (un modèle d'IA local spécialisé en code) écrit le programme.
4. **Contrôle qualité** (verification.py) : lecture de sécurité, puis essai réel de la fonction tester().
5. **Auto-correction** : si l'essai échoue, Janova renvoie l'erreur au professeur, qui corrige.
   Jusqu'à 4 essais au total.
6. **Installation** : le programme va dans ~/Applications-Janova/<nom>/, et une entrée apparaît dans
   le menu des applications. Tu l'ouvres comme n'importe quelle appli, ou en disant « ouvre <nom> ».

Tu peux ensuite la faire évoluer : « modifie calculatrice : ajoute une touche racine carrée ».
L'ancienne version est gardée : /annuler la remet.

Chaque application réussie rejoint la bibliothèque de Janova : c'est un savoir-faire qu'elle garde.
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path

from janova.codeur.modeles import MODELES
from janova.codeur.verification import GESTES_INTERDITS, MODULES_APPLICATION, essayer
from janova.extension.createur import _extraire_json
from janova.mains.primitives import Resultat, sans_accents

ESSAIS_MAX = 4
DOSSIER_APPLICATIONS = "Applications-Janova"

REGLES = f"""Règles :
- un seul fichier Python 3, standard ; modules permis : {", ".join(sorted(MODULES_APPLICATION))}
- interdits : os, sys, subprocess, socket, shutil, réseau, eval, exec, getattr, noms commençant par __
  (sauf __name__), et ces méthodes : {", ".join(sorted(GESTES_INTERDITS))}
- la logique dans des fonctions simples, testables sans fenêtre
- def main() lance l'application ; si elle a une fenêtre, fais « import tkinter as tk » DANS main(), pas en haut
- def tester() vérifie la logique avec au moins 3 assert, SANS ouvrir de fenêtre ni attendre de saisie
- termine par : if __name__ == "__main__": main()
- textes affichés en français, interface simple et claire
Réponds UNIQUEMENT en JSON : {{"nom": "Nom court", "description": "une phrase", "fenetre": true, "code": "..."}}
("fenetre": false si c'est un programme pour le terminal)"""

QUESTION_CREER = """Tu es le professeur de Janova, une IA locale qui apprend à coder. Écris une petite application pour Linux.
Demande : <<<{demande}>>>
{regles}{erreurs}"""

QUESTION_MODIFIER = """Tu es le professeur de Janova, une IA locale qui apprend à coder. Modifie cette application.
Code actuel :
<<<
{code}
>>>
Modification demandée : <<<{demande}>>>
Renvoie le fichier COMPLET modifié, en gardant ce qui marche déjà.
{regles}{erreurs}"""


def identifiant(nom: str) -> str:
    """« Bloc-notes rapide » → « bloc-notes-rapide » : un nom de dossier sans accents ni espaces."""
    return re.sub(r"[^a-z0-9]+", "-", sans_accents(nom)).strip("-")[:40] or "application"


class Atelier:
    def __init__(self, dossier: Path, aide=None, aide_code=None) -> None:
        self.dossier = Path(dossier)
        self.aide = aide  # le professeur général
        self.aide_code = aide_code  # un professeur spécialisé en code, s'il est installé (essayé en premier)
        self.chemin = self.dossier / "bibliotheque.json"
        self.bibliotheque: dict[str, dict] = {}
        if self.chemin.exists():
            try:
                self.bibliotheque = json.loads(self.chemin.read_text(encoding="utf-8"))
            except ValueError:
                self.chemin.replace(self.chemin.with_suffix(".abime"))

    # --- Créer ---------------------------------------------------------------------------------------

    def creer(self, maison: Path, demande: str) -> Resultat:
        existante = self.trouver(demande)
        if existante:
            fiche = self.bibliotheque[existante]
            return Resultat(f"J'ai déjà codé « {fiche['nom']} ». Dis « ouvre {fiche['nom'].lower()} », "
                            f"ou « modifie {fiche['nom'].lower()} : … » pour la changer.")
        modele = self._modele(demande)
        if modele:
            fiche, origine, essais = dict(MODELES[modele]), "réflexe", 1
            probleme = essayer(fiche["code"])
        else:
            fiche, probleme, essais = self._faire_coder(QUESTION_CREER, demande=demande)
            origine = "professeur"
        if fiche is None:
            return Resultat(probleme, False)
        if probleme:
            return Resultat(f"Je n'ai pas réussi à coder une application qui marche ({essais} essai(s)). "
                            f"Dernier problème : {probleme[:300]}", False)
        return self._installer(maison, demande, fiche, origine, essais)

    def _modele(self, demande: str) -> str | None:
        simple = sans_accents(demande)
        return next((cle for cle, m in MODELES.items() if any(mot in simple for mot in m["mots_cles"])), None)

    def trouver(self, texte: str) -> str | None:
        """L'application de la bibliothèque dont le nom apparaît dans le texte (« ouvre ma calculatrice »)."""
        simple = sans_accents(texte)
        for cle, fiche in sorted(self.bibliotheque.items(), key=lambda paire: -len(paire[1]["nom"])):
            if sans_accents(fiche["nom"]) in simple or cle in simple.replace(" ", "-"):
                return cle
        modele = self._modele(texte)  # « crée une calculette » retrouve la « Calculatrice » déjà faite
        return modele if modele in self.bibliotheque else None

    def _faire_coder(self, question: str, **valeurs) -> tuple[dict | None, str | None, int]:
        """Demande le code au professeur, l'essaie, et lui renvoie les erreurs jusqu'à ce que ça marche."""
        professeurs = [p for p in (self.aide_code, self.aide) if p is not None]
        if not professeurs:
            return None, ("Je ne sais pas encore coder ça toute seule, et je n'ai pas de professeur. "
                          "Installe Ollama (voir le README) pour que je puisse apprendre."), 0
        erreurs, derniere, probleme = "", None, None
        for essai in range(1, ESSAIS_MAX + 1):
            reponse = None
            for professeur in professeurs:  # le professeur spécialisé d'abord ; s'il est absent, le général
                reponse = professeur.demander(question.format(regles=REGLES, erreurs=erreurs, **valeurs), en_json=True)
                if reponse:
                    break
            if not reponse:
                return None, "Mon professeur ne répond pas (Ollama est-il lancé ?).", essai
            fiche = _extraire_json(reponse)
            if not fiche or not isinstance(fiche.get("code"), str) or not fiche.get("nom"):
                probleme = "réponse illisible : il faut un objet JSON avec nom, description, fenetre et code"
            else:
                derniere = fiche
                probleme = essayer(fiche["code"])
                if probleme is None:
                    return fiche, None, essai
            erreurs = f"\n\nTon essai précédent ne marche pas. Problème à corriger :\n{probleme[:900]}"
        return derniere, probleme, ESSAIS_MAX

    # --- Modifier ------------------------------------------------------------------------------------

    def modifier(self, maison: Path, nom: str, demande: str) -> Resultat:
        cle = self.trouver(nom)
        if cle is None:
            return Resultat(f"Je ne connais pas d'application « {nom} ». Celles que j'ai codées : "
                            f"{', '.join(f['nom'] for f in self.bibliotheque.values()) or 'aucune'}.", False)
        fiche = self.bibliotheque[cle]
        fichier = Path(fiche["dossier"]) / "application.py"
        ancien_code = fichier.read_text(encoding="utf-8")
        nouvelle, probleme, essais = self._faire_coder(QUESTION_MODIFIER, code=ancien_code, demande=demande)
        if nouvelle is None:
            return Resultat(probleme, False)
        if probleme:
            return Resultat(f"Je n'ai pas réussi à modifier « {fiche['nom']} » ({essais} essai(s)). "
                            f"L'ancienne version est intacte. Dernier problème : {probleme[:300]}", False)
        sauvegarde = fichier.with_name(f"application.v{fiche['version']}.py")
        sauvegarde.write_text(ancien_code, encoding="utf-8")
        fichier.write_text(nouvelle["code"], encoding="utf-8")
        ancienne_version = fiche["version"]
        fiche["version"] += 1
        fiche["historique"].append({"demande": demande, "le": datetime.now().isoformat(timespec="seconds")})
        self._sauvegarder()

        def annuler() -> str:
            fichier.write_text(sauvegarde.read_text(encoding="utf-8"), encoding="utf-8")
            fiche["version"] = ancienne_version
            fiche["historique"].pop()
            self._sauvegarder()
            return f"« {fiche['nom']} » est revenue à la version {ancienne_version}."
        return Resultat(f"« {fiche['nom']} » modifiée et testée (version {fiche['version']}, {essais} essai(s)). "
                        f"Ouvre-la pour voir le changement.", True, annuler)

    # --- Installer -----------------------------------------------------------------------------------

    def _installer(self, maison: Path, demande: str, fiche: dict, origine: str, essais: int) -> Resultat:
        cle = identifiant(fiche["nom"])
        while cle in self.bibliotheque:
            cle = f"{cle}-2" if not cle[-1].isdigit() else f"{cle[:-1]}{int(cle[-1]) + 1}"
        dossier = Path(maison) / DOSSIER_APPLICATIONS / cle
        dossier.mkdir(parents=True, exist_ok=True)
        (dossier / "application.py").write_text(fiche["code"], encoding="utf-8")
        lanceur = Path(maison) / ".local" / "share" / "applications" / f"janova-{cle}.desktop"
        lanceur.parent.mkdir(parents=True, exist_ok=True)
        lanceur.write_text(
            "[Desktop Entry]\nType=Application\n"
            f"Name={fiche['nom']}\nComment={fiche.get('description', '')} (codée par Janova)\n"
            f'Exec={sys.executable} "{dossier / "application.py"}"\n'
            f"Path={dossier}\nIcon=applications-utilities\n"
            f"Terminal={'false' if fiche.get('fenetre', True) else 'true'}\nCategories=Utility;\n",
            encoding="utf-8",
        )
        self.bibliotheque[cle] = {
            "nom": fiche["nom"], "description": fiche.get("description", ""), "demande": demande,
            "fenetre": bool(fiche.get("fenetre", True)), "origine": origine, "version": 1,
            "dossier": str(dossier), "lanceur": str(lanceur),
            "creee_le": datetime.now().isoformat(timespec="seconds"), "historique": [],
        }
        self._sauvegarder()

        def annuler() -> str:
            # On ne retire que ce que Janova vient de créer elle-même.
            for fichier in sorted(dossier.rglob("*"), reverse=True):
                fichier.unlink() if fichier.is_file() else fichier.rmdir()
            dossier.rmdir()
            lanceur.unlink(missing_ok=True)
            self.bibliotheque.pop(cle, None)
            self._sauvegarder()
            return f"« {fiche['nom']} » retirée."

        comment = "de mémoire, sans professeur" if origine == "réflexe" else f"avec mon professeur, {essais} essai(s)"
        return Resultat(f"J'ai codé et testé « {fiche['nom']} » ({comment}). Elle est dans ton menu des "
                        f"applications ; dis « ouvre {fiche['nom'].lower()} » pour la lancer.", True, annuler)

    def lister(self) -> str:
        if not self.bibliotheque:
            return "Je n'ai encore codé aucune application. Exemple : crée-moi une calculatrice"
        lignes = [f"  - {f['nom']} (version {f['version']}, {f['origine']}) : {f['description']}"
                  for f in self.bibliotheque.values()]
        return "Applications que j'ai codées :\n" + "\n".join(lignes)

    def _sauvegarder(self) -> None:
        self.dossier.mkdir(parents=True, exist_ok=True)
        temporaire = self.chemin.with_suffix(".tmp")
        temporaire.write_text(json.dumps(self.bibliotheque, ensure_ascii=False, indent=2), encoding="utf-8")
        temporaire.replace(self.chemin)
