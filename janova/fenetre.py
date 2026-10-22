"""La fenêtre de Janova sur le bureau : une zone de texte pour lui parler, toujours à portée de main.

Lancement : python -m janova --bureau
Pour qu'elle démarre toute seule avec ta session : python -m janova --installer

Elle utilise Tkinter, la bibliothèque de fenêtres fournie avec Python. Sur certains Linux (Ubuntu, Debian),
il faut l'installer une fois : sudo apt install python3-tk

Janova travaille dans un fil séparé (un « thread ») : la fenêtre reste fluide même quand le professeur réfléchit.
Toutes les minutes, elle vérifie les routines et les habitudes (vivre()).
"""

import queue
import threading

from janova.conversation import Conversation
from janova.mains.primitives import Executeur

INTERVALLE_VIE_MS = 60_000  # toutes les minutes : routines, yeux, habitudes


def lancer() -> None:
    try:
        import tkinter as tk
    except ImportError:
        print("Il manque Tkinter pour afficher la fenêtre. Installe-le une fois avec :\n"
              "  sudo apt install python3-tk\npuis relance : python -m janova --bureau")
        return
    FenetreJanova(tk).boucle()


class FenetreJanova:
    def __init__(self, tk, fabrique=Conversation) -> None:
        self.tk = tk
        self.fabrique = fabrique  # crée la conversation (les tests en donnent une avec un dossier temporaire)
        self.taches: queue.Queue = queue.Queue()  # ce que Janova doit faire (dans son fil)
        self.reponses: queue.Queue = queue.Queue()  # ce qu'elle répond (à afficher)
        self.conversation: Conversation | None = None

        self.racine = racine = tk.Tk()
        racine.title("Janova")
        racine.geometry("460x380")
        racine.minsize(320, 240)

        self.journal = tk.Text(racine, wrap="word", state="disabled", padx=8, pady=8, borderwidth=0)
        self.journal.tag_configure("toi", font=("TkDefaultFont", 10, "bold"))
        self.journal.tag_configure("janova", lmargin1=8, lmargin2=8)

        self.boutons = tk.Frame(racine)
        tk.Button(self.boutons, text="Oui", width=8, command=lambda: self.envoyer("oui")).pack(side="left", padx=4)
        tk.Button(self.boutons, text="Non", width=8, command=lambda: self.envoyer("non")).pack(side="left", padx=4)

        bas = tk.Frame(racine)
        bas.pack(fill="x", side="bottom", padx=6, pady=6)
        self.devant = tk.BooleanVar(value=False)
        tk.Checkbutton(bas, text="Devant", variable=self.devant,
                       command=lambda: racine.attributes("-topmost", self.devant.get())).pack(side="right")
        self.zone = tk.Entry(bas)
        self.zone.pack(fill="x", side="left", expand=True)
        self.zone.bind("<Return>", lambda _evenement: self.envoyer(self.zone.get()))
        self.zone.focus_set()
        self.bas = bas
        self.journal.pack(fill="both", expand=True)  # après la barre du bas, pour qu'elle reste toujours visible

        racine.protocol("WM_DELETE_WINDOW", self.fermer)
        self.afficher("Janova", "Je me réveille…")
        threading.Thread(target=self._travailler, daemon=True).start()
        racine.after(100, self._recevoir_reponses)
        racine.after(INTERVALLE_VIE_MS, self._vivre)

    # --- Le fil de Janova : tout ce qu'elle fait passe ici, une chose à la fois -------------------------

    def _travailler(self) -> None:
        self.conversation = self.fabrique()
        self.reponses.put(("Janova", "Je suis prête. Écris-moi ce que tu veux, ou /aide.", False))
        while True:
            genre, texte = self.taches.get()
            try:
                if genre == "message":
                    self.reponses.put(("Janova", self.conversation.recevoir(texte), False))
                elif genre == "vivre":
                    for message in self.conversation.vivre():
                        self.reponses.put(("Janova", message, True))
                elif genre == "fermer":
                    self.conversation.fermer()
                    self.reponses.put(("fin", "", False))
                    return
            except Exception as erreur:  # une erreur ne doit jamais tuer Janova : on l'affiche et on continue
                self.reponses.put(("Janova", f"Oups, une erreur : {erreur}", False))
            self.reponses.put(("attente", "", False))

    # --- La fenêtre ---------------------------------------------------------------------------------

    def envoyer(self, texte: str) -> None:
        texte = texte.strip()
        if not texte:
            return
        self.zone.delete(0, "end")
        self.afficher("Toi", texte)
        if texte in ("/quitter", "/q"):
            self.fermer()
            return
        self.taches.put(("message", texte))

    def afficher(self, qui: str, texte: str) -> None:
        if not texte:
            return
        self.journal.configure(state="normal")
        self.journal.insert("end", f"{qui} : ", "toi" if qui == "Toi" else "janova")
        self.journal.insert("end", texte + "\n\n", "janova")
        self.journal.configure(state="disabled")
        self.journal.see("end")

    def _recevoir_reponses(self) -> None:
        try:
            while True:
                qui, texte, spontane = self.reponses.get_nowait()
                if qui == "fin":
                    self.racine.destroy()
                    return
                if qui == "attente":
                    self._montrer_boutons()
                    continue
                self.afficher(qui, texte)
                if spontane and self.racine.focus_displayof() is None:
                    # Janova parle d'elle-même et la fenêtre n'est pas regardée : une notification du bureau.
                    Executeur().lancer(["notify-send", "Janova", texte[:200]])
        except queue.Empty:
            pass
        self.racine.after(100, self._recevoir_reponses)

    def _montrer_boutons(self) -> None:
        attend = self.conversation is not None and bool(self.conversation.janova.en_attente)
        if attend:
            self.boutons.pack(after=self.bas, side="bottom", pady=4)
        else:
            self.boutons.pack_forget()

    def _vivre(self) -> None:
        self.taches.put(("vivre", ""))
        self.racine.after(INTERVALLE_VIE_MS, self._vivre)

    def fermer(self) -> None:
        self.afficher("Janova", "Bonne nuit, je range ce que j'ai appris…")
        self.taches.put(("fermer", ""))

    def boucle(self) -> None:
        self.racine.mainloop()
