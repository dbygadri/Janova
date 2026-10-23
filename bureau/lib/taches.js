// Lecture et écriture de la liste de tâches d'un projet (<dossier du projet>/.janova/taches.json),
// partagée par l'appli et l'exécuteur.
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const fichier = (projet) => path.join(projet.dossier, '.janova', 'taches.json');

function lire(projet) {
  try {
    const d = JSON.parse(fs.readFileSync(fichier(projet), 'utf8'));
    return Array.isArray(d.taches) ? d.taches : [];
  } catch {
    return [];
  }
}

function ecrire(projet, taches) {
  const f = fichier(projet);
  fs.mkdirSync(path.dirname(f), { recursive: true });
  const tmp = f + '.' + process.pid + '.tmp';
  fs.writeFileSync(tmp, JSON.stringify({ taches }, null, 2) + '\n');
  fs.renameSync(tmp, f);
}

// Relit le fichier juste avant de le modifier, pour ne pas écraser les changements de l'autre programme.
function modifier(projet, fn) {
  const taches = lire(projet);
  const res = fn(taches);
  ecrire(projet, taches);
  return res;
}

function ajouter(projet, { titre, dossier, instructions, cochee }) {
  return modifier(projet, (taches) => {
    const t = {
      id: crypto.randomBytes(4).toString('hex'),
      titre: String(titre || '').trim() || 'Sans titre',
      dossier: projet.groupe ? dossier || '' : '',
      instructions: String(instructions || titre || '').trim(),
      cochee: !!cochee,
      statut: 'en_attente',
      creee: new Date().toISOString(),
    };
    taches.push(t);
    return t;
  });
}

function changer(projet, id, champs) {
  return modifier(projet, (taches) => {
    const t = taches.find((x) => x.id === id);
    if (t) Object.assign(t, champs);
    return t;
  });
}

function supprimer(projet, id) {
  modifier(projet, (taches) => {
    const i = taches.findIndex((x) => x.id === id);
    if (i >= 0) taches.splice(i, 1);
  });
}

module.exports = { fichier, lire, ajouter, changer, supprimer };
