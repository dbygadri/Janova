const { contextBridge, ipcRenderer } = require('electron');

const ecouter = (canal) => (fn) => ipcRenderer.on(canal, (_e, ...a) => fn(...a));
const appel = (canal) => (...a) => ipcRenderer.invoke(canal, ...a);

contextBridge.exposeInMainWorld('janova', {
  projets: {
    liste: appel('projets:liste'),
    choisir: appel('projets:choisir'),
    creer: appel('projets:creer'),
    actualiser: () => ipcRenderer.send('projets:actualiser'),
    surChangement: ecouter('projets:changes'),
  },
  terminal: {
    demarrer: (taille) => ipcRenderer.send('terminal:demarrer', taille),
    ecrire: (d) => ipcRenderer.send('terminal:ecrire', d),
    taille: (t) => ipcRenderer.send('terminal:taille', t),
    surDonnees: ecouter('terminal:donnees'),
    surFin: ecouter('terminal:fin'),
  },
  discussions: {
    nouvelle: appel('discussions:nouvelle'),
    ouvrir: appel('discussions:ouvrir'),
    liste: appel('discussions:liste'),
    supprimer: appel('discussions:supprimer'),
    reponse: appel('discussions:reponse'),
  },
  chat: {
    envoyer: (m) => ipcRenderer.send('chat:envoyer', m),
    stop: () => ipcRenderer.send('chat:stop'),
    retenir: appel('chat:retenir'),
    surTexte: ecouter('chat:texte'),
    surNouveauMessage: ecouter('chat:nouveau-message'),
    surOutil: ecouter('chat:outil'),
    surFin: ecouter('chat:fin'),
  },
  maj: {
    etat: appel('maj:etat'),
    preparer: appel('maj:preparer'),
    installer: appel('maj:installer'),
    revenir: appel('maj:revenir'),
    surProgres: ecouter('maj:progres'),
  },
  notes: { lire: appel('notes:lire'), ecrire: appel('notes:ecrire') },
  journal: { historique: appel('journal:historique'), lire: appel('journal:lire') },
  liens: { lire: appel('liens:lire') },
  deploiement: {
    destinations: appel('deploiement:destinations'),
    resume: appel('deploiement:resume'),
    feuVert: appel('deploiement:feu-vert'),
    enregistrer: appel('deploiement:enregistrer'),
  },
  voix: { disponible: appel('voix:disponible'), transcrire: appel('voix:transcrire') },
  telephone: { sujet: appel('telephone:sujet') },
  taches: {
    lire: appel('taches:lire'),
    annuler: appel('taches:annuler'),
    ajouter: appel('taches:ajouter'),
    changer: appel('taches:changer'),
    supprimer: appel('taches:supprimer'),
    surChangement: ecouter('taches:changees'),
  },
});
