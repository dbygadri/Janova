"""Le modèle commun à tous les organes de Janova.

Un organe est un spécialiste : il sait faire une seule sorte de chose, et la fait bien.

Règle 2 (« n'allumer que ce qui sert ») : un organe a deux états.
- **Endormi** : seule sa classe existe. On peut lui demander s'il reconnaît une étape
  (méthode `reconnait`), ce qui ne coûte presque rien.
- **Réveillé** : on a créé l'organe (son `__init__` s'est exécuté). Plus tard, c'est là qu'un
  organe lourd chargera ses données ou son modèle. Il ne se réveille que si on lui confie du travail.
"""


class Organe:
    # --- Ce que chaque organe doit déclarer -------------------------------------------------------

    nom = "organe"  # le nom affiché à l'utilisateur
    # Coût annoncé : plus il est petit, plus l'organe est économe (règle 1). Il résume toutes les
    # ressources : électricité (temps de calcul), mémoire, stockage.
    cout = 1
    # Besoin de la carte graphique ? Les organes qui en ont besoin passent toujours en dernier,
    # même si leur coût annoncé est plus petit : Janova cherche à s'en passer.
    besoin_gpu = False
    deterministe = True  # même question → toujours même réponse ? Si oui, on peut en faire un réflexe (règle 3)

    # --- Ce que chaque organe doit savoir faire ---------------------------------------------------

    @classmethod
    def reconnait(cls, etape: str) -> bool:
        """Répond True si l'organe sait traiter cette étape.

        C'est une « méthode de classe » : elle s'appelle sur l'organe endormi, sans le réveiller.
        Elle doit donc rester très rapide.
        """
        raise NotImplementedError

    def traiter(self, etape: str) -> str | None:
        """Traite l'étape et renvoie la réponse en texte, ou None en cas d'échec."""
        raise NotImplementedError
