"""L'auto-extension : Janova se crée de nouveaux organes.

Quand aucune partie de Janova ne sait traiter une étape, elle demande à l'aide extérieure
d'écrire un **organe** pour ce genre d'étape : un petit programme qui marchera aussi avec
d'autres valeurs. Si l'IA juge que ce n'est pas possible, elle répond simplement à l'étape.

Un organe proposé n'est accepté que s'il :
1. passe la lecture de sécurité du bac à sable ;
2. réussit ses propres tests, exécutés dans le bac à sable ;
3. traite bien l'étape qui a déclenché sa création.
S'il échoue, on renvoie les erreurs à l'IA pour qu'elle corrige (2 essais de plus au maximum).

Les organes acceptés sont enregistrés dans donnees/organes_appris/ (un fichier JSON par organe),
et rechargés à chaque démarrage : Janova garde ce qu'elle a appris.

Ensuite, ils évoluent : chaque fausse alerte (organe réveillé pour une étape qui n'était pas pour lui)
est notée, et pendant le sommeil leurs mots-clés évoluent pour les éviter (voir evolution.py).
"""

import json
import re
import unicodedata
from pathlib import Path

from janova.aide_exterieure import AideExterieure
from janova.extension.bac_a_sable import MODULES_AUTORISES, executer, verifier_code
from janova.extension.evolution import evoluer
from janova.organes.base import Organe

ESSAIS_MAX = 3

QUESTION = """Tu aides Janova, une IA locale très économe en énergie. Elle n'a pas su traiter cette étape :
<<<{etape}>>>

Si un petit programme Python simple et déterministe peut traiter CE GENRE d'étape (aussi avec d'autres
valeurs ou d'autres mots), écris un organe. Sinon, réponds directement à l'étape.
Réponds UNIQUEMENT avec un objet JSON, de l'une de ces deux formes :

1) {{"organe": {{"nom": "...", "description": "...", "mots_cles": ["..."], "code": "...",
                "tests": [{{"etape": "...", "attendu": "..."}}]}}}}
   - "code" définit deux fonctions : def reconnait(etape) -> bool et def traiter(etape) -> str
   - Python standard uniquement ; seuls imports autorisés : {modules}
   - interdits : fichiers, réseau, eval, exec, getattr, type, noms ou attributs commençant par __
   - au moins 3 tests, avec des valeurs différentes ; "attendu" est EXACTEMENT ce que renvoie traiter
   - "mots_cles" : 1 à 5 mots en minuscules sans accents ; toute étape de ce genre en contient au moins un

2) {{"reponse": "ta réponse, courte"}}{erreurs}"""


def _sans_accents(texte: str) -> str:
    decompose = unicodedata.normalize("NFKD", texte.lower())
    return "".join(c for c in decompose if not unicodedata.combining(c))


def _extraire_json(texte: str) -> dict | None:
    """Récupère l'objet JSON d'une réponse d'IA, même entouré de texte. None s'il est illisible."""
    debut, fin = texte.find("{"), texte.rfind("}")
    if debut == -1 or fin == -1:
        return None
    try:
        donnees = json.loads(texte[debut : fin + 1])
    except ValueError:
        return None
    return donnees if isinstance(donnees, dict) else None


def fabriquer_organe(fiche: dict, delai_secondes: float = 5.0) -> type[Organe]:
    """Transforme la fiche d'un organe appris (nom, mots-clés, code…) en un vrai organe utilisable par le noyau."""

    class OrganeAppris(Organe):
        nom = fiche["nom"]
        description = fiche.get("description", "")
        cout = 3  # plus cher que les organes écrits à la main : il tourne dans le bac à sable
        besoin_gpu = False
        deterministe = True
        code = fiche["code"]
        mots_cles = [_sans_accents(mot) for mot in fiche["mots_cles"]]  # ils peuvent évoluer pendant le sommeil

        @classmethod
        def reconnait(cls, etape: str) -> bool:
            # Le coup d'œil : une simple recherche de mots-clés, sans lancer le bac à sable (règle 2).
            texte = _sans_accents(etape)
            return any(mot in texte for mot in cls.mots_cles)

        def traiter(self, etape: str) -> str | None:
            # Le vrai travail : dans le bac à sable, l'organe vérifie lui-même l'étape puis la traite.
            ok, reponse = executer(self.code, [etape], delai_secondes)[0]
            return reponse if ok and reponse.strip() else None

    # La fiche complète reste attachée à l'organe : elle sert à noter ses fausses alertes et à le faire évoluer.
    OrganeAppris.fiche = fiche
    return OrganeAppris


