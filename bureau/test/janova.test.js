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

test('réflexes : seule une réponse courte, sans contexte et durable peut être retenue', () => {
  const { peutRetenir } = require('../lib/reflexes');
  const ok = { question: "C'est quoi un serveur DNS ?", reponse: "Un annuaire d'Internet." };
  assert.ok(peutRetenir(ok));
  assert.ok(!peutRetenir({ ...ok, question: 'q'.repeat(120) }));
  assert.ok(!peutRetenir({ ...ok, reponse: 'r'.repeat(1500) }));
  assert.ok(!peutRetenir({ ...ok, question: '' }));
  assert.ok(!peutRetenir({ ...ok, session: 'abc' }));
  assert.ok(!peutRetenir({ ...ok, contexte: [{ question: 'a', reponse: 'b' }] }));
  assert.ok(!peutRetenir({ ...ok, outils: true }));
  for (const question of ['Quelle heure est-il ?', "On est quel jour aujourd'hui ?", 'Quelle météo demain ?',
    'Le prix du pain ?', "L'actualité en ce moment ?", "Quel est l'âge de Macron ?"]) {
    assert.ok(!peutRetenir({ ...ok, question }), question);
  }
  assert.ok(!peutRetenir({ ...ok, reponse: 'Il fait 20 degrés en ce moment.' }));
  assert.ok(peutRetenir({ ...ok, question: 'Que veut dire « prioritaire » ?' })); // « prix » n'est pas un mot entier ici
});

test('réflexes : « Retenir » fait apprendre la réponse au noyau, qui la sert ensuite seul', async () => {
  const { retenir } = require('../lib/reflexes');
  const noyau = require('../cerveau/noyau');
  if (!noyau.disponible) return;
  const question = 'Que veut dire RAM ?';
  assert.strictEqual(await noyau.demander(question), null);
  assert.deepStrictEqual(await retenir(question, 'La mémoire vive de l’ordinateur.'), { appris: true });
  const r = await noyau.demander('que veut dire ram');
  assert.strictEqual(r.reponse, 'La mémoire vive de l’ordinateur.');
  assert.ok(!(await retenir('', 'x')).appris);
});

test('nuit : horaires, limite par nuit et compte rendu du matin (heure fournie)', () => {
  const nuit = require('../lib/nuit');
  const memoire = require('../lib/memoire');
  const h = (s) => new Date(s); // heure locale
  assert.ok(nuit.estLaNuit(h('2026-10-24T23:00:00')) && nuit.estLaNuit(h('2026-10-25T06:59:00')));
  assert.ok(!nuit.estLaNuit(h('2026-10-25T07:00:00')) && !nuit.estLaNuit(h('2026-10-24T22:59:00')));
  assert.strictEqual(nuit.nuitDe(h('2026-10-24T23:30:00')), '2026-10-24');
  assert.strictEqual(nuit.nuitDe(h('2026-10-25T03:00:00')), '2026-10-24');
  assert.strictEqual(nuit.nuitDe(h('2026-10-25T12:00:00')), null);

  const jourT = { cochee: true, statut: 'en_attente' };
  const nuitT = { ...jourT, nuit: true };
  assert.ok(nuit.peutPartir(jourT, h('2026-10-24T14:00:00'), 0));
  assert.ok(!nuit.peutPartir(nuitT, h('2026-10-24T14:00:00'), 0));
  assert.ok(nuit.peutPartir(nuitT, h('2026-10-25T01:00:00'), 2));
  assert.ok(!nuit.peutPartir(nuitT, h('2026-10-25T01:00:00'), 3));
  assert.ok(!nuit.peutPartir({ ...nuitT, cochee: false }, h('2026-10-25T01:00:00'), 0));
  assert.strictEqual(nuit.limite(), nuit.LIMITE_PAR_DEFAUT);
  memoire.changerReglages({ taches_de_nuit_max: 5 });
  assert.strictEqual(nuit.limite(), 5);

  const taches = [
    { titre: 'Faire A', nuit: true, statut: 'terminee', debut: h('2026-10-24T23:10:00').toISOString(), resultat: 'A est fait.' },
    { titre: 'Faire B', nuit: true, statut: 'bloquee', debut: h('2026-10-25T02:00:00').toISOString(), resultat: 'Il manque une info.' },
    { titre: 'De jour', statut: 'terminee', debut: h('2026-10-24T15:00:00').toISOString() },
  ];
  assert.strictEqual(nuit.parties(taches, '2026-10-24').length, 2);
  assert.strictEqual(nuit.ecrireSiBesoin(h('2026-10-25T06:00:00'), [{ projet: 'Janova', taches }]), null);
  const f = nuit.ecrireSiBesoin(h('2026-10-25T07:05:00'), [{ projet: 'Janova', taches }], ['mise en ligne de Janova']);
  assert.ok(f.endsWith(path.join('comptes-rendus', '2026-10-25.md')));
  const texte = fs.readFileSync(f, 'utf8');
  for (const morceau of ['Faire A', 'terminée', 'A est fait.', 'bloquée', 'Ce qui attend ton avis', 'Tâche bloquée : Faire B', 'À valider : mise en ligne']) {
    assert.ok(texte.includes(morceau), morceau);
  }
  assert.ok(!texte.includes('De jour'));
  assert.strictEqual(nuit.ecrireSiBesoin(h('2026-10-25T08:00:00'), [{ projet: 'Janova', taches }]), null); // une seule fois
  assert.strictEqual(nuit.ecrireSiBesoin(h('2026-10-26T08:00:00'), [{ projet: 'Janova', taches }]), null); // nuit sans tâche

  assert.strictEqual(nuit.nonLu(h('2026-10-25T09:00:00')).jour, '2026-10-25');
  nuit.marquerLu('2026-10-25');
  assert.strictEqual(nuit.nonLu(h('2026-10-25T09:00:00')), null);
});

