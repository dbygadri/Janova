// La mémoire unique de Janova : un seul dossier, indépendant de la machine, fait de fichiers simples.
// Il pourra plus tard se synchroniser entre le ThinkPad, le VPS, le téléphone…
//
//   projets.json            les projets (chemins relatifs au dossier des projets de chaque machine)
//   github.json             les dépôts GitHub connus
//   projets/<id>/           par projet : taches.json et une note <Nom>.md (le centre du graphe du projet)
//   discussions/<id>.json   chaque discussion, avec sa copie lisible <id>.md reliée à son projet
//   echanges/<mois>.jsonl   chaque question posée à un cerveau et sa réponse : de quoi apprendre
//   noyau/                  ce que le noyau Janova a appris (réflexes, organes, idées)
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

module.exports = { MEMOIRE, chemin, lireJson, ecrire, ecrireJson, nomDeFichier, noterEchange, noteProjet, lisezMoi };
