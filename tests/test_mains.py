"""Tests des mains, de la confiance, des routines, des yeux, de la conversation et de la fenêtre.

Rien ne touche ton vrai ordinateur : un faux exécuteur note les commandes au lieu de les lancer,
et le « dossier personnel » est un dossier temporaire.
"""

import json
import queue
import tempfile
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from janova.conversation import Conversation
from janova.decision import Decideur
from janova.installer import desinstaller, installer
from janova.mains import Confiance, Contexte, Mains, comprendre
from janova.mains.primitives import fond_ecran, ranger_dossier, resoudre_chemin, theme
from janova.noyau import Janova
from janova.routines import Routines, extraire_routine
from janova.yeux import Yeux


class FauxExecuteur:
    """Note les commandes. Répond comme gsettings : le thème actuel est « default »."""

    def __init__(self):
        self.commandes = []
        self.lances = []

    def lancer(self, commande):
        self.commandes.append(commande)
        if commande[:2] == ["gsettings", "get"]:
            return 0, "'default'"
        return 0, ""

    def detacher(self, commande):
        self.lances.append(commande)
        return True

    def trouver(self, programme):
        return f"/usr/bin/{programme}" if programme == "firefox" else None


class FauxProfesseur:
    nom = "aide extérieure"
    modele = "faux"
    indisponible = ""

    def __init__(self, reponse):
        self.reponse = reponse
        self.appels = 0

    def demander(self, question, en_json=False):
        self.appels += 1
        return self.reponse


