"""Les applications que Janova sait coder par réflexe, sans professeur : ses premiers savoir-faire.

Chaque modèle suit les mêmes règles que le code écrit par un professeur (voir verification.py) :
- la logique dans des fonctions simples, vérifiées par tester() sans ouvrir de fenêtre ;
- main() lance l'application ; tkinter n'est importé que dans main() ;
- le fichier se termine par : if __name__ == "__main__": main()

Les mots-clés servent à reconnaître la demande (« crée-moi une calculatrice »).
"""

CALCULATRICE = '''"""Calculatrice, créée par Janova."""
import ast
import operator

OPERATIONS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
              ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod}


def calculer(expression):
    """Calcule une expression comme « 2 + 3 × 4 », sans eval (donc sans danger). Renvoie le résultat en texte."""
    expression = expression.replace("×", "*").replace("÷", "/").replace(",", ".")

    def valeur(noeud):
        if isinstance(noeud, ast.Constant) and isinstance(noeud.value, (int, float)):
            return noeud.value
        if isinstance(noeud, ast.BinOp) and type(noeud.op) in OPERATIONS:
            gauche, droite = valeur(noeud.left), valeur(noeud.right)
            if isinstance(noeud.op, ast.Pow) and abs(droite) > 100:
                raise ValueError("nombre trop grand")
            return OPERATIONS[type(noeud.op)](gauche, droite)
        if isinstance(noeud, ast.UnaryOp) and isinstance(noeud.op, (ast.USub, ast.UAdd)):
            nombre = valeur(noeud.operand)
            return -nombre if isinstance(noeud.op, ast.USub) else nombre
        raise ValueError("expression invalide")

    resultat = valeur(ast.parse(expression, mode="eval").body)
    return f"{resultat:g}" if isinstance(resultat, float) else str(resultat)


def main():
    import tkinter as tk

    fenetre = tk.Tk()
    fenetre.title("Calculatrice")
    fenetre.resizable(False, False)
    ecran = tk.StringVar()
    tk.Entry(fenetre, textvariable=ecran, font=("TkDefaultFont", 18), justify="right", width=16).grid(
        row=0, column=0, columnspan=4, padx=6, pady=6, sticky="we")

    def appuyer(touche):
        if touche == "C":
            ecran.set("")
        elif touche == "=":
            try:
                ecran.set(calculer(ecran.get()))
            except (ValueError, SyntaxError, ZeroDivisionError, OverflowError):
                ecran.set("Erreur")
        else:
            ecran.set(ecran.get() + touche)

    touches = ["7", "8", "9", "÷", "4", "5", "6", "×", "1", "2", "3", "-", "0", ".", "C", "+", "(", ")", "%", "="]
    for numero, touche in enumerate(touches):
        tk.Button(fenetre, text=touche, width=4, height=2, font=("TkDefaultFont", 14),
                  command=lambda t=touche: appuyer(t)).grid(row=1 + numero // 4, column=numero % 4, padx=2, pady=2)
    fenetre.bind("<Return>", lambda evenement: appuyer("="))
    fenetre.mainloop()


def tester():
    assert calculer("2 + 3 × 4") == "14"
    assert calculer("7 ÷ 2") == "3.5"
    assert calculer("-(2 + 3)") == "-5"
    for mauvais in ("2 +", "import os", "1 / 0"):
        try:
            calculer(mauvais)
        except (ValueError, SyntaxError, ZeroDivisionError):
            continue
        raise AssertionError(f"aurait dû refuser : {mauvais}")


if __name__ == "__main__":
    main()
'''

