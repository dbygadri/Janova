// Retenir une réponse de Claude comme réflexe du noyau, pour que Janova y réponde seule la prochaine fois.
// Rien n'est retenu automatiquement : le bureau propose « Retenir », l'utilisateur décide.
const { execFile } = require('child_process');
const fs = require('fs');
const path = require('path');
const memoire = require('./memoire');

const QUESTION_MAX = 120;
const REPONSE_MAX = 1500;

// Ce qui change avec le temps ne doit pas devenir un réflexe : la réponse serait vite fausse.
const CHANGE_AVEC_LE_TEMPS = new RegExp('(?<![\\p{L}\\d])(' + [
  'heures?', 'minutes?', 'date', "aujourd'hui", 'aujourd’hui', 'demain', 'hier', 'ce soir', 'ce matin', 'cette semaine',
  'ce mois', 'cette année', 'maintenant', 'actuellement', 'en ce moment', 'récemment', 'dernière?s?', 'derniers',
  'météo', 'temps qu.il fait', 'températures?', 'prix', 'coûte', 'tarifs?', 'bourse', 'actualités?', 'news',
  'nouvelles?', 'infos?', 'résultats?', 'scores?', 'élections?', 'quel jour', 'quelle année', 'quel mois', 'âge',
].join('|') + ')(?![\\p{L}\\d])', 'iu');

// Une réponse peut être retenue si elle tient seule : courte, sans contexte de discussion
// (ni échange précédent avec Claude, ni réponses du noyau à lui redonner, ni fichier lu), et durable.
function peutRetenir({ question, reponse, contexte = [], session = null, outils = false }) {
  const q = (question || '').trim();
  const r = (reponse || '').trim();
  if (!q || !r || q.length >= QUESTION_MAX || r.length >= REPONSE_MAX) return false;
  if (session || contexte.length || outils) return false;
  if (/```janova-/.test(r)) return false; // une proposition (tâche, projet…) n'est pas une réponse à resservir
  return !CHANGE_AVEC_LE_TEMPS.test(q) && !CHANGE_AVEC_LE_TEMPS.test(r);
}

// Le noyau est livré à côté du bureau (version installée : noyau/janova) ou dans le dépôt (../janova).
const RACINE_BUREAU = path.join(__dirname, '..');
const RACINE_NOYAU = () => [path.join(RACINE_BUREAU, 'noyau'), path.join(RACINE_BUREAU, '..')]
  .find((d) => fs.existsSync(path.join(d, 'janova', 'pont.py')));

// Demande au pont du noyau d'apprendre la paire. Renvoie { appris: true } ou { appris: false, erreur }.
function retenir(question, reponse, delai = 8000) {
  const racine = RACINE_NOYAU();
  if (!racine) return Promise.resolve({ appris: false, erreur: 'Le noyau de Janova est introuvable.' });
  return new Promise((resolve) => {
    const p = execFile('python3', ['-m', 'janova.pont'], {
      cwd: racine,
      env: { ...process.env, JANOVA_MEMOIRE: memoire.MEMOIRE },
      timeout: delai,
    }, (err, out) => {
      if (err) return resolve({ appris: false, erreur: 'Le noyau n’a pas répondu.' });
      try { resolve(JSON.parse(out)); } catch { resolve({ appris: false, erreur: 'Réponse illisible du noyau.' }); }
    });
    p.stdin.end(JSON.stringify({ apprendre: { question, reponse } }));
  });
}

module.exports = { peutRetenir, retenir, QUESTION_MAX, REPONSE_MAX };
