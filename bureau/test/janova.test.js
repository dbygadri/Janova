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
process.env.JANOVA_MEMOIRE = path.join(tmp, 'memoire');
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
  fs.mkdirSync(process.env.JANOVA_MEMOIRE, { recursive: true });
  fs.writeFileSync(path.join(process.env.JANOVA_MEMOIRE, 'github.json'), JSON.stringify([{ name: 'alkestore-mvp' }, { name: 'Janova' }]));
  const liste = projets.liste();
  assert.deepStrictEqual(liste.map((p) => p.nom), ['Alkestore', 'Janova']);
  assert.ok(liste[0].groupe && !liste[1].groupe);
  assert.strictEqual(projets.dossierDepot(liste[0], 'alkestore-mvp'), path.join(process.env.JANOVA_RACINE, 'alkestore-mvp'));
  assert.strictEqual(liste[1].dossier, path.join(process.env.JANOVA_RACINE, 'Janova'));
  // La mémoire ne garde que des chemins relatifs : elle ne dépend pas de la machine.
  const enregistre = JSON.parse(fs.readFileSync(path.join(process.env.JANOVA_MEMOIRE, 'projets.json'), 'utf8'));
  assert.ok(enregistre.projets.every((p) => !path.isAbsolute(p.dossier)));
  projets.memoriserDernier('gh-janova');
  assert.strictEqual(projets.dernier(), 'gh-janova');
});

test('tâches : ajouter, cocher, supprimer', () => {
  const taches = require('../lib/taches');
  const p = { id: 'essai', dossier: path.join(tmp, 'p'), groupe: false };
  const t = taches.ajouter(p, { titre: 'Essai', cochee: false });
  assert.strictEqual(taches.lire(p)[0].statut, 'en_attente');
  taches.changer(p, t.id, { cochee: true });
  assert.strictEqual(taches.lire(p)[0].cochee, true);
  assert.ok(fs.existsSync(path.join(process.env.JANOVA_MEMOIRE, 'projets', 'essai', 'taches.json')));
  taches.supprimer(p, t.id);
  assert.strictEqual(taches.lire(p).length, 0);
});

test('discussions : enregistrer et rechercher', () => {
  const discussions = require('../lib/discussions');
  const d = discussions.nouvelle('gh-janova', tmp);
  d.titre = 'Couleur du bouton';
  d.messages.push({ role: 'moi', texte: 'Mets le bouton en vert' });
  discussions.enregistrer(d, 'Janova');
  assert.strictEqual(discussions.liste({ recherche: 'vert' }).length, 1);
  const md = fs.readFileSync(path.join(process.env.JANOVA_MEMOIRE, 'discussions', d.id + '.md'), 'utf8');
  assert.ok(md.includes('[[Janova]]') && md.includes('Mets le bouton en vert'));
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
  assert.strictEqual(g.interditsPour(tmp).length, g.INTERDITS.length + 2); // + la mémoire, jamais modifiée pendant une tâche
  assert.ok(!g.INTERDITS_DEPLOIEMENT.includes('Bash(vercel:*)') && g.INTERDITS_DEPLOIEMENT.includes('Bash(git push --force:*)'));
});

test('cerveau : la porte fournit discuter et executerTache', () => {
  const cerveau = require('../cerveau');
  assert.strictEqual(typeof cerveau.discuter, 'function');
  assert.strictEqual(typeof cerveau.executerTache, 'function');
});

test('cerveau en couches : le noyau répond seul à ce qu\'il sait déjà faire', async () => {
  const noyau = require('../cerveau/noyau');
  assert.ok(noyau.disponible, 'le noyau Janova doit être livré avec le bureau');
  const r = await noyau.demander('calcule 6 * 7');
  assert.ok(r && r.reponse.includes('42'));
  assert.strictEqual(await noyau.demander('ajoute une page de connexion au site'), null);
  // Depuis le chat, le noyau n'agit jamais sur l'ordinateur.
  assert.strictEqual(await noyau.demander('range mes téléchargements'), null);
});