class CreateurOrganes:
    def __init__(
        self, aide: AideExterieure, dossier: Path, noms_reserves: set[str] = frozenset(), delai_secondes: float = 5.0
    ) -> None:
        self.aide = aide
        self.dossier = Path(dossier)
        self.noms_reserves = set(noms_reserves)  # noms déjà pris par les organes écrits à la main
        self.delai_secondes = delai_secondes
        self.dernieres_erreurs: list[str] = []  # pour comprendre un échec (affiché par le noyau)

    def charger_tous(self) -> list[type[Organe]]:
        """Recharge les organes appris lors des utilisations précédentes."""
        organes = []
        for fichier in sorted(self.dossier.glob("*.json")):
            try:
                fiche = json.loads(fichier.read_text(encoding="utf-8"))
            except ValueError:
                continue  # fichier abîmé : on l'ignore
            # On revérifie le code à chaque chargement : un fichier modifié à la main pourrait être dangereux.
            if not verifier_code(fiche.get("code", "")):
                organes.append(fabriquer_organe(fiche, self.delai_secondes))
        return organes

    def resoudre(self, etape: str) -> tuple[type[Organe] | None, str | None]:
        """Demande à l'aide extérieure de traiter l'étape.

        Renvoie (nouvel organe, réponse) si un organe a été créé, (None, réponse) si l'IA a répondu
        directement, et (None, None) si elle n'a rien pu faire.
        """
        self.dernieres_erreurs = []
        erreurs = ""
        for essai in range(1, ESSAIS_MAX + 1):
            texte = self.aide.demander(
                QUESTION.format(etape=etape, modules=", ".join(sorted(MODULES_AUTORISES)), erreurs=erreurs),
                en_json=True,
            )
            if texte is None:
                return None, None  # Ollama injoignable
            donnees = _extraire_json(texte)
            if donnees is None:
                erreurs = "\n\nTa réponse précédente n'était pas un JSON valide. Recommence."
                self.dernieres_erreurs.append(f"essai {essai} : JSON illisible")
                continue
            if "organe" not in donnees:
                reponse = str(donnees.get("reponse", "")).strip()
                return None, reponse or None

            # _verifier renvoie (fiche, réponse à l'étape) si l'organe est accepté, sinon (None, problème).
            fiche, detail = self._verifier(donnees["organe"], etape)
            if fiche is not None:
                return self._enregistrer(fiche), detail
            self.dernieres_erreurs.append(f"essai {essai} : {detail}")
            erreurs = f"\n\nTon organe précédent a été refusé :\n{detail}\nCorrige-le."
        return None, None

    def _verifier(self, organe: object, etape: str) -> tuple[dict | None, str]:
        """Vérifie un organe proposé. Renvoie (fiche, réponse à l'étape) s'il est accepté, sinon (None, problème)."""
        if not isinstance(organe, dict):
            return None, "« organe » doit être un objet JSON"
        try:
            fiche = {
                "nom": re.sub(r"[^a-z0-9_]+", "_", _sans_accents(str(organe["nom"]))).strip("_") or "organe",
                "description": str(organe.get("description", "")),
                "mots_cles": [str(mot) for mot in organe["mots_cles"]][:5],
                "code": str(organe["code"]),
                "tests": [(str(t["etape"]), str(t["attendu"])) for t in organe["tests"]],
            }
        except (KeyError, TypeError) as erreur:
            return None, f"il manque un champ : {erreur}"
        if not fiche["mots_cles"]:
            return None, "il faut au moins un mot-clé"
        if len(fiche["tests"]) < 3:
            return None, "il faut au moins 3 tests"
        problemes = verifier_code(fiche["code"])
        if problemes:
            return None, "code refusé : " + "; ".join(problemes)

        # Les tests et l'étape d'origine, tous exécutés d'un coup dans le bac à sable.
        resultats = executer(fiche["code"], [t[0] for t in fiche["tests"]] + [etape], self.delai_secondes)
        echecs = [
            f"- traiter({entree!r}) a donné {sortie!r} au lieu de {attendu!r}" if ok
            else f"- {entree!r} : {sortie}"
            for (entree, attendu), (ok, sortie) in zip(fiche["tests"], resultats)
            if not (ok and sortie.strip() == attendu.strip())
        ]
        ok_etape, reponse_etape = resultats[-1]
        if not ok_etape or not reponse_etape.strip():
            echecs.append(f"- l'étape d'origine {etape!r} : {reponse_etape}")
        organe_test = fabriquer_organe(fiche)
        if not organe_test.reconnait(etape):
            echecs.append(f"- aucun mot-clé {fiche['mots_cles']} n'apparaît dans l'étape d'origine")
        if echecs:
            return None, "\n".join(echecs)
        return fiche, reponse_etape

    def _enregistrer(self, fiche: dict) -> type[Organe]:
        """Enregistre l'organe accepté sur le disque, avec un nom unique, et le renvoie prêt à servir."""
        self.dossier.mkdir(parents=True, exist_ok=True)
        nom, numero = fiche["nom"], 2
        while fiche["nom"] in self.noms_reserves or (self.dossier / f"{fiche['nom']}.json").exists():
            fiche["nom"] = f"{nom}_{numero}"
            numero += 1
        fiche["tests"] = [{"etape": e, "attendu": a} for e, a in fiche["tests"]]
        fiche["generation"] = 1  # augmente à chaque évolution
        fiche["fausses_alertes"] = []
        self._sauvegarder(fiche)
        return fabriquer_organe(fiche, self.delai_secondes)

    def _sauvegarder(self, fiche: dict) -> None:
        chemin = self.dossier / f"{fiche['nom']}.json"
        chemin.write_text(json.dumps(fiche, ensure_ascii=False, indent=2), encoding="utf-8")

    # --- Évolution ----------------------------------------------------------------------------------

    def noter_fausse_alerte(self, organe: type[Organe], etape: str) -> None:
        """L'organe s'est réveillé pour une étape qui n'était pas pour lui : on le note (50 au maximum)."""
        alertes = organe.fiche.setdefault("fausses_alertes", [])
        if etape not in alertes:
            alertes.append(etape)
            del alertes[:-50]  # on ne garde que les 50 plus récentes
            self._sauvegarder(organe.fiche)

    def faire_evoluer(self, organe: type[Organe], etapes_reussies: list[str], graine: int) -> bool:
        """Fait évoluer les mots-clés de l'organe. Renvoie True s'il a changé."""
        positifs = [test["etape"] for test in organe.fiche["tests"]] + etapes_reussies
        nouveaux = evoluer(organe.mots_cles, positifs, organe.fiche.get("fausses_alertes", []), graine)
        if nouveaux is None:
            return False
        organe.mots_cles = nouveaux
        organe.fiche["mots_cles"] = nouveaux
        organe.fiche["generation"] = organe.fiche.get("generation", 1) + 1
        self._sauvegarder(organe.fiche)
        return True
