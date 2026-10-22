"""La conversation : tout ce que tu écris à Janova passe par ici, dans le terminal comme dans la fenêtre du bureau.

Elle reconnaît :
- les commandes (/bilan, /idee, /routines…) ;
- tes réponses « oui » / « non » aux propositions de Janova ;
- les routines (« tous les matins, change mon thème ») ;
- et tout le reste, qui devient une tâche pour le noyau.
"""

from janova.mains.primitives import sans_accents
from janova.noyau import Janova

AIDE = """Parle-moi normalement, par exemple :
  range mes téléchargements           mets le thème sombre
  change le fond d'écran              ouvre firefox
  tous les matins, change mon thème   calcule 12 * (3 + 4)
Quand je propose une action, réponds oui ou non.
Commandes :
  /annuler     défaire ma dernière action sur l'ordinateur
  /confiance   ce que je fais seule et ce pour quoi je te demande encore
  /routines    tes routines   (/routine-supprimer 2 pour en retirer une)
  /yeux oui    me laisser remarquer tes habitudes (/yeux non pour arrêter)
  /idee        ranger une idée, ex. : /idee alkestore : ajouter le paiement mobile
  /idees       toutes tes idées      /classer 3 alkestore   corriger une catégorie
  /croissance  mon stade de vie et mon autonomie
  /bilan       toutes les ressources dépensées      /etat   mes signes vitaux
  /organes     mes organes      /reflexes   mes réflexes      /dormir   sommeil
  /aide        cette aide       /quitter    fermer Janova"""

OUI = {"oui", "ok", "d'accord", "dac", "vas-y", "vas y", "go", "yes", "ouais", "volontiers", "/oui"}
NON = {"non", "no", "nan", "annule", "stop", "pas maintenant", "/non"}


class Conversation:
    def __init__(self, janova: Janova | None = None) -> None:
        self.janova = janova or Janova()

    def recevoir(self, saisie: str) -> str:
        """Répond à ce que tu as écrit."""
        saisie = saisie.strip()
        if not saisie:
            return ""
        j = self.janova
        simple = sans_accents(saisie).strip(" !.")
        if j.en_attente and (simple in OUI or simple in NON):
            return j.valider(simple in OUI)
        if saisie.startswith("/"):
            return self._commande(saisie)
        routine = j.creer_routine(saisie)
        if routine is not None:
            return routine
        return j.traiter(saisie).texte()

    def _commande(self, saisie: str) -> str:
        j = self.janova
        commande, _, reste = saisie.partition(" ")
        reste = reste.strip()
        if commande == "/aide":
            return AIDE
        if commande == "/bilan":
            return j.bilan()
        if commande == "/etat":
            return j.etat()
        if commande == "/organes":
            return j.organes()
        if commande == "/reflexes":
            return f"{len(j.reflexes)} réflexe(s) appris."
        if commande == "/dormir":
            return j.dormir()
        if commande == "/annuler":
            return j.mains.annuler()
        if commande == "/confiance":
            return j.mains.confiance.resume()
        if commande == "/routines":
            return j.routines.lister()
        if commande == "/routine-supprimer":
            return j.routines.supprimer(int(reste)) if reste.isdigit() else "Exemple : /routine-supprimer 2"
        if commande == "/yeux":
            if reste in ("oui", "non"):
                return j.yeux.ouvrir(reste == "oui")
            return f"Mes yeux sont {'ouverts' if j.yeux.actifs else 'fermés'}. /yeux oui ou /yeux non."
        if commande == "/idee":
            return j.ranger_idee(reste).texte_affiche() if reste else "Exemple : /idee alkestore : paiement mobile"
        if commande == "/idees":
            return j.idees.lister()
        if commande == "/classer":
            numero, _, categorie = reste.partition(" ")
            if numero.isdigit() and categorie.strip():
                return j.idees.classer(int(numero), categorie)
            return "Exemple : /classer 3 alkestore"
        if commande == "/croissance":
            return j.etat_croissance()
        return f"Commande inconnue : {commande}. Tape /aide pour la liste."

    def vivre(self) -> list[str]:
        """À appeler régulièrement : routines, observation, propositions d'habitudes."""
        return self.janova.vivre()

    def fermer(self) -> str:
        return self.janova.dormir()
