// Mises à jour de Janova par elle-même (fichier protégé).
// La version qui tourne est une copie installée à part : modifier le code du dépôt ne la change pas.
// Une nouvelle version est construite, testée, puis installée seulement après le oui de l'utilisateur ;
// la précédente reste gardée pour revenir en arrière en un clic.
const { execFile } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');
const projets = require('./projets');
const taches = require('./taches');
const { BRANCHE, touchesProtegees } = require('./garde-fous');

const VERSIONS = path.join(projets.DONNEES, 'versions');
const ACTUELLE = path.join(projets.DONNEES, 'actuelle');
const PRECEDENTE = path.join(projets.DONNEES, 'precedente');
const SECOURS = path.join(projets.DONNEES, 'revenir-version-precedente.sh');
const GARDER = 3; // nombre de versions gardées sur le disque
const NODE_BIN = path.dirname(process.env.JANOVA_NODE || path.join(os.homedir(), '.local', 'opt', 'node', 'bin', 'node'));
const ENV = { ...projets.ENV_GIT, PATH: `${NODE_BIN}:${path.join(os.homedir(), '.local', 'bin')}:${process.env.PATH}` };

const depot = () => (projets.trouver('gh-janova') || { dossier: path.join(projets.RACINE, 'Janova') }).dossier;

function lancer(cmd, args, opts = {}) {
  return new Promise((resolve, reject) => {
    const p = execFile(cmd, args, { env: ENV, maxBuffer: 1 << 26, ...opts }, (err, out, errOut) =>
      err ? reject(new Error((errOut || out || err.message).toString().trim().slice(-1500))) : resolve(out.toString().trim()));
    if (opts.surSortie) {
      p.stdout.on('data', (b) => opts.surSortie(b.toString()));
      p.stderr.on('data', (b) => opts.surSortie(b.toString()));
    }
  });
}
const git = (...args) => lancer('git', args, { cwd: depot() });

function meta(lien) {
  try {
    return JSON.parse(fs.readFileSync(path.join(fs.realpathSync(lien), 'version.json'), 'utf8'));
  } catch {
    return null;
  }
}
const electronActuel = () => path.join(ACTUELLE, 'node_modules', 'electron', 'dist', 'electron');

async function existe(ref) {
  try { await git('rev-parse', '--verify', '-q', ref + '^{commit}'); return true; } catch { return false; }
}

// Changements du bureau et du noyau entre la version installée et une branche du dépôt.
async function changementsDepuis(installee, ref) {
  const plage = installee && (await existe(installee)) ? `${installee}..${ref}` : ref;
  const sujets = (await git('log', '--format=%s', '-n', '30', plage, '--', 'bureau/', 'janova/')).split('\n').filter(Boolean);
  const fichiers = installee && (await existe(installee))
    ? (await git('diff', '--name-only', installee, ref)).split('\n').filter(Boolean)
    : [];
  return { sujets, gardeFous: touchesProtegees(fichiers) };
}

async function etat(refs = [BRANCHE, 'main']) {
  const installee = meta(ACTUELLE);
  const precedente = meta(PRECEDENTE);
  let candidat = null;
  if (fs.existsSync(path.join(depot(), '.git'))) {
    for (const ref of refs) {
      if (!(await existe(ref))) continue;
      const sha = await git('rev-parse', ref);
      if (installee && installee.sha === sha) continue;
      const { sujets, gardeFous } = await changementsDepuis(installee && installee.sha, ref);
      if (sujets.length) { candidat = { ref, sha, changements: sujets, gardeFous }; break; }
    }
  }
  return { installee, precedente, candidat };
}

function tacheEnCours() {
  return projets.liste().filter((p) => p.present).some((p) => taches.lire(p).some((t) => t.statut === 'en_cours'));
}

// Construit et teste la nouvelle version, sans encore l'installer.
async function preparer(progres = () => {}, refs) {
  const { candidat, installee } = await etat(refs);
  if (!candidat) throw new Error('Janova est déjà à jour.');
  const nom = new Date().toISOString().slice(0, 16).replace(/[-:]/g, '').replace('T', '-') + '-' + candidat.sha.slice(0, 7);
  const dossier = path.join(VERSIONS, nom);
  const prep = path.join(VERSIONS, '.preparation');
  fs.rmSync(prep, { recursive: true, force: true });
  fs.mkdirSync(prep, { recursive: true });
  try {
    progres('Copie de la nouvelle version…');
    const archive = path.join(VERSIONS, '.archive.tar');
    await git('archive', '-o', archive, candidat.sha, 'bureau');
    await lancer('tar', ['-xf', archive, '--strip-components=1', '-C', prep]);
    // Le noyau Janova voyage avec le bureau : il sert de première couche du cerveau.
    fs.mkdirSync(path.join(prep, 'noyau'));
    await git('archive', '-o', archive, candidat.sha, 'janova');
    await lancer('tar', ['-xf', archive, '-C', path.join(prep, 'noyau')]);
    fs.rmSync(archive, { force: true });

    const ancienne = installee && path.join(fs.realpathSync(ACTUELLE));
    const memeBriques = ancienne && fs.existsSync(path.join(ancienne, 'node_modules')) &&
      fs.readFileSync(path.join(ancienne, 'package-lock.json'), 'utf8') === fs.readFileSync(path.join(prep, 'package-lock.json'), 'utf8');
    if (memeBriques) {
      progres('Reprise des briques de la version actuelle…');
      await lancer('cp', ['-a', path.join(ancienne, 'node_modules'), prep]);
    } else {
      progres('Installation des briques (quelques minutes)…');
      await lancer('npm', ['ci', '--no-audit', '--no-fund'], { cwd: prep });
      await lancer('node', ['node_modules/electron/install.js'], { cwd: prep });
      await lancer('npx', ['electron-rebuild', '-f', '-w', 'node-pty'], { cwd: prep });
    }

    progres('Tests…');
    await lancer('npm', ['test'], { cwd: prep });
    progres('Essai de la fenêtre…');
    const out = await lancer(path.join(prep, 'node_modules', 'electron', 'dist', 'electron'), [prep, '--autotest'], { cwd: prep });
    if (!out.includes('AUTOTEST OK')) throw new Error(out.slice(-800));

    fs.writeFileSync(path.join(prep, 'version.json'), JSON.stringify({
      nom, sha: candidat.sha, ref: candidat.ref, creee: new Date().toISOString(), changements: candidat.changements,
    }, null, 2));
    fs.renameSync(prep, dossier);
    progres('Prête.');
    return { version: nom, ...candidat };
  } catch (e) {
    fs.rmSync(prep, { recursive: true, force: true });
    throw new Error('La nouvelle version ne passe pas les tests, elle n\'est pas installée. Détail : ' + e.message);
  }
}

