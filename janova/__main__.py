"""Lancer Janova.

    python -m janova                 dans le terminal
    python -m janova --bureau        la fenêtre sur le bureau (avec routines et habitudes chaque minute)
    python -m janova --installer     démarrage automatique avec ta session + entrée dans le menu
    python -m janova --desinstaller  retirer le démarrage automatique
"""

import sys

from janova.conversation import AIDE, Conversation


def terminal() -> None:
    conversation = Conversation()
    print("Janova est prête.", AIDE, sep="\n")
    while True:
        for message in conversation.vivre():  # routines et habitudes, vérifiées entre deux messages
            print(f"\n{message}")
        # input() attend que l'utilisateur tape une phrase puis Entrée.
        # Ctrl+C ou Ctrl+D (fin de saisie) ferment Janova proprement au lieu d'afficher une erreur.
        try:
            saisie = input("\ntoi > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if saisie in ("/quitter", "/q"):
            break
        reponse = conversation.recevoir(saisie)
        if reponse:
            print(reponse)
    print(conversation.fermer())  # avant de partir, Janova range ce qu'elle a appris


if "--bureau" in sys.argv:
    from janova.fenetre import lancer

    lancer()
elif "--installer" in sys.argv:
    from janova.installer import installer

    print(installer())
elif "--desinstaller" in sys.argv:
    from janova.installer import desinstaller

    print(desinstaller())
else:
    terminal()