test('idées : lignes « IDÉE : » lues, filtrées et ajoutées non cochées', () => {
  const idees = require('../lib/idees');
  const taches = require('../lib/taches');
  const lu = idees.lire([
    'J’ai fait le travail.',
    'DÉCISION : garder le vert',
    '- **IDÉE** : Ajouter un bouton Exporter | Ajoute un bouton « Exporter » dans la liste des notes.',
    'idee : Écrire la doc',
    '* IDÉE : Mettre en ligne la version | Déploie sur Vercel.',
    'IDÉE : Quatrième idée | trop',
  ].join('\n'));
  assert.strictEqual(lu.texte, 'J’ai fait le travail.\nDÉCISION : garder le vert');
  assert.strictEqual(lu.idees.length, idees.MAX_PAR_TACHE);
  assert.deepStrictEqual(lu.idees[0], { titre: 'Ajouter un bouton Exporter', instructions: 'Ajoute un bouton « Exporter » dans la liste des notes.' });
  assert.deepStrictEqual(lu.idees[1], { titre: 'Écrire la doc', instructions: 'Écrire la doc' });

  assert.ok(!idees.acceptable({ titre: 'Déployer le site', instructions: 'x' }));
  assert.ok(!idees.acceptable({ titre: 'Nettoyer', instructions: 'Simplifie bureau/runner.js' }));
  assert.ok(!idees.acceptable({ titre: 'Revoir les garde-fous', instructions: 'x' }));
  assert.ok(!idees.acceptable({ titre: 'Revoir', instructions: 'Change deploiement.js' }));
  assert.ok(idees.acceptable({ titre: 'Ajouter un bouton', instructions: 'Dans renderer.js' }));

  const p = { id: 'idees', dossier: path.join(tmp, 'pi'), groupe: false };
  taches.ajouter(p, { titre: 'Écrire la doc !', cochee: false });
  const ajoutees = idees.ajouter(p, lu.idees, { id: 'abcd1234' });
  assert.deepStrictEqual(ajoutees.map((t) => t.titre), ['Ajouter un bouton Exporter']); // doublon et mise en ligne ignorés
  assert.strictEqual(ajoutees[0].cochee, false);
  assert.strictEqual(ajoutees[0].proposee, true);
  assert.strictEqual(ajoutees[0].origine, 'abcd1234');
  for (let i = 0; i < 12; i++) idees.ajouter(p, [{ titre: 'Idée ' + i, instructions: 'x' }], { id: 'o' });
  assert.strictEqual(taches.lire(p).filter((t) => t.proposee).length, idees.MAX_EN_ATTENTE);
  assert.ok(idees.CONSIGNE.startsWith('IDÉE :') && /mise en ligne/.test(idees.CONSIGNE));
});