class BaseTest(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.TemporaryDirectory()
        self.racine = Path(self.dossier.name)
        self.maison = self.racine / "maison"
        (self.maison / "Téléchargements").mkdir(parents=True)
        self.executeur = FauxExecuteur()
        self.contexte = Contexte(self.maison, self.executeur, "gnome")

    def tearDown(self):
        self.dossier.cleanup()

    def janova(self, aide=None):
        return Janova(self.racine / "donnees", aide=aide, contexte_systeme=self.contexte)


class TestComprendre(BaseTest):
    def test_formules_courantes(self):
        self.assertEqual(comprendre("trie mes dossiers"), [("ranger_dossier", {"dossier": "téléchargements"})])
        self.assertEqual(comprendre("mets le thème sombre"), [("theme", {"mode": "sombre"})])
        self.assertEqual(comprendre("change mon thème"), [("theme", {"mode": "inverse"})])
        self.assertEqual(comprendre("ouvre firefox"), [("ouvrir", {"cible": "firefox"})])
        self.assertEqual(comprendre("déplace facture.pdf dans Documents"),
                         [("deplacer", {"source": "facture.pdf", "destination": "Documents"})])
        self.assertEqual(comprendre("supprime vieux.txt"), [("corbeille", {"chemin": "vieux.txt"})])
        self.assertIsNone(comprendre("calcule 2 + 2"))
        self.assertIsNone(comprendre("ouvre le fichier"))


class TestPrimitives(BaseTest):
    def test_chemins_en_francais(self):
        self.assertEqual(resoudre_chemin(self.contexte, "mes téléchargements"), self.maison / "Téléchargements")
        self.assertEqual(resoudre_chemin(self.contexte, "~/notes"), self.maison / "notes")

    def test_ranger_puis_annuler(self):
        dossier = self.maison / "Téléchargements"
        for nom in ("photo.jpg", "facture.pdf", "film.mkv", "truc.xyz", "en_cours.part"):
            (dossier / nom).write_text("x")
        resultat = ranger_dossier(self.contexte, "téléchargements")
        self.assertIn("4 fichier(s)", resultat.texte)
        self.assertTrue((dossier / "Images" / "photo.jpg").exists())
        self.assertTrue((dossier / "en_cours.part").exists())  # un téléchargement pas fini : on n'y touche pas
        resultat.annulation()
        self.assertTrue((dossier / "photo.jpg").exists())
        self.assertFalse((dossier / "Images").exists())  # le dossier créé, resté vide, est retiré

    def test_ranger_n_ecrase_jamais(self):
        dossier = self.maison / "Téléchargements"
        (dossier / "Images").mkdir()
        (dossier / "Images" / "photo.jpg").write_text("ancienne")
        (dossier / "photo.jpg").write_text("nouvelle")
        ranger_dossier(self.contexte, "téléchargements")
        self.assertEqual((dossier / "Images" / "photo.jpg").read_text(), "ancienne")
        self.assertEqual((dossier / "Images" / "photo (2).jpg").read_text(), "nouvelle")

    def test_theme_gnome_et_annulation(self):
        resultat = theme(self.contexte, "inverse")
        self.assertEqual(resultat.texte, "Thème sombre activé.")
        self.assertIn(["gsettings", "set", "org.gnome.desktop.interface", "color-scheme", "prefer-dark"],
                      self.executeur.commandes)
        resultat.annulation()
        self.assertEqual(self.executeur.commandes[-1][-1], "default")

    def test_fond_ecran_au_hasard_dans_les_images(self):
        (self.maison / "Images").mkdir()
        (self.maison / "Images" / "plage.png").write_bytes(b"x")
        self.assertIn("plage.png", fond_ecran(self.contexte).texte)


class TestConfiance(BaseTest):
    def test_l_autonomie_grandit_avec_les_accords(self):
        confiance = Confiance(self.racine / "confiance.json")
        for _ in range(2):
            confiance.accord("theme")
        self.assertFalse(confiance.autonome("theme"))
        confiance.accord("theme")
        self.assertTrue(confiance.autonome("theme"))
        confiance.refus("theme")
        self.assertFalse(confiance.autonome("theme"))  # un refus remet à zéro

    def test_la_corbeille_n_est_jamais_automatique(self):
        confiance = Confiance()
        for _ in range(10):
            confiance.accord("corbeille")
        self.assertFalse(confiance.autonome("corbeille"))


class TestMainsDansJanova(BaseTest):
    def test_propose_puis_agit_seule_apres_trois_accords(self):
        conversation = Conversation(self.janova())
        for _ in range(3):
            self.assertIn("Je propose : changer le thème (sombre)", conversation.recevoir("mets le thème sombre"))
            self.assertEqual(conversation.recevoir("oui"), "Thème sombre activé.")
        reponse = conversation.recevoir("mets le thème sombre")
        self.assertIn("Thème sombre activé.", reponse)
        self.assertNotIn("Je propose", reponse)

    def test_non_et_annuler(self):
        (self.maison / "Téléchargements" / "photo.jpg").write_text("x")
        conversation = Conversation(self.janova())
        conversation.recevoir("range mes téléchargements")
        self.assertIn("je ne fais rien", conversation.recevoir("non"))
        self.assertTrue((self.maison / "Téléchargements" / "photo.jpg").exists())
        conversation.recevoir("range mes téléchargements")
        conversation.recevoir("oui")
        self.assertFalse((self.maison / "Téléchargements" / "photo.jpg").exists())
        self.assertIn("remis", conversation.recevoir("/annuler"))
        self.assertTrue((self.maison / "Téléchargements" / "photo.jpg").exists())

    def test_le_professeur_apprend_une_recette(self):
        professeur = FauxProfesseur(json.dumps({"gestes": [
            {"primitive": "creer_dossier", "parametres": {"chemin": "Projets/Janova"}},
            {"primitive": "ouvrir", "parametres": {"cible": "~/Projets/Janova"}},
        ]}))
        conversation = Conversation(self.janova(professeur))
        demande = "prépare mon espace de travail Janova sur le bureau"
        self.assertIn("Je propose : créer un dossier", conversation.recevoir(demande))
        conversation.recevoir("oui")
        self.assertTrue((self.maison / "Projets" / "Janova").is_dir())
        self.assertIn("Je propose", conversation.recevoir(demande))  # la recette resert, sans professeur
        self.assertEqual(professeur.appels, 1)

    def test_le_professeur_ne_peut_pas_inventer_de_geste(self):
        professeur = FauxProfesseur(json.dumps({"gestes": [{"primitive": "rm_rf", "parametres": {}}]}))
        janova = self.janova(professeur)
        janova.traiter("installe le wifi sur cet ordinateur")
        self.assertEqual(janova.en_attente, [])


class TestRoutines(BaseTest):
    def test_phrases(self):
        self.assertEqual(extraire_routine("tous les matins, change mon thème"), ("08:00", list(range(7)), "change mon thème"))
        self.assertEqual(extraire_routine("chaque lundi à 9h range mes téléchargements"),
                         ("09:00", [0], "range mes téléchargements"))
        self.assertIsNone(extraire_routine("calcule 2 + 2"))

    def test_une_fois_par_jour(self):
        routines = Routines(self.racine / "routines.json")
        routines.ajouter("08:00", list(range(7)), "change mon thème", maintenant=datetime(2026, 10, 22, 7, 0))
        self.assertEqual(routines.dues(datetime(2026, 10, 22, 7, 59)), [])
        self.assertEqual(len(routines.dues(datetime(2026, 10, 22, 8, 0))), 1)
        self.assertEqual(routines.dues(datetime(2026, 10, 22, 9, 0)), [])
        self.assertEqual(len(routines.dues(datetime(2026, 10, 23, 8, 1))), 1)

    def test_janova_lance_la_routine(self):
        janova = self.janova()
        for _ in range(3):  # la confiance est déjà gagnée pour le thème
            janova.mains.confiance.accord("theme")
        janova.routines.ajouter("08:00", list(range(7)), "change mon thème", maintenant=datetime(2026, 10, 22, 7, 0))
        messages = janova.vivre(datetime(2026, 10, 22, 8, 0))
        self.assertIn("Thème sombre activé.", messages[0])


class TestYeux(BaseTest):
    def test_fermes_par_defaut(self):
        yeux = Yeux(self.racine / "yeux", self.maison)
        yeux.noter("mets le thème sombre")
        self.assertEqual(yeux.etat["evenements"], [])

    def test_habitude_proposee_puis_routine(self):
        janova = self.janova()
        janova.yeux.ouvrir(True)
        lundi = datetime(2026, 10, 19, 21, 0)
        for jour in range(3):
            janova.yeux.noter("mets le thème sombre", lundi + timedelta(days=jour))
        messages = janova.vivre(lundi + timedelta(days=3, hours=-12))
        self.assertIn("le soir (3 jours différents)", messages[0])
        self.assertIn("C'est noté", janova.valider(True))
        self.assertEqual(janova.routines.routines[0].tache, "mets le thème sombre")
        messages = janova.vivre(lundi + timedelta(days=4))
        self.assertTrue(messages[0].startswith("Routine"))  # la routine se lance le soir venu
        self.assertFalse(any("remarqué" in m for m in messages))  # l'habitude n'est plus proposée

    def test_lit_les_fichiers_recents_de_linux(self):
        yeux = Yeux(self.racine / "yeux", self.maison)
        yeux.ouvrir(True)
        yeux.etat["vu_jusqu_a"] = "2026-01-01T00:00:00"
        liste = self.maison / ".local/share/recently-used.xbel"
        liste.parent.mkdir(parents=True)
        adresse = (self.maison / "Documents" / "compta.ods").as_uri()
        liste.write_text(f'<?xml version="1.0"?><xbel version="1.0"><bookmark href="{adresse}" '
                         'added="2026-10-20T08:00:00Z" modified="2026-10-20T08:05:00Z" visited="2026-10-20T08:05:00Z"/>'
                         '</xbel>', encoding="utf-8")
        self.assertEqual(yeux.regarder(), 1)
        self.assertEqual(yeux.etat["evenements"][0]["quoi"], "ouvre ~/Documents/compta.ods")
        self.assertEqual(yeux.regarder(), 0)  # déjà vu


class TestConversation(BaseTest):
    def test_routine_par_phrase(self):
        conversation = Conversation(self.janova())
        self.assertIn("tous les jours à 08:00 : change mon thème",
                      conversation.recevoir("tous les matins, change mon thème"))
        self.assertIn("n°1", conversation.recevoir("/routines"))

    def test_oui_sans_rien_en_attente_est_une_tache_normale(self):
        conversation = Conversation(self.janova())
        self.assertNotIn("Je n'attends", conversation.recevoir("oui"))

    def test_installer(self):
        installer(self.maison)
        self.assertIn("--bureau", (self.maison / ".config/autostart/janova.desktop").read_text())
        self.assertIn("2 fichier(s)", desinstaller(self.maison))


class FauxWidget:
    def __init__(self, *args, **kwargs):
        self.texte = ""

    def __getattr__(self, nom):
        return lambda *args, **kwargs: None

    def insert(self, position, texte, *tags):
        self.texte += texte

    def get(self):
        return self.texte


class FauxTk:
    """Remplace Tkinter, absent des machines de test, pour vérifier la logique de la fenêtre."""

    Text = Frame = Button = Entry = Checkbutton = FauxWidget

    class BooleanVar(FauxWidget):
        pass

    class Tk(FauxWidget):
        def focus_displayof(self):
            return True


class TestFenetre(BaseTest):
    def test_la_fenetre_transmet_et_affiche(self):
        from janova.fenetre import FenetreJanova

        fenetre = FenetreJanova(FauxTk, lambda: Conversation(self.janova()))
        fenetre.envoyer("calcule 2 + 2")
        fin = time.time() + 5
        while "2 + 2 = 4" not in fenetre.journal.texte and time.time() < fin:
            try:
                qui, texte, _ = fenetre.reponses.get(timeout=0.2)
                if qui == "Janova":
                    fenetre.afficher(qui, texte)
            except queue.Empty:
                pass
        self.assertIn("2 + 2 = 4", fenetre.journal.texte)
        fenetre.taches.put(("fermer", ""))
        while time.time() < fin + 5:  # on attend que Janova ait fini de ranger avant d'effacer le dossier
            if fenetre.reponses.get(timeout=1)[0] == "fin":
                break


if __name__ == "__main__":
    unittest.main()
