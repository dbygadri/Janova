// La mémoire unique de Janova : un seul dossier, indépendant de la machine, fait de fichiers simples.
// Il pourra plus tard se synchroniser entre le ThinkPad, le VPS, le téléphone…
//
//   projets.json            les projets (chemins relatifs au dossier des projets de chaque machine)
//   github.json             les dépôts GitHub connus
//   projets/<id>/           par projet : taches.json, contexte.md (fait, reste, décisions), notes.md,
//                           deploiement.json (où le mettre en ligne) et une note <Nom>.md (centre du graphe)
//   discussions/<id>.json   chaque discussion, avec sa copie lisible <id>.md reliée à son projet
//   echanges/<mois>.jsonl   chaque question posée à un cerveau et sa réponse : de quoi apprendre
//   noyau/                  ce que le noyau Janova a appris (réflexes, organes, idées)
//   reglages.json           réglages communs (notifications…)
//
// Ce qui est propre à une machine (versions installées, journaux, dernier projet ouvert) reste à part.
const fs = require('fs');
const path = require('path');
const os = require('os');

const MEMOIRE = process.env.JANOVA_MEMOIRE || path.join(os.homedir(), 'Janova-memoire');

function lireJson(f, defaut) {
  try { return JSON.parse(fs.readFileSync(f, 'utf8')); } catch { return defaut; }
}

function ecrire(f, contenu) {
  fs.mkdirSync(path.dirname(f), { recursive: true });
  const tmp = f + '.' + process.pid + '.tmp';
  fs.writeFileSync(tmp, contenu);
  fs.renameSync(tmp, f);
}
const ecrireJson = (f, d) => ecrire(f, JSON.stringify(d, null, 2) + '\n');

const chemin = (...parties) => path.join(MEMOIRE, ...parties);
const nomDeFichier = (s) => String(s).replace(/[\/\\:*?"<>|]/g, '-').trim() || 'sans-nom';

// Garde la trace de chaque échange avec un cerveau, pour que le noyau apprenne.
function noterEchange({ projet, discussion, question, reponse, couche }) {
  const f = chemin('echanges', new Date().toISOString().slice(0, 7) + '.jsonl');
  fs.mkdirSync(path.dirname(f), { recursive: true });
  fs.appendFileSync(f, JSON.stringify({ date: new Date().toISOString(), projet, discussion, couche, question, reponse }) + '\n');
}

// La note d'un projet : le point où se rejoignent ses discussions dans le graphe.
function noteProjet(p) {
  const f = chemin('projets', p.id, nomDeFichier(p.nom) + '.md');
  if (fs.existsSync(f)) return;
  const depots = p.depots.length > 1 ? `\nDépôts : ${p.depots.join(', ')}\n` : '';
  ecrire(f, `# ${p.nom}\n\nProjet suivi par Janova.\n${depots}`);
}

function lisezMoi() {
  const f = chemin('LISEZ-MOI.md');
  if (fs.existsSync(f)) return;
  ecrire(f, `# Mémoire de Janova

Tout ce que Janova sait est rangé ici, dans des fichiers simples.
Ce dossier ne dépend pas de la machine : c'est la même mémoire partout où Janova vivra.
Il s'ouvre aussi dans Obsidian, pour voir les discussions reliées à leurs projets.
`);
}

// --- Contexte d'un projet : ce qui a été fait, ce qui reste, les décisions prises. ---
// Relu par Claude Code au début de chaque tâche, et par le chat, pour ne jamais repartir de zéro.
const SECTIONS = ['Décisions', 'Reste à faire', 'Fait'];
const fichierContexte = (p) => chemin('projets', p.id, 'contexte.md');

function lireContexte(p) {
  try { return fs.readFileSync(fichierContexte(p), 'utf8'); } catch { return `# Contexte : ${p.nom}\n\n## Décisions\n\n## Reste à faire\n\n## Fait\n`; }
}

function sections(texte) {
  const res = { tete: '', parties: {} };
  let actuelle = null;
  for (const ligne of texte.split('\n')) {
    const m = ligne.match(/^## (.+)$/);
    if (m) { actuelle = m[1].trim(); res.parties[actuelle] = []; continue; }
    if (actuelle) res.parties[actuelle].push(ligne);
    else res.tete += ligne + '\n';
  }
  return res;
}

function assembler({ tete, parties }) {
  const noms = [...SECTIONS, ...Object.keys(parties).filter((n) => !SECTIONS.includes(n))];
  return tete.trimEnd() + '\n\n' + noms.map((n) => `## ${n}\n${(parties[n] || []).join('\n').trim()}\n`).join('\n');
}

// Après une tâche : ajoute ce qui a été fait et les décisions, remplace « reste à faire » si la tâche le précise.
function mettreAJourContexte(p, { fait, decisions = [], reste = null }) {
  const c = sections(lireContexte(p));
  for (const n of SECTIONS) c.parties[n] = c.parties[n] || [];
  const jour = new Date().toISOString().slice(0, 10);
  if (fait) c.parties['Fait'] = [`- ${jour} : ${fait}`, ...c.parties['Fait'].filter((l) => l.trim())];
  for (const d of decisions) c.parties['Décisions'].push(`- ${jour} : ${d}`);
  if (reste) c.parties['Reste à faire'] = reste.map((l) => `- ${l}`);
  ecrire(fichierContexte(p), assembler(c));
}

// Version courte pour les consignes : les 25 dernières choses faites suffisent.
function contexteCourt(p) {
  const c = sections(lireContexte(p));
  if (c.parties['Fait']) c.parties['Fait'] = c.parties['Fait'].filter((l) => l.trim()).slice(0, 25);
  return assembler(c);
}

const lireTexte = (f) => { try { return fs.readFileSync(f, 'utf8'); } catch { return ''; } };
const lireNotes = (p) => lireTexte(chemin('projets', p.id, 'notes.md'));
const ecrireNotes = (p, texte) => ecrire(chemin('projets', p.id, 'notes.md'), texte);
const ecrireContexte = (p, texte) => ecrire(fichierContexte(p), texte);

const reglages = () => lireJson(chemin('reglages.json'), {});
const changerReglages = (champs) => ecrireJson(chemin('reglages.json'), { ...reglages(), ...champs });

module.exports = {
  MEMOIRE, chemin, lireJson, ecrire, ecrireJson, nomDeFichier, noterEchange, noteProjet, lisezMoi,
  lireContexte, ecrireContexte, mettreAJourContexte, contexteCourt, lireNotes, ecrireNotes, reglages, changerReglages,
};
