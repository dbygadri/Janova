// La porte du cerveau : le reste de l'appli ne parle qu'à ce fichier.
// Un cerveau fournit deux choses :
//
//   discuter({ message, session, dossier, consigne, contexte }, { surTexte, surNouveauMessage, surOutil })
//     → { arreter(), fin: Promise<{ session, erreur, couche }> }
//     Répond à un message du chat, au fil de l'eau. « session » permet de reprendre une discussion ;
//     « couche » dit qui a répondu (« noyau » ou « claude »).
//
//   executerTache({ consigne, dossier, interdits, journal, dureeMax })
//     → Promise<{ reussi, resume }>
//     Fait une tâche seul, sans personne devant l'écran, en respectant les interdits.
//
// Par défaut, le cerveau est « en couches » : le noyau Janova d'abord, Claude pour le neuf.
// Quand le noyau saura tout faire seul, il suffira d'ajuster couches.js ou d'en choisir un autre ici.

const CERVEAUX = {
  couches: () => require('./couches'),
  claude: () => require('./claude'),
};

const choisi = process.env.JANOVA_CERVEAU || 'couches';
module.exports = (CERVEAUX[choisi] || CERVEAUX.couches)();
