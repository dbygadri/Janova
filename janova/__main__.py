"""Petite démonstration, lancée avec : python -m janova

On demande une tâche à l'utilisateur, et le noyau la découpe en étapes.
"""

from janova.noyau import decouper_en_etapes

# input() affiche la question et attend que l'utilisateur tape une phrase puis Entrée.
tache = input("Quelle tâche dois-je découper ? ")

etapes = decouper_en_etapes(tache)

if not etapes:
    print("Je n'ai reçu aucune tâche.")
else:
    print("Voici les étapes :")
    # enumerate() numérote les étapes ; start=1 pour commencer à 1 au lieu de 0.
    for numero, etape in enumerate(etapes, start=1):
        print(f"  {numero}. {etape}")