test('curiosité : en pause au départ, et seulement quand l\'ordinateur est inactif sans tâche en cours', () => {
  const curiosite = require('../lib/curiosite');
  const memoire = require('../lib/memoire');
  assert.deepStrictEqual(curiosite.reglages(), curiosite.DEFAUTS);
  assert.strictEqual(curiosite.reglages().active, false);
  curiosite.activer(true);
  memoire.changerReglages({ curiosite_inactivite_min: 15 });
  const r = curiosite.reglages();
  assert.ok(r.active && r.inactiviteMin === 15 && r.intervalleMin === 10);
  const base = { reglages: r, inactifS: 20 * 60, tacheEnCours: false, enCours: false, derniere: 0, maintenant: 1e12 };
  assert.ok(curiosite.peutLancer(base));
  assert.ok(!curiosite.peutLancer({ ...base, inactifS: 14 * 60 })); // l'utilisateur est là
  assert.ok(!curiosite.peutLancer({ ...base, tacheEnCours: true })); // Claude Code travaille
  assert.ok(!curiosite.peutLancer({ ...base, enCours: true }));
  assert.ok(!curiosite.peutLancer({ ...base, derniere: 1e12 - 9 * 60 * 1000 })); // une toutes les 10 minutes
  assert.ok(curiosite.peutLancer({ ...base, derniere: 1e12 - 10 * 60 * 1000 }));
  assert.ok(!curiosite.peutLancer({ ...base, reglages: { ...r, active: false } }));
  curiosite.activer(false);
});

test('curiosité : sujets, suggestion, écart et découvertes (sans réseau)', async () => {
  const curiosite = require('../lib/curiosite');
  const memoire = require('../lib/memoire');
  const sujets = await curiosite.sujets();
  assert.ok(sujets.some((s) => s.origine === 'cap'));
  assert.strictEqual((await curiosite.suggerer('robots jardiniers')).ok, true);
  assert.strictEqual((await curiosite.suggerer('dby.perso@gmail.com')).ok, false); // rien de personnel ne part
  assert.strictEqual((await curiosite.sujets())[0].nom, 'robots jardiniers');
  await curiosite.ecarter('robots jardiniers');
  assert.ok(!(await curiosite.sujets()).some((s) => s.nom === 'robots jardiniers'));

  const d = (date, sujet) => JSON.stringify({ date, sujet, pourquoi: 'parce que', appris: ['Une chose apprise.'], sources: [{ adresse: 'https://fr.wikipedia.org/wiki/X', titre: 'X', source: 'Wikipédia (fr)' }] });
  memoire.ecrire(memoire.chemin('noyau', 'curiosite', '2026-10-25.jsonl'), d(new Date('2026-10-25T02:00:00').toISOString(), 'B') + '\n' + d(new Date('2026-10-25T12:00:00').toISOString(), 'C') + '\n');
  memoire.ecrire(memoire.chemin('noyau', 'curiosite', '2026-10-24.jsonl'), d(new Date('2026-10-24T23:30:00').toISOString(), 'A') + '\n');
  assert.deepStrictEqual(curiosite.decouvertes().map((x) => x.sujet), ['C', 'B', 'A']); // les plus récentes en haut

  const nuit = require('../lib/nuit');
  assert.deepStrictEqual(nuit.decouvertesDeLaNuit('2026-10-24').map((x) => x.sujet), ['A', 'B']);
  const texte = nuit.rediger('2026-10-24', [], [], nuit.decouvertesDeLaNuit('2026-10-24'));
  for (const morceau of ['Ce que j\'ai découvert', '### A', 'Pourquoi : parce que', '- Une chose apprise.', 'https://fr.wikipedia.org/wiki/X']) {
    assert.ok(texte.includes(morceau), morceau);
  }
  assert.ok(!nuit.rediger('2026-10-24', []).includes('découvert'));
});