function pointer(lien, cible) {
  const tmp = lien + '.tmp';
  fs.rmSync(tmp, { force: true });
  fs.symlinkSync(cible, tmp);
  fs.renameSync(tmp, lien);
}

// Script de secours : revenir à la version précédente même si Janova ne s'ouvre plus.
function ecrireSecours() {
  fs.writeFileSync(SECOURS, `#!/bin/bash
# Revient à la version précédente de Janova (secours, si la version actuelle ne s'ouvre plus).
cd "${projets.DONNEES}" || exit 1
[ -L precedente ] || { notify-send "Janova" "Aucune version précédente gardée."; exit 1; }
a=$(readlink actuelle); p=$(readlink precedente)
ln -sfn "$p" actuelle.tmp && mv -T actuelle.tmp actuelle
ln -sfn "$a" precedente.tmp && mv -T precedente.tmp precedente
systemctl --user restart janova-taches
notify-send "Janova" "Retour à la version précédente."
exec "${electronActuel()}" "${ACTUELLE}"
`, { mode: 0o755 });
}

async function redemarrerService() {
  await lancer('systemctl', ['--user', 'restart', 'janova-taches']).catch(() => {});
}

// Installe une version préparée (après le oui de l'utilisateur).
async function installer(nom) {
  const dossier = path.join(VERSIONS, path.basename(nom));
  const m = meta(dossier);
  if (!m) throw new Error('Version introuvable, prépare-la à nouveau.');
  if (tacheEnCours()) throw new Error('Une tâche est en cours. Attends qu\'elle se termine, puis réessaie.');

  // Le travail validé rejoint la version principale du dépôt, puis GitHub.
  if (m.ref === BRANCHE) {
    const branche = await git('rev-parse', '--abbrev-ref', 'HEAD');
    if (branche !== 'main' || (await git('status', '--porcelain'))) {
      throw new Error('Le dépôt Janova a des modifications en cours ou n\'est pas sur sa version principale. Enregistre-les d\'abord.');
    }
    try {
      await git('merge', '--no-edit', m.sha);
    } catch (e) {
      await git('merge', '--abort').catch(() => {});
      throw new Error('Les changements ne s\'assemblent pas avec la version principale. Demande à Claude de les reprendre.');
    }
    await git('push', 'origin', 'main').catch(() => {});
  }

  if (fs.existsSync(ACTUELLE)) pointer(PRECEDENTE, fs.readlinkSync(ACTUELLE));
  pointer(ACTUELLE, dossier);
  ecrireSecours();
  nettoyer();
  await redemarrerService();
}

async function revenir() {
  if (!meta(PRECEDENTE)) throw new Error('Aucune version précédente gardée.');
  if (tacheEnCours()) throw new Error('Une tâche est en cours. Attends qu\'elle se termine, puis réessaie.');
  const a = fs.readlinkSync(ACTUELLE);
  pointer(ACTUELLE, fs.readlinkSync(PRECEDENTE));
  pointer(PRECEDENTE, a);
  await redemarrerService();
}

// Garde les versions les plus récentes, et toujours l'actuelle et la précédente.
function nettoyer() {
  const gardees = new Set([ACTUELLE, PRECEDENTE].filter((l) => fs.existsSync(l)).map((l) => fs.realpathSync(l)));
  const noms = fs.readdirSync(VERSIONS).filter((n) => !n.startsWith('.')).sort().reverse();
  noms.slice(GARDER).map((n) => path.join(VERSIONS, n)).filter((d) => !gardees.has(d))
    .forEach((d) => fs.rmSync(d, { recursive: true, force: true }));
}

module.exports = { VERSIONS, ACTUELLE, PRECEDENTE, SECOURS, etat, preparer, installer, revenir, electronActuel, ecrireSecours, pointer };
