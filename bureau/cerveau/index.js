// La porte du cerveau : le reste de l'appli ne parle qu'à ce fichier.
// Un cerveau fournit deux choses :
//
//   discuter({ message, session, dossier, consigne, outils }, { surTexte, surNouveauMessage, surOutil })
//     → { arreter(), fin: Promise<{ session, erreur }> }
//     Répond à un message du chat, au fil de l'eau. « session » permet de reprendre une discussion.
//
//   executerTache({ consigne, dossier, interdits, journal, dureeMax })
//     → Promise<{ reussi, resume }>
//     Fait une tâche seul, sans personne devant l'écran, en respectant les interdits.
//
// Aujourd'hui le cerveau est Claude (et Claude Code). Pour brancher le noyau Janova,
// il suffira d'écrire cerveau/janova.js avec les mêmes deux fonctions et de le choisir ici.

const CERVEAUX = {
  claude: () => require('./claude'),
};

const choisi = process.env.JANOVA_CERVEAU || 'claude';
module.exports = (CERVEAUX[choisi] || CERVEAUX.claude)();
