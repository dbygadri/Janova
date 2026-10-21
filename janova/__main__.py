"""Démonstration de Janova, lancée avec : python -m janova

On tape une tâche, Janova la découpe en étapes, confie chaque étape à la partie la plus économe
capable de la traiter, et affiche ce que ça a coûté.
"""

from janova.noyau import Janova

AIDE = """Tape une tâche, par exemple :
  calcule 12 * (3 + 4), puis mets en majuscules : bonjour
  calcule 2 + 3, puis multiplie le résultat par 4
  bonjour, comment vas-tu ?
Commandes :
  /bilan     toutes les ressources dépensées (électricité, mémoire, carte graphique, stockage)
  /etat      signes vitaux (batterie, mémoire, température) et mode choisi
  /reflexes  nombre de réflexes appris
  /organes   la liste des organes (de base et appris) et l'état de l'aide extérieure
  /dormir    sommeil : endort les organes et trie les réflexes
  /idee      ranger une idée, ex. : /idee alkestore : ajouter le paiement mobile
  /idees     toutes tes idées, rangées par catégorie
  /classer   corriger la catégorie d'une idée, ex. : /classer 3 alkestore
  /croissance  stade de vie, taux d'autonomie et ce que Janova a appris
  /aide      cette aide
  /quitter   fermer Janova"""

janova = Janova()
print("Janova est prête.", AIDE, sep="\n")

while True:
    # input() attend que l'utilisateur tape une phrase puis Entrée.
    # Ctrl+C ou Ctrl+D (fin de saisie) ferment Janova proprement au lieu d'afficher une erreur.
    try:
        saisie = input("\ntoi > ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        break

    if saisie in ("/quitter", "/q"):
        break
    elif saisie == "/bilan":
        print(janova.bilan())
    elif saisie == "/reflexes":
        print(f"{len(janova.reflexes)} réflexe(s) appris.")
    elif saisie == "/etat":
        print(janova.etat())
    elif saisie == "/organes":
        print(janova.organes())
    elif saisie == "/dormir":
        print(janova.dormir())
    elif saisie.startswith("/idee "):
        print(janova.ranger_idee(saisie[len("/idee "):]).texte_affiche())
    elif saisie == "/idees":
        print(janova.idees.lister())
    elif saisie.startswith("/classer"):
        morceaux = saisie.split(maxsplit=2)
        if len(morceaux) == 3 and morceaux[1].isdigit():
            print(janova.idees.classer(int(morceaux[1]), morceaux[2]))
        else:
            print("Écris par exemple : /classer 3 alkestore")
    elif saisie == "/croissance":
        print(janova.etat_croissance())
    elif saisie == "/aide":
        print(AIDE)
    elif saisie.startswith("/"):
        print(f"Commande inconnue : {saisie}. Tape /aide pour la liste.")
    elif saisie:
        print(janova.traiter(saisie).texte())

print(janova.dormir())  # avant de partir, Janova range ce qu'elle a appris
