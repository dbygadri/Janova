// Journal en direct : ce que l'IA fait en ce moment, en phrases simples, et l'historique de toutes les tâches.
const fs = require('fs');
const path = require('path');
const projets = require('./projets');
const taches = require('./taches');

const court = (f) => (f ? path.basename(String(f)) : '');

// Une ligne du journal de Claude Code → une phrase lisible (ou null si rien d'intéressant).
function decrire(ev) {
  if (ev.type === 'assistant') {
    const res = [];
    for (const c of (ev.message && ev.message.content) || []) {
      if (c.type === 'text' && c.text.trim()) res.push({ genre: 'texte', texte: c.text.trim() });
      if (c.type !== 'tool_use') continue;
      const i = c.input || {};
      const actions = {
        Read: () => `Lit ${court(i.file_path)}`,
        Edit: () => `Modifie ${court(i.file_path)}`,
        MultiEdit: () => `Modifie ${court(i.file_path)}`,
        Write: () => `Écrit ${court(i.file_path)}`,
        Glob: () => 'Cherche des fichiers',
        Grep: () => `Cherche « ${String(i.pattern || '').slice(0, 40)} »`,
        Bash: () => i.description || `Lance : ${String(i.command || '').slice(0, 80)}`,
        WebFetch: () => 'Consulte une page web',
        WebSearch: () => `Cherche sur le web : ${String(i.query || '').slice(0, 60)}`,
        Task: () => 'Confie une partie du travail à un assistant',
        Agent: () => 'Confie une partie du travail à un assistant',
      };
      if (c.name === 'TodoWrite') continue;
      res.push({ genre: 'action', texte: (actions[c.name] || (() => c.name))() });
    }
    return res;
  }
  if (ev.type === 'result') return [{ genre: 'fin', texte: ev.is_error ? 'Terminé avec une erreur.' : 'Terminé.' }];
  return [];
}

// Lit la suite d'un journal à partir d'une position : renvoie les nouvelles phrases et la nouvelle position.
function lireDepuis(fichier, position = 0) {
  let contenu = '';
  try {
    const taille = fs.statSync(fichier).size;
    if (taille <= position) return { lignes: [], position };
    const fd = fs.openSync(fichier, 'r');
    const buf = Buffer.alloc(taille - position);
    fs.readSync(fd, buf, 0, buf.length, position);
    fs.closeSync(fd);
    contenu = buf.toString('utf8');
  } catch {
    return { lignes: [], position };
  }
  const fin = contenu.lastIndexOf('\n');
  if (fin < 0) return { lignes: [], position };
  const lignes = [];
  for (const l of contenu.slice(0, fin).split('\n')) {
    try { lignes.push(...decrire(JSON.parse(l))); } catch {}
  }
  return { lignes, position: position + Buffer.byteLength(contenu.slice(0, fin + 1)) };
}

// Toutes les tâches de tous les projets, les plus récentes d'abord, et celle qui tourne en ce moment.
function historique() {
  const toutes = [];
  for (const p of projets.liste()) {
    for (const t of taches.lire(p)) toutes.push({ ...t, projet: p.id, projetNom: p.nom });
  }
  const date = (t) => t.fin || t.debut || t.creee || '';
  toutes.sort((a, b) => date(b).localeCompare(date(a)));
  return { enCours: toutes.find((t) => t.statut === 'en_cours') || null, taches: toutes.filter((t) => t.debut || t.fin) };
}

module.exports = { decrire, lireDepuis, historique };
