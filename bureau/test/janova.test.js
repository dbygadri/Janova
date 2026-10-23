// Tests du bureau de Janova : lancés avant toute installation d'une nouvelle version (npm test).
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync } = require('child_process');

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'janova-test-'));
process.env.JANOVA_DONNEES = path.join(tmp, 'donnees');
process.env.JANOVA_ETAT = path.join(tmp, 'etat');
process.env.JANOVA_RACINE = path.join(tmp, 'racine');
test.after(() => fs.rmSync(tmp, { recursive: true, force: true }));

const racine = path.join(__dirname, '..');

test('tous les fichiers JavaScript sont valides', () => {
  const fichiers = [];
  const parcourir = (d) => {
    for (const e of fs.readdirSync(d, { withFileTypes: true })) {
      if (e.name === 'node_modules' || e.name.startsWith('.')) continue;
      const f = path.join(d, e.name);
      if (e.isDirectory()) parcourir(f);
      else if (f.endsWith('.js')) fichiers.push(f);
    }
  };
  parcourir(racine);
  for (const f of fichiers) execFileSync(process.execPath, ['--check', f]);
  assert.ok(fichiers.length > 5);
});

test('projets : groupe Alkestore et dépôts GitHub', () => {
  const projets = require('../lib/projets');
  fs.mkdirSync(process.env.JANOVA_DONNEES, { recursive: true });
  fs.writeFileSync(path.join(process.env.JANOVA_DONNEES, 'github.json'), JSON.stringify([{ name: 'alkestore-mvp' }, { name: 'Janova' }]));
  const liste = projets.liste();
  assert.deepStrictEqual(liste.map((p) => p.nom), ['Alkestore', 'Janova']);
  assert.ok(liste[0].groupe && !liste[1].groupe);
  assert.strictEqual(projets.dossierDepot(liste[0], 'alkestore-mvp'), path.join(process.env.JANOVA_RACINE, 'alkestore-mvp'));
});

test('tâches : ajouter, cocher, supprimer', () => {
  const taches = require('../lib/taches');
  const p = { dossier: path.join(tmp, 'p'), groupe: false };
  const t = taches.ajouter(p, { titre: 'Essai', cochee: false });
  assert.strictEqual(taches.lire(p)[0].statut, 'en_attente');
  taches.changer(p, t.id, { cochee: true });
  assert.strictEqual(taches.lire(p)[0].cochee, true);
  taches.supprimer(p, t.id);
  assert.strictEqual(taches.lire(p).length, 0);
});

test('discussions : enregistrer et rechercher', () => {
  const discussions = require('../lib/discussions');
  const d = discussions.nouvelle('gh-janova', tmp);
  d.titre = 'Couleur du bouton';
  d.messages.push({ role: 'moi', texte: 'Mets le bouton en vert' });
  discussions.enregistrer(d);
  assert.strictEqual(discussions.liste({ recherche: 'vert' }).length, 1);
  assert.strictEqual(discussions.liste({ recherche: 'rouge' }).length, 0);
  assert.strictEqual(discussions.liste({ projet: null }).length, 0);
});

test('garde-fous : fichiers protégés et interdits', () => {
  const g = require('../lib/garde-fous');
  assert.deepStrictEqual(g.touchesProtegees(['bureau/runner.js', 'bureau/style.css', 'bureau/cerveau/claude.js']), ['bureau/runner.js', 'bureau/cerveau/claude.js']);
  for (const i of ['Bash(git push:*)', 'Bash(vercel:*)', 'Bash(ssh:*)']) assert.ok(g.INTERDITS.includes(i));
  const depotJanova = path.join(tmp, 'Janova');
  fs.mkdirSync(path.join(depotJanova, 'bureau', 'lib'), { recursive: true });
  fs.writeFileSync(path.join(depotJanova, 'bureau', 'lib', 'garde-fous.js'), '');
  assert.ok(g.interditsPour(depotJanova).includes(`Edit(/${depotJanova}/bureau/runner.js)`));
  assert.strictEqual(g.interditsPour(tmp).length, g.INTERDITS.length);
});

test('cerveau : la porte fournit discuter et executerTache', () => {
  const cerveau = require('../cerveau');
  assert.strictEqual(typeof cerveau.discuter, 'function');
  assert.strictEqual(typeof cerveau.executerTache, 'function');
});
