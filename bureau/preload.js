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
  taches: {
    lire: appel('taches:lire'),
    ajouter: appel('taches:ajouter'),
    changer: appel('taches:changer'),
    supprimer: appel('taches:supprimer'),
    surChangement: ecouter('taches:changees'),
  },
});