test('mémoire : chaque échange est gardé pour apprendre', () => {
  const memoire = require('../lib/memoire');
  memoire.noterEchange({ projet: 'gh-janova', question: 'Bonjour', reponse: 'Bonjour !', couche: 'noyau' });
  const dossier = path.join(process.env.JANOVA_MEMOIRE, 'echanges');
  const lignes = fs.readdirSync(dossier).flatMap((f) => fs.readFileSync(path.join(dossier, f), 'utf8').trim().split('\n'));
  assert.strictEqual(JSON.parse(lignes.pop()).couche, 'noyau');
});

test('mémoire du projet : fait, décisions, reste à faire', () => {
  const memoire = require('../lib/memoire');
  const p = { id: 'ctx', nom: 'Ctx' };
  memoire.mettreAJourContexte(p, { fait: 'Page de connexion', decisions: ['Paiement mobile'], reste: ['Tester'] });
  memoire.mettreAJourContexte(p, { fait: 'Bouton vert' });
  const c = memoire.lireContexte(p);
  assert.ok(/## Fait\n- \d{4}-\d\d-\d\d : Bouton vert\n- .* : Page de connexion/.test(c));
  assert.ok(c.includes('Paiement mobile') && c.includes('- Tester'));
});

test('journal : les actions de Claude Code deviennent des phrases simples', () => {
  const { decrire } = require('../lib/journal');
  const lignes = decrire({ type: 'assistant', message: { content: [
    { type: 'tool_use', name: 'Edit', input: { file_path: '/a/b/style.css' } },
    { type: 'tool_use', name: 'Bash', input: { command: 'npm test', description: 'Lance les tests' } },
    { type: 'text', text: 'Fini.' },
  ] } });
  assert.deepStrictEqual(lignes.map((l) => l.texte), ['Modifie style.css', 'Lance les tests', 'Fini.']);
});

test('mise en ligne : résumé de ce qui part, feu vert obligatoire', () => {
  const memoire = require('../lib/memoire');
  const deploiement = require('../lib/deploiement');
  const taches = require('../lib/taches');
  const depot = path.join(process.env.JANOVA_RACINE, 'site');
  fs.mkdirSync(depot, { recursive: true });
  const g = (...a) => execFileSync('git', ['-c', 'user.name=t', '-c', 'user.email=t@t', ...a], { cwd: depot });
  g('init', '-q', '-b', 'main');
  fs.writeFileSync(path.join(depot, 'a.txt'), '1');
  g('add', '.'); g('commit', '-qm', 'Première page');
  g('checkout', '-qb', 'janova/travail');
  fs.writeFileSync(path.join(depot, 'a.txt'), '2');
  g('commit', '-qam', 'Bouton vert'); g('checkout', '-q', 'main');
  const p = { id: 'site', nom: 'Site', dossier: depot, depots: ['site'], groupe: false };
  memoire.ecrireJson(memoire.chemin('projets', 'site', 'deploiement.json'), { destinations: [{ id: 'web', nom: 'Le site', depot: 'site', type: 'vercel', description: 'Le site.', instructions: 'Publier.', retour: 'Revenir.' }] });
  const r = deploiement.resume(p, 'web');
  assert.deepStrictEqual(r.changements, ['Bouton vert', 'Première page']);
  assert.strictEqual(r.aFusionner, 1);
  assert.throws(() => deploiement.feuVert(p, 'web', { retour: true }), /Aucune mise en ligne précédente/);
  const t = deploiement.feuVert(p, 'web');
  assert.ok(t.feuVert && t.type === 'deploiement' && t.cochee);
  assert.throws(() => deploiement.feuVert(p, 'web'), /déjà prévue/);
  // Une tâche ajoutée normalement ne peut pas se donner un feu vert.
  const ordinaire = taches.ajouter(p, { titre: 'x', feuVert: 'oui', type: 'deploiement' });
  assert.ok(!ordinaire.feuVert && !ordinaire.type);
});
