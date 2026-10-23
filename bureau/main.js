const { app, BrowserWindow, ipcMain, session, powerMonitor, shell } = require('electron');
const path = require('path');
const os = require('os');
const fs = require('fs');
const pty = require('node-pty');
const projets = require('./lib/projets');
const taches = require('./lib/taches');
const discussions = require('./lib/discussions');
const miseAJour = require('./lib/mise-a-jour');
const memoire = require('./lib/memoire');
const journal = require('./lib/journal');
const deploiement = require('./lib/deploiement');
const voix = require('./lib/voix');
const reflexes = require('./lib/reflexes');
const curiosite = require('./lib/curiosite');
const { liens } = require('./lib/liens');
const { sujetTelephone } = require('./lib/notifier');
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
puis demande : « Est-ce que je crée ce projet ? » Janova crée alors le dossier et un dépôt GitHub privé.

Pour mettre un projet en ligne, l'utilisateur utilise le bouton « Mettre en ligne » en haut : Janova lui montre ce qui va partir, attend son feu vert, puis s'en occupe. Ne propose jamais de tâche Claude Code qui déploie.
Si le projet n'a pas encore de destination de mise en ligne, tu peux en proposer une, exactement sous cette forme :
\`\`\`janova-destination
{"id": "court-sans-espace", "nom": "nom simple", "depot": "dépôt concerné", "type": "vercel | vps | android | autre", "description": "ce qui sera mis en ligne, en mots simples", "verification": "adresse à vérifier", "instructions": "étapes précises pour Claude Code : construire, mettre en ligne, garder la version précédente, vérifier", "retour": "étapes précises pour remettre la version précédente"}
\`\`\`
puis demande : « J'enregistre cette destination ? »`;

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
  const destinations = deploiement.destinations(projet).map((d) => `- ${d.nom} (${d.type})`).join('\n');
  return CONSIGNE_COMMUNE + `

Projet actuel : ${projet.nom}, dans ${projet.dossier}. ${depots}${soiMeme}

Mémoire du projet (ce qui a été fait, ce qui reste, les décisions) :
${memoire.contexteCourt(projet)}

Destinations de mise en ligne déjà connues : ${destinations ? '\n' + destinations : 'aucune.'}

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
let surveillanceCuriosite = null; // la curiosité (recherches quand l'ordinateur est inactif)

function creerFenetre() {
  fenetre = new BrowserWindow({
    width: 1500,
    height: 900,
    title: 'Janova',
    icon: path.join(__dirname, 'icone.png'),
    backgroundColor: '#16181d',
    autoHideMenuBar: true,
    show: !process.argv.includes('--autotest'),
    webPreferences: { preload: path.join(__dirname, 'preload.js'), webviewTag: true },
  });
  // Les fenêtres web (GitHub, Vercel…) n'ont accès à rien de Janova : pas de préchargement, pas de Node.
  fenetre.webContents.on('will-attach-webview', (_e, prefs, params) => {
    delete prefs.preload;
    prefs.nodeIntegration = false;
    prefs.contextIsolation = true;
    if (!/^https:\/\//.test(params.src || '')) _e.preventDefault();
  });
  fenetre.loadFile('index.html');
  // La fenêtre de Janova ne quitte jamais sa page : un lien s'ouvre dans le navigateur, pas ici.
  fenetre.webContents.on('will-navigate', (e) => e.preventDefault());
  fenetre.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
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
  discussion = discussions.nouvelle(p && p.id);
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
  enregistrerDiscussion(discussion);
});

// --- Chat avec le cerveau ---
const nomProjet = (d) => { const p = d.projet && projets.trouver(d.projet); return p ? p.nom : null; };
const enregistrerDiscussion = (d) => discussions.enregistrer(d, nomProjet(d));

ipcMain.on('chat:envoyer', async (_e, message) => {
  if (chat || !discussion) return;
  const d = discussion;
  const p = d.projet ? projets.trouver(d.projet) : null;
  if (!d.messages.length) d.titre = message.replace(/\s+/g, ' ').slice(0, 70);
  d.messages.push({ role: 'moi', texte: message });
  const reponse = { role: 'claude', texte: '' };
  d.messages.push(reponse);
  // Ce qu'il faut savoir ensuite pour décider si la réponse peut devenir un réflexe.
  const avant = { session: d.session, contexte: d.horsClaude || [], outils: false };

  chat = cerveau.discuter(
    {
      message,
      session: d.session,
      dossier: p && p.present ? p.dossier : os.homedir(),
      consigne: consigneChat(p),
      contexte: d.horsClaude || [],
    },
    {
      surTexte: (t) => { reponse.texte += t; envoyer('chat:texte', t); },
      surNouveauMessage: () => {
        if (reponse.texte && !reponse.texte.endsWith('\n\n')) reponse.texte += '\n\n';
        envoyer('chat:nouveau-message');
      },
      surOutil: (nom) => { avant.outils = true; envoyer('chat:outil', nom); },
    },
  );
  const { session, erreur, couche, niveaux } = await chat.fin;
  chat = null;
  d.session = session;
  if (couche) reponse.couche = couche;
  if (niveaux) reponse.niveaux = niveaux;
  // Ce que le noyau a répondu seul est redonné à Claude la fois suivante, pour qu'il garde le fil.
  if (couche === 'noyau') d.horsClaude = [...(d.horsClaude || []), { question: message, reponse: reponse.texte }];
  if (couche === 'claude' && !erreur) d.horsClaude = [];
  // Une réponse de Claude qui tient seule peut être retenue par le noyau, si l'utilisateur le veut.
  if (couche === 'claude' && !erreur && reflexes.peutRetenir({ question: message, reponse: reponse.texte, ...avant })) {
    reponse.retenable = true;
  }
  if (!reponse.texte) d.messages.pop();
  else memoire.noterEchange({ projet: d.projet, discussion: d.id, question: message, reponse: reponse.texte, couche });
  enregistrerDiscussion(d);
  envoyer('chat:fin', erreur, couche, !!reponse.retenable);
});
ipcMain.on('chat:stop', () => chat && chat.arreter());
// « Retenir » : le noyau apprend la réponse de Claude, pour répondre seul la prochaine fois.
ipcMain.handle('chat:retenir', async (_e, index) => {
  const d = discussion;
  const m = d && d.messages[index];
  const q = d && d.messages[index - 1];
  if (!m || !m.retenable || !q || q.role !== 'moi') return { appris: false, erreur: 'Cette réponse ne peut pas être retenue.' };
  const r = await reflexes.retenir(q.texte, m.texte);
  if (r.appris) { m.retenu = true; enregistrerDiscussion(d); }
  return r;
});

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
// Depuis la fenêtre, on ne peut que cocher, décocher ou relancer une tâche : jamais donner un feu vert.
ipcMain.handle('taches:changer', (_e, id, { cochee, relancer }) => {
  if (!projet) return;
  const t = taches.lire(projet).find((x) => x.id === id);
  if (!t || t.type) return;
  const champs = { cochee: !!cochee };
  if (relancer && (t.statut === 'echec' || t.statut === 'bloquee')) Object.assign(champs, { statut: 'en_attente', resultat: null });
  return taches.changer(projet, id, champs);
});
ipcMain.handle('taches:annuler', (_e, id) => {
  const t = projet && taches.lire(projet).find((x) => x.id === id);
  if (t && t.statut === 'terminee' && !t.type && !t.annulation) return taches.changer(projet, id, { annulation: 'demandee' });
});
ipcMain.handle('taches:supprimer', (_e, id) => projet && taches.supprimer(projet, id));

// Les fenêtres web gardent tes connexions d'une fois sur l'autre. Elles se présentent comme un navigateur
// ordinaire, sinon Google refuse la connexion à la Play Console.
function preparerSessions() {
  const web = session.fromPartition('persist:web');
  web.setUserAgent(web.getUserAgent().replace(/\s*(Electron|janova-bureau)\/\S+/g, ''));
  // Le micro n'est permis que pour la fenêtre de Janova (dictée), jamais pour les sites.
  session.defaultSession.setPermissionRequestHandler((wc, permission, rappel) => rappel(permission === 'media' && wc === (fenetre && fenetre.webContents)));
  web.setPermissionRequestHandler((_wc, permission, rappel) => rappel(permission === 'clipboard-sanitized-write'));
}

app.whenReady().then(() => {
  preparerSessions();
  memoire.lisezMoi();
  for (const p of projets.liste()) memoire.noteProjet(p);
  creerFenetre();
  // Curiosité : une recherche gratuite (sans Claude) quand l'ordinateur est inactif. Jamais pendant l'autotest.
  if (!process.argv.includes('--autotest')) {
    surveillanceCuriosite = curiosite.surveiller({
      inactiviteS: () => powerMonitor.getSystemIdleTime(),
      tacheEnCours: () => !!journal.historique().enCours,
      surEvenement: (e) => envoyer('curiosite:evenement', e),
    });
  }
});
app.on('window-all-closed', () => app.quit());

// --- Notes et mémoire du projet ---
ipcMain.handle('notes:lire', () => projet && { notes: memoire.lireNotes(projet), contexte: memoire.lireContexte(projet) });
ipcMain.handle('notes:ecrire', (_e, { notes, contexte }) => {
  if (!projet) return;
  if (typeof notes === 'string') memoire.ecrireNotes(projet, notes);
  if (typeof contexte === 'string') memoire.ecrireContexte(projet, contexte);
});

// --- Journal en direct ---
ipcMain.handle('journal:historique', () => journal.historique());
ipcMain.handle('journal:lire', (_e, { fichier, position }) => {
  // On ne lit que les journaux de Janova.
  const dossier = path.join(projets.ETAT, 'journaux');
  if (!fichier || path.dirname(path.resolve(fichier)) !== dossier) return { lignes: [], position: 0 };
  return journal.lireDepuis(fichier, position);
});

// --- Outils web du projet ---
ipcMain.handle('liens:lire', () => liens(projet));

// --- Mise en ligne ---
ipcMain.handle('deploiement:destinations', () => (projet ? deploiement.destinations(projet).map((d) => ({
  id: d.id, nom: d.nom, type: d.type, derniere: deploiement.derniere(projet, d.id),
})) : []));
ipcMain.handle('deploiement:resume', erreurs((id) => deploiement.resume(projet, id)));
ipcMain.handle('deploiement:feu-vert', erreurs(({ id, retour }) => deploiement.feuVert(projet, id, { retour })));
ipcMain.handle('deploiement:enregistrer', erreurs((d) => {
  if (!projet) throw new Error('Aucun projet ouvert.');
  if (!d || !/^[a-z0-9-]{1,40}$/.test(d.id || '') || !d.nom || !d.instructions) throw new Error('Destination incomplète.');
  const f = memoire.chemin('projets', projet.id, 'deploiement.json');
  const c = memoire.lireJson(f, { destinations: [] });
  c.destinations = [...(c.destinations || []).filter((x) => x.id !== d.id), d];
  memoire.ecrireJson(f, c);
  return true;
}));

// --- Curiosité : l'onglet « Recherche » ---
ipcMain.handle('curiosite:etat', async () => ({
  reglages: curiosite.reglages(),
  enCours: surveillanceCuriosite && surveillanceCuriosite.etat.enCours,
  decouvertes: curiosite.decouvertes(30),
  sujets: await curiosite.sujets().catch(() => []),
}));
ipcMain.handle('curiosite:activer', (_e, oui) => { curiosite.activer(oui); return curiosite.reglages(); });
ipcMain.handle('curiosite:ecarter', erreurs((nom) => curiosite.ecarter(nom)));
ipcMain.handle('curiosite:suggerer', erreurs((nom) => curiosite.suggerer(nom)));
// « Chercher maintenant » : même règle qu'en automatique pour les tâches, une recherche à la fois.
ipcMain.handle('curiosite:chercher', () => {
  if (!surveillanceCuriosite || surveillanceCuriosite.etat.enCours) return false;
  if (journal.historique().enCours) return false;
  surveillanceCuriosite.essayer(true).catch(() => {});
  return true;
});
// Les liens des découvertes s'ouvrent dans le navigateur par défaut (adresses web seulement).
ipcMain.handle('liens:ouvrir', (_e, adresse) => {
  if (typeof adresse === 'string' && /^https?:\/\/[^\s]+$/.test(adresse)) shell.openExternal(adresse);
});

// --- Commande vocale et téléphone ---
ipcMain.handle('voix:disponible', () => voix.disponible());
ipcMain.handle('voix:transcrire', erreurs((wav) => voix.transcrire(wav)));
ipcMain.handle('telephone:sujet', () => sujetTelephone().sujet);
