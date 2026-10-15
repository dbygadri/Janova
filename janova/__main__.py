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
    elif saisie == "/aide":
        print(AIDE)
    elif saisie.startswith("/"):
        print(f"Commande inconnue : {saisie}. Tape /aide pour la liste.")
    elif saisie:
        print(janova.traiter(saisie).texte())

print(janova.dormir())  # avant de partir, Janova range ce qu'elle a appris
