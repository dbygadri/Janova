// Idées de tâches suivantes proposées par Claude Code à la fin d'une tâche (lignes « IDÉE : titre | instructions »).
// Elles arrivent toujours NON cochées : l'utilisateur coche celles qu'il veut, ou les supprime.
const taches = require('./taches');
const { PROTEGES } = require('./garde-fous');

const MAX_PAR_TACHE = 3;
const MAX_EN_ATTENTE = 10; // idées non cochées en attente, par projet

// Texte à ajouter à la consigne de fin de tâche.
const CONSIGNE = `IDÉE : titre court | instructions précises pour Claude Code (une tâche suivante utile, ${MAX_PAR_TACHE} au maximum, seulement si c'est vraiment utile ; jamais une mise en ligne ni une modification des garde-fous)`;

const LIGNE = /^\s*[-*]?\s*\**ID[ÉE]E\**\s*:\s*(.+)$/i;

// Sépare les lignes « IDÉE : » du reste du résumé.
function lire(resume) {
  const idees = [];
  const texte = [];
  for (const l of String(resume || '').split('\n')) {
    const m = l.match(LIGNE);
    if (!m) { texte.push(l); continue; }
    const [titre, ...reste] = m[1].replace(/\*+\s*$/, '').split('|');
    const t = titre.trim();
    if (t) idees.push({ titre: t, instructions: reste.join('|').trim() || t });
  }
  return { texte: texte.join('\n').trim(), idees: idees.slice(0, MAX_PAR_TACHE) };
}

// Minuscules, sans accents ni ponctuation, pour comparer deux titres.
const normaliser = (s) => String(s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')
  .replace(/[^a-z0-9]+/g, ' ').trim();

const DEPLOIEMENT = /\b(deploy\w*|deploi\w*|mettre en ligne|mise en ligne|mis en ligne|publier|publication|vercel|git push|play store|app store)\b/;
const NOMS_PROTEGES = PROTEGES.flatMap((p) => [p, p.replace(/^bureau\//, ''), p.replace(/\/$/, '').split('/').pop()])
  .map((n) => normaliser(n)).filter(Boolean);

// Une idée ne doit jamais parler de mise en ligne ni toucher aux garde-fous.
function acceptable(idee) {
  const brut = `${idee.titre} ${idee.instructions}`;
  const texte = normaliser(brut);
  if (DEPLOIEMENT.test(texte)) return false;
  if (/garde.?fous?/i.test(brut)) return false;
  const mots = ` ${texte} `;
  return !NOMS_PROTEGES.some((n) => mots.includes(` ${n} `));
}

// Ajoute les idées acceptables comme tâches non cochées du projet, rattachées à la tâche d'origine
// (même partie du projet pour un groupe). Renvoie les tâches ajoutées.
function ajouter(projet, idees, origine = {}) {
  const ajoutees = [];
  for (const idee of idees.slice(0, MAX_PAR_TACHE)) {
    const liste = taches.lire(projet);
    if (liste.filter((t) => t.proposee && !t.cochee && t.statut === 'en_attente').length >= MAX_EN_ATTENTE) break;
    if (!acceptable(idee)) continue;
    const titre = normaliser(idee.titre);
    if (liste.some((t) => t.statut !== 'terminee' && normaliser(t.titre) === titre)) continue;
    ajoutees.push(taches.ajouter(projet, {
      ...idee, dossier: origine.dossier || '', cochee: false, proposee: true, origine: origine.id,
    }));
  }
  return ajoutees;
}

module.exports = { CONSIGNE, MAX_PAR_TACHE, MAX_EN_ATTENTE, lire, normaliser, acceptable, ajouter };
