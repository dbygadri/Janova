"""L'organe social, construit avec de vrais neurones à impulsions.

Comment fonctionne un neurone biologique (modèle « intègre-et-tire avec fuite ») :
- il accumule les signaux qu'il reçoit, comme un seau qui se remplit ;
- le seau fuit un peu à chaque instant (sans signal, il se vide) ;
- quand le seau déborde (seuil atteint), le neurone envoie une **impulsion**.
S'il ne reçoit rien, il ne fait rien et ne consomme rien : c'est un grand secret d'économie du cerveau.

Notre petit réseau :
- **neurones d'entrée** : un par mot connu ; ils émettent une impulsion à chaque instant où leur mot est présent ;
- **neurones de sortie** : un par intention (salutation, remerciement…) ; le premier qui envoie une impulsion gagne ;
- **un neurone inhibiteur** : les mots inconnus le font parler, et il freine toutes les sorties. Ainsi
  « bonjour, calcule 2 + 2 » n'est pas pris pour une simple salutation ;
- **l'apprentissage** suit la règle de Hebb : « des neurones qui s'activent ensemble se connectent ».
  Plus un mot apparaît dans les exemples d'une intention, plus sa connexion vers elle est forte.

Économie : seuls les mots présents travaillent. Une phrase sans aucun mot connu ne coûte presque rien.
Ce réseau est volontairement petit et pédagogique : les vrais gains d'énergie des neurones à impulsions
viennent des puces spéciales (« neuromorphiques »). Simulé sur un processeur ordinaire, il montre le principe.
"""

import re
import unicodedata

from janova.organes.base import Organe

# --- Ce que le réseau apprend : des exemples de phrases pour chaque intention -------------------------

EXEMPLES = {
    "salutation": ["bonjour", "salut", "bonjour janova", "salut janova", "coucou", "bonsoir", "hello", "hey janova"],
    "etat": ["comment vas-tu", "comment ça va", "ça va", "tu vas bien", "comment tu vas", "la forme"],
    "remerciement": ["merci", "merci beaucoup", "merci janova", "je te remercie", "super merci", "génial merci"],
    "compliment": ["tu es génial", "tu es super", "bravo", "bien joué", "tu es forte", "excellent travail"],
    "au_revoir": ["au revoir", "à bientôt", "bonne nuit", "à plus tard", "à demain", "bye"],
    "identite": ["qui es-tu", "tu es qui", "comment tu t'appelles", "présente-toi", "quel est ton nom", "c'est quoi janova"],
}

REPONSES = {
    "salutation": "Bonjour ! Je suis Janova. Que puis-je faire pour toi ?",
    "etat": "Je vais bien, merci ! Mes réserves d'énergie sont au vert.",
    "remerciement": "Avec plaisir !",
    "compliment": "Merci, ça me fait plaisir ! Je continue d'apprendre.",
    "au_revoir": "À bientôt !",
    "identite": "Je suis Janova, une IA locale inspirée du corps humain : peu d'énergie, beaucoup de puissance.",
}

# --- Les réglages des neurones ---------------------------------------------------------------------

INSTANTS = 8  # durée de la simulation, en « instants »
FUITE = 0.8  # à chaque instant, le seau garde 80 % de son contenu (il en perd 20 %)
SEUIL = 1.5  # niveau à partir duquel le neurone envoie une impulsion
POIDS_INHIBITION = 1.2  # force du frein, pour chaque mot inconnu


def mots(phrase: str) -> list[str]:
    """Les mots d'une phrase, en minuscules et sans accents (les mots d'une seule lettre sont ignorés)."""
    decompose = unicodedata.normalize("NFKD", phrase.lower())
    sans_accents = "".join(c for c in decompose if not unicodedata.combining(c))
    return [mot for mot in re.findall(r"[a-z]+", sans_accents) if len(mot) >= 2]


class ReseauImpulsions:
    def __init__(self, exemples: dict[str, list[str]]) -> None:
        self.intentions = list(exemples)
        # Les connexions : poids[mot][intention]. On les apprend avec la règle de Hebb :
        # chaque fois qu'un mot et une intention apparaissent ensemble, leur connexion se renforce.
        comptes: dict[str, dict[str, float]] = {}
        for intention, phrases in exemples.items():
            for phrase in phrases:
                liste = mots(phrase)
                for mot in liste:
                    # Dans une phrase courte, chaque mot compte davantage.
                    comptes.setdefault(mot, {}).setdefault(intention, 0.0)
                    comptes[mot][intention] += 1 / len(liste)
        # Un mot présent dans plusieurs intentions (« janova ») se partage : il distingue moins.
        self.poids = {}
        for mot, par_intention in comptes.items():
            total = sum(par_intention.values())
            plus_fort = max(par_intention.values())
            self.poids[mot] = {i: (v / total) * min(1.0, plus_fort * 2) for i, v in par_intention.items()}
        self.impulsions = 0  # compteur d'impulsions envoyées : l'« activité » du réseau

    def reconnaitre(self, phrase: str) -> str | None:
        """Simule le réseau. Renvoie l'intention dont le neurone a tiré en premier, ou None (silence)."""
        liste = mots(phrase)
        connus = [mot for mot in liste if mot in self.poids]
        if not connus:
            return None  # aucun neurone d'entrée ne s'active : le réseau reste silencieux, presque gratuit
        inconnus = len(liste) - len(connus)

        # Le courant reçu par chaque neurone de sortie, à chaque instant :
        # la somme des connexions des mots connus, moins le frein des mots inconnus.
        courant = {intention: -POIDS_INHIBITION * inconnus for intention in self.intentions}
        for mot in connus:
            for intention, poids in self.poids[mot].items():
                courant[intention] += poids

        potentiel = {intention: 0.0 for intention in self.intentions}  # le niveau de chaque seau
        for _ in range(INSTANTS):
            self.impulsions += len(connus) + (1 if inconnus else 0)  # les entrées tirent à chaque instant
            for intention in self.intentions:
                potentiel[intention] = potentiel[intention] * FUITE + courant[intention]
            gagnants = [i for i in self.intentions if potentiel[i] >= SEUIL]
            if gagnants:
                self.impulsions += 1
                # Si plusieurs débordent au même instant, le plus rempli gagne.
                return max(gagnants, key=lambda intention: potentiel[intention])
        return None  # personne n'a débordé : le réseau ne sait pas répondre


_reseau: ReseauImpulsions | None = None


def reseau() -> ReseauImpulsions:
    """Le réseau n'est construit qu'au premier besoin, puis réutilisé (règle 2 : n'allumer que ce qui sert)."""
    global _reseau
    if _reseau is None:
        _reseau = ReseauImpulsions(EXEMPLES)
    return _reseau


class OrganeSocial(Organe):
    nom = "social"
    cout = 1
    deterministe = True

    @classmethod
    def reconnait(cls, etape: str) -> bool:
        return reseau().reconnaitre(etape) is not None

    def traiter(self, etape: str) -> str | None:
        intention = reseau().reconnaitre(etape)
        return REPONSES.get(intention) if intention else None
