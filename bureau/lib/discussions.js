// Historique des discussions, dans la mémoire unique : un fichier par discussion,
// et sa copie lisible en Markdown, reliée à la note de son projet (graphe façon Obsidian).
const fs = require('fs');
const crypto = require('crypto');
const memoire = require('./memoire');

const DOSSIER = memoire.chemin('discussions');
const base = (id) => memoire.chemin('discussions', String(id).replace(/[^a-z0-9]/gi, ''));

function nouvelle(projetId) {
  return {
    id: crypto.randomBytes(6).toString('hex'),
    projet: projetId || null,
    titre: 'Nouvelle discussion',
    creee: new Date().toISOString(),
    maj: new Date().toISOString(),
    session: null,
    messages: [],
  };
}

function lire(id) {
  return memoire.lireJson(base(id) + '.json', null);
}

function enMarkdown(d, nomProjet) {
  const lignes = [`# ${d.titre}`, '', `${nomProjet ? `Projet : [[${memoire.nomDeFichier(nomProjet)}]]` : 'Question générale'} · ${d.creee.slice(0, 10)}`, ''];
  for (const m of d.messages) {
    const qui = m.role === 'moi' ? 'Moi' : m.couche === 'noyau' ? 'Janova' : 'Claude';
    lignes.push(`**${qui}** : ${m.texte}`, '');
  }
  return lignes.join('\n');
}

function enregistrer(d, nomProjet) {
  if (!d.messages.length) return;
  d.maj = new Date().toISOString();
  memoire.ecrire(base(d.id) + '.json', JSON.stringify(d, null, 1));
  memoire.ecrire(base(d.id) + '.md', enMarkdown(d, nomProjet));
}

function supprimer(id) {
  fs.rmSync(base(id) + '.json', { force: true });
  fs.rmSync(base(id) + '.md', { force: true });
}

// Liste résumée, la plus récente en premier. La recherche porte sur le titre et tout le texte.
function liste({ projet, recherche } = {}) {
  let noms = [];
  try { noms = fs.readdirSync(DOSSIER).filter((n) => n.endsWith('.json')); } catch {}
  const mots = String(recherche || '').toLowerCase().split(/\s+/).filter(Boolean);
  const res = [];
  for (const n of noms) {
    const d = lire(n.slice(0, -5));
    if (!d) continue;
    if (projet !== undefined && d.projet !== projet) continue;
    if (mots.length) {
      const texte = (d.titre + ' ' + d.messages.map((m) => m.texte).join(' ')).toLowerCase();
      if (!mots.every((m) => texte.includes(m))) continue;
    }
    const dernierMsg = d.messages[d.messages.length - 1];
    res.push({ id: d.id, projet: d.projet, titre: d.titre, maj: d.maj, extrait: dernierMsg ? dernierMsg.texte.slice(0, 140) : '' });
  }
  return res.sort((a, b) => b.maj.localeCompare(a.maj));
}

module.exports = { nouvelle, lire, enregistrer, supprimer, liste };
