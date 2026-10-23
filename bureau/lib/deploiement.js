// Mise en ligne des projets (fichier protégé).
// Chaque projet décrit ses destinations dans la mémoire (projets/<id>/deploiement.json) :
//   { "destinations": [{ id, nom, depot, type: "vercel" | "vps" | "android" | "autre",
//                        description, verification, instructions, retour }] }
// Rien ne part en ligne sans le feu vert de l'utilisateur : c'est lui qui crée la tâche de déploiement,
// après avoir lu en mots simples ce qui va être mis en ligne. L'historique garde chaque version mise en ligne.
const { execFileSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const memoire = require('./memoire');
const projets = require('./projets');
const taches = require('./taches');
const { BRANCHE } = require('./garde-fous');

const config = (p) => memoire.lireJson(memoire.chemin('projets', p.id, 'deploiement.json'), { destinations: [] });
const destinations = (p) => config(p).destinations || [];
const destination = (p, id) => destinations(p).find((d) => d.id === id) || null;

const fichierHistorique = (p) => memoire.chemin('projets', p.id, 'deploiements.json');
const historique = (p) => memoire.lireJson(fichierHistorique(p), []);
function noter(p, entree) {
  memoire.ecrireJson(fichierHistorique(p), [entree, ...historique(p)].slice(0, 200));
}
// Dernière version mise en ligne avec succès sur cette destination.
const derniere = (p, destId) => historique(p).find((h) => h.destination === destId && h.statut === 'terminee') || null;

function git(dossier, ...args) {
  try {
    return execFileSync('git', args, { cwd: dossier, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }).trim();
  } catch {
    return '';
  }
}

// Ce qui va être mis en ligne, en mots simples : les changements depuis la dernière mise en ligne.
function resume(p, destId) {
  const d = destination(p, destId);
  if (!d) throw new Error('Destination inconnue.');
  const dossier = projets.dossierDepot(p, d.depot);
  if (!fs.existsSync(path.join(dossier, '.git'))) throw new Error(`Le dépôt « ${d.depot} » n'est pas sur ce PC.`);
  const travail = git(dossier, 'rev-parse', '--verify', '-q', BRANCHE) ? BRANCHE : 'main';
  const avant = derniere(p, destId);
  const plage = avant && git(dossier, 'cat-file', '-t', avant.sha) ? `${avant.sha}..${travail}` : `-n15 ${travail}`;
  const changements = git(dossier, 'log', '--format=%s', ...plage.split(' ')).split('\n').filter(Boolean);
  const aFusionner = travail === BRANCHE ? Number(git(dossier, 'rev-list', '--count', `main..${BRANCHE}`) || 0) : 0;
  return {
    destination: d.nom,
    description: d.description,
    changements: avant ? changements : changements.slice(0, 15),
    premiere: !avant,
    aFusionner,
    precedente: avant ? { date: avant.date, sha: avant.sha.slice(0, 7) } : null,
  };
}

// Le feu vert de l'utilisateur : crée la tâche de mise en ligne (ou de retour à la version précédente).
function feuVert(p, destId, { retour = false } = {}) {
  const d = destination(p, destId);
  if (!d) throw new Error('Destination inconnue.');
  if (retour && !derniere(p, destId)) throw new Error('Aucune mise en ligne précédente connue pour revenir en arrière.');
  const occupee = taches.lire(p).find((t) => t.destination === destId && ['en_attente', 'en_cours'].includes(t.statut) && t.cochee);
  if (occupee) throw new Error('Une mise en ligne de cette destination est déjà prévue.');
  const t = taches.ajouter(p, {
    titre: (retour ? 'Revenir à la version précédente : ' : 'Mettre en ligne : ') + d.nom,
    dossier: d.depot,
    instructions: retour ? d.retour : d.instructions,
    cochee: true,
  });
  return taches.changer(p, t.id, { type: retour ? 'retour' : 'deploiement', destination: destId, feuVert: new Date().toISOString() });
}

module.exports = { destinations, destination, resume, feuVert, historique, noter, derniere };
