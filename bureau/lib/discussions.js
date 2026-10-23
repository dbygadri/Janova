// Historique des discussions avec Claude : un fichier par discussion.
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { DONNEES } = require('./projets');

const DOSSIER = path.join(DONNEES, 'discussions');
const fichier = (id) => path.join(DOSSIER, id.replace(/[^a-z0-9]/gi, '') + '.json');

function nouvelle(projetId, cwd) {
  return {
    id: crypto.randomBytes(6).toString('hex'),
    projet: projetId || null,
    cwd,
    titre: 'Nouvelle discussion',
    creee: new Date().toISOString(),
    maj: new Date().toISOString(),
    session: null,
    messages: [],
  };
}

function lire(id) {
  try { return JSON.parse(fs.readFileSync(fichier(id), 'utf8')); } catch { return null; }
}

function enregistrer(d) {
  if (!d.messages.length) return;
  d.maj = new Date().toISOString();
  fs.mkdirSync(DOSSIER, { recursive: true });
  const f = fichier(d.id);
  fs.writeFileSync(f + '.tmp', JSON.stringify(d, null, 1));
  fs.renameSync(f + '.tmp', f);
}

function supprimer(id) {
  fs.rmSync(fichier(id), { force: true });
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
