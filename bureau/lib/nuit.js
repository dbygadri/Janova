// Tâches de nuit et compte rendu du matin : la logique, sans effet tant que l'exécuteur ne s'en sert pas.
// Une « nuit » va de 23:00 à 07:00 (heure locale) ; elle porte la date du soir où elle commence.
// L'heure est toujours fournie en paramètre, pour que les tests ne dépendent pas de l'heure réelle.
const fs = require('fs');
const memoire = require('./memoire');

const DEBUT = 23;
const FIN = 7;
const LIMITE_PAR_DEFAUT = 3;
const STATUTS = { terminee: 'terminée', echec: 'en échec', bloquee: 'bloquée' };

const jour = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

const estLaNuit = (date) => date.getHours() >= DEBUT || date.getHours() < FIN;

// La nuit à laquelle appartient un instant (null en journée) : la date du soir, AAAA-MM-JJ.
function nuitDe(date) {
  if (!estLaNuit(date)) return null;
  const soir = new Date(date);
  if (date.getHours() < FIN) soir.setDate(soir.getDate() - 1);
  return jour(soir);
}

// La nuit qui vient de se terminer, vue depuis le matin (07:00 ou plus tard le même jour).
function nuitPassee(date) {
  const veille = new Date(date);
  veille.setDate(veille.getDate() - 1);
  return jour(veille);
}

// Réglage simple, dans la mémoire unique : combien de tâches de nuit au plus par nuit.
function limite() {
  const n = Number(memoire.reglages().taches_de_nuit_max);
  return Number.isInteger(n) && n >= 0 ? n : LIMITE_PAR_DEFAUT;
}

// Les tâches de nuit parties pendant une nuit donnée (d'après leur heure de début).
const parties = (taches, nuit) => taches.filter((t) => t.nuit && t.debut && nuitDe(new Date(t.debut)) === nuit);

// Une tâche cochée peut-elle partir maintenant ? Sans « nuit » : tout de suite, comme avant.
// Avec « nuit » : seulement la nuit, et tant que la limite de la nuit n'est pas atteinte.
function peutPartir(t, date, dejaParties, max = limite()) {
  if (!t.cochee || t.statut !== 'en_attente') return false;
  if (!t.nuit) return true;
  return estLaNuit(date) && dejaParties < max;
}

// Texte du compte rendu, en français simple. entrees : [{ projet, tache }].
function rediger(nuit, entrees, aValider = []) {
  const titre = new Date(nuit + 'T12:00:00');
  titre.setDate(titre.getDate() + 1);
  const lignes = [`# Compte rendu du matin : ${jour(titre)}`, '', `Cette nuit, Janova a travaillé sur ${entrees.length} tâche${entrees.length > 1 ? 's' : ''}.`, ''];
  for (const { projet, tache } of entrees) {
    lignes.push(`## ${tache.titre} (${projet})`, '', `Statut : ${STATUTS[tache.statut] || tache.statut}`, '', String(tache.resultat || 'Aucun résumé noté.').trim(), '');
  }
  const bloquees = entrees.filter(({ tache }) => tache.statut === 'bloquee');
  lignes.push('## Ce qui attend ton avis', '');
  if (!bloquees.length && !aValider.length) lignes.push('Rien pour le moment.');
  for (const { projet, tache } of bloquees) lignes.push(`- Tâche bloquée : ${tache.titre} (${projet})`);
  for (const a of aValider) lignes.push(`- À valider : ${a}`);
  return lignes.join('\n') + '\n';
}

const fichier = (date) => memoire.chemin('comptes-rendus', jour(date) + '.md');

// À partir de 07:00, écrit une seule fois le compte rendu de la nuit passée, s'il y a eu des tâches de nuit.
// Rend le chemin du fichier écrit, ou null s'il n'y avait rien à écrire.
function ecrireSiBesoin(date, projetsEtTaches, aValider = []) {
  if (estLaNuit(date)) return null;
  const f = fichier(date);
  if (fs.existsSync(f)) return null;
  const nuit = nuitPassee(date);
  const entrees = projetsEtTaches.flatMap(({ projet, taches }) => parties(taches, nuit).map((tache) => ({ projet, tache })));
  if (!entrees.length) return null;
  memoire.ecrire(f, rediger(nuit, entrees, aValider));
  return f;
}

// Pour le bureau : le compte rendu du jour s'il n'a pas encore été lu.
function nonLu(date) {
  const f = fichier(date);
  if (!fs.existsSync(f)) return null;
  if ((memoire.reglages().comptes_rendus_lus || []).includes(jour(date))) return null;
  return { jour: jour(date), texte: fs.readFileSync(f, 'utf8') };
}

function marquerLu(j) {
  const lus = memoire.reglages().comptes_rendus_lus || [];
  if (!lus.includes(j)) memoire.changerReglages({ comptes_rendus_lus: [...lus, j].slice(-60) });
}

module.exports = {
  LIMITE_PAR_DEFAUT, estLaNuit, nuitDe, nuitPassee, limite, parties, peutPartir, rediger, ecrireSiBesoin, nonLu, marquerLu,
};
