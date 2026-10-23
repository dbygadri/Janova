const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const os = require('os');
const fs = require('fs');
const pty = require('node-pty');
const projets = require('./lib/projets');
const taches = require('./lib/taches');
const discussions = require('./lib/discussions');
const miseAJour = require('./lib/mise-a-jour');
const cerveau = require('./cerveau');

const ENV = cerveau.ENV;

const CONSIGNE_COMMUNE = `Tu es l'assistant de Janova, le tableau de bord de développement personnel de l'utilisateur.
L'utilisateur ne sait pas coder mais il est très imaginatif. Réponds en français simple, en phrases courtes, sans jargon.
Comporte-toi comme un développeur à qui il confie un travail : pose quelques questions simples si besoin, puis propose.
Devoir de conseil : si une demande peut poser problème (sécurité, coût, perte de données, mauvaise idée), dis-le avant, explique le risque simplement, propose mieux, et laisse-le trancher.
Tu peux lire des fichiers pour comprendre, mais tu ne modifies rien toi-même.

Si l'utilisateur veut créer un nouveau projet, propose-le exactement sous cette forme (nom sans espace ni accent) :
\`\`\`janova-projet
{"nom": "nom-du-projet", "description": "une phrase"}
\`\`\`
puis demande : « Est-ce que je crée ce projet ? » Janova crée alors le dossier et un dépôt GitHub privé.`;

function consigneChat(projet) {
  if (!projet) {
    return CONSIGNE_COMMUNE + `\n\nCette discussion n'est liée à aucun projet : c'est une question générale. Ne propose pas de tâche pour Claude Code ici ; si un travail sur le code est demandé, dis à l'utilisateur de choisir d'abord le projet dans le menu en haut.`;
  }
  const depots = projet.groupe
    ? `Ce projet regroupe plusieurs dépôts git, chacun dans un sous-dossier : ${projet.depots.join(', ')}. Une tâche = un seul dépôt ; indique-le dans "dossier".`
    : `Le projet est un seul dépôt git ; laisse "dossier" vide.`;
  const soiMeme = projet.id === 'gh-janova'
    ? `\nCe projet est Janova elle-même : « janova/ » est le noyau d'IA locale (Python), « bureau/ » est l'application que l'utilisateur utilise en ce moment (Electron). Les changements de « bureau/ » ne s'appliquent qu'après son oui, via le bouton « Nouvelle version de Janova ». Les garde-fous (bureau/lib/garde-fous.js, bureau/lib/mise-a-jour.js, bureau/runner.js, bureau/cerveau/) ne se modifient jamais sans qu'il l'ait demandé explicitement : préviens-le avant.`
    : '';
  return CONSIGNE_COMMUNE + `

Projet actuel : ${projet.nom}, dans ${projet.dossier}. ${depots}${soiMeme}

Quand l'utilisateur veut un travail sur le code, rédige une tâche pour Claude Code, exactement sous cette forme :
\`\`\`janova-tache
{"titre": "titre court", "dossier": "${projet.groupe ? projet.depots[0] : ''}", "instructions": "instructions précises et complètes pour Claude Code"}
\`\`\`
Claude Code travaillera seul, sur une branche git, sans pouvoir déployer.
Juste après le bloc, demande : « Est-ce que Claude Code peut démarrer cette tâche ? » L'utilisateur répondra avec les boutons Oui / Non.`;
}

let fenetre;
let terminal = null;
let chat = null;
let projet = null;
let discussion = null;

function creerFenetre() {
  fenetre = new BrowserWindow({
    width: 1500,
    height: 900,
    title: 'Janova',
    icon: path.join(__dirname, 'icone.png'),
    backgroundColor: '#16181d',
    autoHideMenuBar: true,
    show: !process.argv.includes('--autotest'),
    webPreferences: { preload: path.join(__dirname, 'preload.js') },
  });
  fenetre.loadFile('index.html');
  fenetre.on('closed', () => {
    fenetre = null;
    if (terminal) terminal.kill();
    if (chat) chat.arreter();
  });
  // Contrôle d'une nouvelle version avant installation : la fenêtre doit s'ouvrir sans erreur.
  if (process.argv.includes('--autotest')) {
    const erreursPage = [];
    fenetre.webContents.on('console-message', (e) => { if (e.level === 'error') erreursPage.push(e.message); });
    fenetre.webContents.on('preload-error', (_e, _p, err) => erreursPage.push(String(err)));
    fenetre.webContents.on('did-finish-load', () => setTimeout(async () => {
      const ok = await fenetre.webContents.executeJavaScript(`!!document.querySelector('#projet option') && !!document.querySelector('.xterm')`).catch(() => false);
      if (!ok) erreursPage.push('La fenêtre ne s\'est pas affichée correctement.');
      console.log(erreursPage.length ? 'AUTOTEST ECHEC\n' + erreursPage.join('\n') : 'AUTOTEST OK');
      if (terminal) terminal.kill();
      app.exit(erreursPage.length ? 1 : 0);
    }, 4000));
  }
}

const envoyer = (canal, ...args) => fenetre && !fenetre.isDestroyed() && fenetre.webContents.send(canal, ...args);
const erreurs = (fn) => async (_e, ...a) => {
  try { return { ok: await fn(...a) }; } catch (e) { return { erreur: e.message }; }
};