MINUTEUR = '''"""Minuteur, créé par Janova."""


def lire_duree(texte):
    """« 5 » = 5 minutes, « 1:30 » = 1 minute 30, « 90s » = 90 secondes. Renvoie des secondes."""
    texte = texte.strip().lower().replace(",", ".")
    if texte.endswith("s"):
        return int(float(texte[:-1]))
    if ":" in texte:
        minutes, secondes = texte.split(":", 1)
        return int(minutes or 0) * 60 + int(secondes or 0)
    return int(float(texte) * 60)


def formater(secondes):
    minutes, secondes = divmod(max(int(secondes), 0), 60)
    heures, minutes = divmod(minutes, 60)
    return f"{heures}:{minutes:02d}:{secondes:02d}" if heures else f"{minutes:02d}:{secondes:02d}"


def main():
    import tkinter as tk

    fenetre = tk.Tk()
    fenetre.title("Minuteur")
    fenetre.resizable(False, False)
    etat = {"reste": 0, "actif": False}
    affichage = tk.Label(fenetre, text="00:00", font=("TkDefaultFont", 36))
    affichage.pack(padx=20, pady=10)
    saisie = tk.Entry(fenetre, justify="center", width=10)
    saisie.insert(0, "5")
    saisie.pack()
    tk.Label(fenetre, text="minutes (ou 1:30, ou 90s)").pack()

    def tic():
        if not etat["actif"]:
            return
        affichage.config(text=formater(etat["reste"]))
        if etat["reste"] <= 0:
            etat["actif"] = False
            affichage.config(text="Terminé !")
            for delai in (0, 400, 800):
                fenetre.after(delai, fenetre.bell)
            return
        etat["reste"] -= 1
        fenetre.after(1000, tic)

    def demarrer():
        try:
            etat["reste"] = lire_duree(saisie.get())
        except ValueError:
            affichage.config(text="Durée ?")
            return
        etat["actif"] = True
        tic()

    def arreter():
        etat["actif"] = False

    boutons = tk.Frame(fenetre)
    boutons.pack(pady=10)
    tk.Button(boutons, text="Démarrer", command=demarrer).pack(side="left", padx=4)
    tk.Button(boutons, text="Arrêter", command=arreter).pack(side="left", padx=4)
    fenetre.mainloop()


def tester():
    assert lire_duree("5") == 300
    assert lire_duree("1:30") == 90
    assert lire_duree("90s") == 90
    assert formater(65) == "01:05"
    assert formater(3725) == "1:02:05"


if __name__ == "__main__":
    main()
'''

BLOC_NOTES = '''"""Bloc-notes, créé par Janova. Les notes sont gardées dans ~/.local/share/janova-apps/bloc-notes.txt"""
from pathlib import Path


def chemin_notes():
    return Path.home() / ".local" / "share" / "janova-apps" / "bloc-notes.txt"


def lire():
    chemin = chemin_notes()
    return chemin.read_text(encoding="utf-8") if chemin.exists() else ""


def ecrire(texte):
    chemin = chemin_notes()
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(texte, encoding="utf-8")


def compter_mots(texte):
    return len(texte.split())


def main():
    import tkinter as tk

    fenetre = tk.Tk()
    fenetre.title("Bloc-notes")
    fenetre.geometry("520x420")
    zone = tk.Text(fenetre, wrap="word", undo=True, padx=8, pady=8)
    zone.pack(fill="both", expand=True)
    zone.insert("1.0", lire())
    statut = tk.Label(fenetre, anchor="w")
    statut.pack(fill="x")

    def sauver():
        texte = zone.get("1.0", "end-1c")
        ecrire(texte)
        statut.config(text=f"{compter_mots(texte)} mot(s) — enregistré")
        fenetre.after(10000, sauver)  # enregistrement automatique toutes les 10 secondes

    def fermer():
        ecrire(zone.get("1.0", "end-1c"))
        fenetre.destroy()

    fenetre.protocol("WM_DELETE_WINDOW", fermer)
    fenetre.after(10000, sauver)
    fenetre.mainloop()


def tester():
    assert compter_mots("bonjour le monde") == 3
    assert compter_mots("") == 0
    ecrire("essai de Janova")
    assert lire() == "essai de Janova"


if __name__ == "__main__":
    main()
'''

MODELES = {
    "calculatrice": {"nom": "Calculatrice", "description": "Une calculatrice avec des boutons",
                     "mots_cles": ["calculatrice", "calculette"], "fenetre": True, "code": CALCULATRICE},
    "minuteur": {"nom": "Minuteur", "description": "Un minuteur qui sonne à la fin",
                 "mots_cles": ["minuteur", "compte a rebours", "timer", "chrono"], "fenetre": True, "code": MINUTEUR},
    "bloc-notes": {"nom": "Bloc-notes", "description": "Un bloc-notes qui enregistre tout seul",
                   "mots_cles": ["bloc-notes", "bloc notes", "pense-bete", "prise de notes"], "fenetre": True,
                   "code": BLOC_NOTES},
}
