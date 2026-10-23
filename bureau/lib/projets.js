// Liste des projets : un projet = un dépôt GitHub, ou un groupe de dépôts (comme Alkestore).
const fs = require('fs');
const path = require('path');
const os = require('os');
const { execFile } = require('child_process');

const DONNEES = process.env.JANOVA_DONNEES || path.join(os.homedir(), '.local', 'share', 'janova-bureau');
const ETAT = process.env.JANOVA_ETAT || path.join(os.homedir(), '.local', 'state', 'janova-bureau');
const RACINE = process.env.JANOVA_RACINE || path.join(os.homedir(), 'projet');
const FICHIER = path.join(DONNEES, 'projets.json');
const CACHE_GITHUB = path.join(DONNEES, 'github.json');
const COMPTE = 'dbygadri';

const DEPART = {
  projets: [
    {
      id: 'alkestore',
      nom: 'Alkestore',
      dossier: RACINE,
      depots: ['alkestore-mvp', 'alkestore-admin', 'alkestore-landing', 'AlkeStore_mobileApp'],
    },
  ],
  dernier: 'alkestore',
};

function lireJson(f, defaut) {
  try { return JSON.parse(fs.readFileSync(f, 'utf8')); } catch { return defaut; }
}
function ecrireJson(f, d) {
  fs.mkdirSync(path.dirname(f), { recursive: true });
  const tmp = f + '.' + process.pid + '.tmp';
  fs.writeFileSync(tmp, JSON.stringify(d, null, 2) + '\n');
  fs.renameSync(tmp, f);
}

function lireConfig() {
  const c = lireJson(FICHIER, null);
  if (c) return c;
  ecrireJson(FICHIER, DEPART);
  return JSON.parse(JSON.stringify(DEPART));
}

// Les dépôts GitHub qui n'appartiennent à aucun groupe deviennent chacun un projet.
function liste() {
  const c = lireConfig();
  const pris = new Set(c.projets.flatMap((p) => p.depots.map((d) => d.toLowerCase())));
  const projets = [...c.projets];
  for (const r of lireJson(CACHE_GITHUB, [])) {
    if (pris.has(r.name.toLowerCase())) continue;
    projets.push({ id: 'gh-' + r.name.toLowerCase(), nom: r.name, dossier: path.join(RACINE, r.name), depots: [r.name] });
  }
  return projets.map((p) => ({ ...p, groupe: p.depots.length > 1, present: fs.existsSync(p.dossier) }));
}

function trouver(id) {
  return liste().find((p) => p.id === id) || null;
}

function dernier() {
  const id = lireConfig().dernier;
  return id === undefined ? 'alkestore' : id;
}
function memoriserDernier(id) {
  const c = lireConfig();
  c.dernier = id;
  ecrireJson(FICHIER, c);
}

// Dossier de travail d'un dépôt du projet (le projet lui-même s'il n'a qu'un dépôt).
function dossierDepot(p, depot) {
  return p.groupe ? path.join(p.dossier, depot || '') : p.dossier;
}

function gh(args, opts = {}) {
  return new Promise((resolve, reject) =>
    execFile('gh', args, { maxBuffer: 1 << 24, ...opts }, (err, out, errOut) =>
      err ? reject(new Error((errOut || err.message).trim())) : resolve(out)));
}
function git(dossier, args) {
  return new Promise((resolve, reject) =>
    execFile('git', args, { cwd: dossier, env: ENV_GIT }, (err, out, errOut) =>
      err ? reject(new Error((errOut || err.message).trim())) : resolve(out.trim())));
}
// git n'a pas d'identité configurée sur ce PC : on reprend celle des commits existants.
const ENV_GIT = {
  ...process.env,
  GIT_AUTHOR_NAME: COMPTE, GIT_AUTHOR_EMAIL: 'dby.perso@gmail.com',
  GIT_COMMITTER_NAME: COMPTE, GIT_COMMITTER_EMAIL: 'dby.perso@gmail.com',
};

async function actualiserGithub() {
  const out = await gh(['repo', 'list', COMPTE, '--json', 'name,isPrivate,description,url', '--limit', '500']);
  const depots = JSON.parse(out).sort((a, b) => a.name.localeCompare(b.name));
  ecrireJson(CACHE_GITHUB, depots);
  return depots;
}

// Le dossier .janova (tâches, notes) reste sur le PC : jamais envoyé sur GitHub.
function exclureDonnees(depot) {
  const f = path.join(depot, '.git', 'info', 'exclude');
  if (!fs.existsSync(path.join(depot, '.git'))) return;
  const actuel = fs.existsSync(f) ? fs.readFileSync(f, 'utf8') : '';
  if (!actuel.split('\n').includes('.janova/')) {
    fs.mkdirSync(path.dirname(f), { recursive: true });
    fs.appendFileSync(f, (actuel && !actuel.endsWith('\n') ? '\n' : '') + '.janova/\n');
  }
}

// Télécharge sur le PC les dépôts du projet qui n'y sont pas encore.
async function preparer(p) {
  fs.mkdirSync(p.dossier, { recursive: true });
  for (const d of p.depots) {
    const dossier = dossierDepot(p, d);
    if (!fs.existsSync(path.join(dossier, '.git'))) {
      if (fs.existsSync(dossier) && fs.readdirSync(dossier).length) continue;
      await gh(['repo', 'clone', `${COMPTE}/${d}`, dossier]);
    }
    exclureDonnees(dossier);
  }
}

async function creer(nom, description) {
  nom = String(nom || '').trim();
  if (!/^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$/.test(nom)) {
    throw new Error('Nom invalide : utilise seulement des lettres, des chiffres et des tirets (sans espace ni accent).');
  }
  if (liste().some((p) => p.nom.toLowerCase() === nom.toLowerCase() || p.depots.some((d) => d.toLowerCase() === nom.toLowerCase()))) {
    throw new Error('Un projet porte déjà ce nom.');
  }
  const dossier = path.join(RACINE, nom);
  if (fs.existsSync(dossier)) throw new Error(`Le dossier ${dossier} existe déjà.`);
  fs.mkdirSync(dossier, { recursive: true });
  fs.writeFileSync(path.join(dossier, 'README.md'), `# ${nom}\n${description ? '\n' + description + '\n' : ''}`);
  await git(dossier, ['init', '-q', '-b', 'main']);
  exclureDonnees(dossier);
  await git(dossier, ['add', '-A']);
  await git(dossier, ['commit', '-q', '-m', 'Création du projet']);
  const args = ['repo', 'create', `${COMPTE}/${nom}`, '--private', '--source', dossier, '--push'];
  if (description) args.push('--description', description);
  await gh(args, { env: ENV_GIT });
  await actualiserGithub().catch(() => {});
  return trouver('gh-' + nom.toLowerCase());
}

module.exports = { DONNEES, ETAT, RACINE, ENV_GIT, liste, trouver, dernier, memoriserDernier, dossierDepot, actualiserGithub, preparer, creer, exclureDonnees };