// --- Projets ---
ipcMain.handle('projets:liste', () => ({ projets: projets.liste(), actuel: projet ? projet.id : projets.dernier() }));
// Au démarrage, Janova va chercher sur GitHub les dépôts ajoutés depuis la dernière fois.
ipcMain.on('projets:actualiser', () => projets.actualiserGithub().then(() => envoyer('projets:changes')).catch(() => {}));

let surveille = null;
function surveillerTaches() {
  if (surveille) fs.unwatchFile(surveille);
  surveille = taches.fichier(projet);
  fs.watchFile(surveille, { interval: 1000 }, () => envoyer('taches:changees'));
}

ipcMain.handle('projets:choisir', erreurs(async (id) => {
  const p = projets.trouver(id);
  if (!p) throw new Error('Projet introuvable.');
  await projets.preparer(p);
  projet = projets.trouver(id);
  projets.memoriserDernier(id);
  surveillerTaches();
  return projet;
}));

ipcMain.handle('projets:creer', erreurs(async ({ nom, description }) => projets.creer(nom, description)));

// --- Terminal Claude Code ---
ipcMain.on('terminal:demarrer', (_e, { cols, rows }) => {
  if (terminal) terminal.kill();
  const cwd = projet && fs.existsSync(projet.dossier) ? projet.dossier : os.homedir();
  const t = pty.spawn('/bin/bash', ['-i', '-c', 'claude; exec bash -i'], { name: 'xterm-256color', cols, rows, cwd, env: ENV });
  terminal = t;
  t.onData((d) => terminal === t && envoyer('terminal:donnees', d));
  t.onExit(() => { if (terminal === t) { terminal = null; envoyer('terminal:fin'); } });
});
ipcMain.on('terminal:ecrire', (_e, d) => terminal && terminal.write(d));
ipcMain.on('terminal:taille', (_e, { cols, rows }) => terminal && terminal.resize(cols, rows));

// --- Discussions ---
ipcMain.handle('discussions:nouvelle', (_e, projetId) => {
  const p = projetId ? projets.trouver(projetId) : null;
  discussion = discussions.nouvelle(p && p.id, p ? p.dossier : os.homedir());
  return discussion;
});
ipcMain.handle('discussions:ouvrir', (_e, id) => {
  const d = discussions.lire(id);
  if (d) discussion = d;
  return d;
});
ipcMain.handle('discussions:liste', (_e, filtre) => discussions.liste(filtre));
ipcMain.handle('discussions:supprimer', (_e, id) => discussions.supprimer(id));
ipcMain.handle('discussions:reponse', (_e, { message, bloc, reponse }) => {
  const m = discussion && discussion.messages[message];
  if (!m) return;
  m.reponses = { ...(m.reponses || {}), [bloc]: reponse };
  discussions.enregistrer(discussion);
});

// --- Chat avec le cerveau ---
ipcMain.on('chat:envoyer', async (_e, message) => {
  if (chat || !discussion) return;
  const d = discussion;
  const p = d.projet ? projets.trouver(d.projet) : null;
  if (!d.messages.length) d.titre = message.replace(/\s+/g, ' ').slice(0, 70);
  d.messages.push({ role: 'moi', texte: message });
  const reponse = { role: 'claude', texte: '' };
  d.messages.push(reponse);

  chat = cerveau.discuter(
    { message, session: d.session, dossier: fs.existsSync(d.cwd) ? d.cwd : os.homedir(), consigne: consigneChat(p) },
    {
      surTexte: (t) => { reponse.texte += t; envoyer('chat:texte', t); },
      surNouveauMessage: () => {
        if (reponse.texte && !reponse.texte.endsWith('\n\n')) reponse.texte += '\n\n';
        envoyer('chat:nouveau-message');
      },
      surOutil: (nom) => envoyer('chat:outil', nom),
    },
  );
  const { session, erreur } = await chat.fin;
  chat = null;
  d.session = session;
  if (!reponse.texte) d.messages.pop();
  discussions.enregistrer(d);
  envoyer('chat:fin', erreur);
});
ipcMain.on('chat:stop', () => chat && chat.arreter());

// --- Mises à jour de Janova elle-même ---
ipcMain.handle('maj:etat', erreurs(() => miseAJour.etat()));
ipcMain.handle('maj:preparer', erreurs(() => miseAJour.preparer((ligne) => envoyer('maj:progres', ligne))));
ipcMain.handle('maj:installer', erreurs(async (version) => {
  await miseAJour.installer(version);
  redemarrer();
}));
ipcMain.handle('maj:revenir', erreurs(async () => {
  await miseAJour.revenir();
  redemarrer();
}));
// Relance Janova depuis la version désormais installée.
function redemarrer() {
  setTimeout(() => {
    app.relaunch({ execPath: miseAJour.electronActuel(), args: [miseAJour.ACTUELLE] });
    app.exit(0);
  }, 300);
}

// --- Tâches du projet actuel ---
ipcMain.handle('taches:lire', () => (projet ? taches.lire(projet) : []));
ipcMain.handle('taches:ajouter', (_e, t) => projet && taches.ajouter(projet, t));
ipcMain.handle('taches:changer', (_e, id, champs) => projet && taches.changer(projet, id, champs));
ipcMain.handle('taches:supprimer', (_e, id) => projet && taches.supprimer(projet, id));

app.whenReady().then(creerFenetre);
app.on('window-all-closed', () => app.quit());
