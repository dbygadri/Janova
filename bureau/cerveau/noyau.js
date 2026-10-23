// Cerveau « noyau » : le noyau d'IA locale Janova (Python), par le pont janova/pont.py.
// Il ne répond que s'il sait déjà faire (réflexe ou organe) ; sinon il renvoie null.
const { execFile } = require('child_process');
const fs = require('fs');
const path = require('path');
const memoire = require('../lib/memoire');

// Le noyau est livré à côté du bureau (version installée : noyau/janova) ou dans le dépôt (../janova).
const RACINE_BUREAU = path.join(__dirname, '..');
const RACINE_NOYAU = [path.join(RACINE_BUREAU, 'noyau'), path.join(RACINE_BUREAU, '..')]
  .find((d) => fs.existsSync(path.join(d, 'janova', 'pont.py')));

function demander(message, delai = 8000) {
  if (!RACINE_NOYAU) return Promise.resolve(null);
  return new Promise((resolve) => {
    const p = execFile('python3', ['-m', 'janova.pont'], {
      cwd: RACINE_NOYAU,
      env: { ...process.env, JANOVA_MEMOIRE: memoire.MEMOIRE },
      timeout: delai,
    }, (err, out) => {
      if (err) return resolve(null);
      try {
        const r = JSON.parse(out);
        resolve(r.reponse ? r : null);
      } catch {
        resolve(null);
      }
    });
    p.stdin.end(JSON.stringify({ message }));
  });
}

module.exports = { nom: 'noyau Janova', disponible: !!RACINE_NOYAU, demander };
