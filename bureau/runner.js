// Exécuteur de tâches (fichier protégé) : tourne en fond, prend les tâches cochées une par une,
// tous projets confondus, et les confie au cerveau.
const { execFileSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const taches = require('./lib/taches');
const projets = require('./lib/projets');
const cerveau = require('./cerveau');
const { BRANCHE, REGLES, estJanova, interditsPour, touchesProtegees } = require('./lib/garde-fous');

const DUREE_MAX = 2 * 60 * 60 * 1000; // 2 heures par tâche
const JOURNAUX = path.join(projets.ETAT, 'journaux');

function git(dossier, ...args) {
  return execFileSync('git', args, { cwd: dossier, env: cerveau.ENV, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }).trim();
}

function consigne(p, t) {
  return `Tu travailles seul, sans personne devant l'écran, pour le projet « ${p.nom} ».

Tâche : ${t.titre}

Instructions :
${t.instructions}

${REGLES}

Termine par un résumé de 2 à 4 phrases en français simple, pour quelqu'un qui ne code pas : ce que tu as fait, et ce qui reste à faire.`;
}

async function executer(p, t) {
  const dossier = projets.dossierDepot(p, t.dossier);
  const debut = Date.now();
  const fin = (statut, resultat, extra = {}) =>
    taches.changer(p, t.id, {
      statut, resultat, fin: new Date().toISOString(), duree_s: Math.round((Date.now() - debut) / 1000), ...extra,
    });

  if (!fs.existsSync(path.join(dossier, '.git'))) {
    return fin('bloquee', p.groupe
      ? `Le dépôt « ${t.dossier || '(aucun)'} » n'est pas sur ce PC. Choisis un dépôt pour cette tâche.`
      : "Ce projet n'est pas encore un dépôt git sur ce PC. Ouvre-le une fois dans Janova.");
  }
  projets.exclureDonnees(dossier);
  if (git(dossier, 'status', '--porcelain')) {
    return fin('bloquee', 'Ce dossier contient des modifications non enregistrées. Enregistre-les (commit) ou annule-les, puis recoche la tâche.');
  }

  const origine = git(dossier, 'rev-parse', '--abbrev-ref', 'HEAD');
  try {
    git(dossier, 'checkout', '-q', BRANCHE);
  } catch {
    git(dossier, 'checkout', '-q', '-b', BRANCHE);
  }
  const avant = git(dossier, 'rev-parse', 'HEAD');
  taches.changer(p, t.id, { statut: 'en_cours', debut: new Date().toISOString(), branche: BRANCHE, commit_avant: avant });

  fs.mkdirSync(JOURNAUX, { recursive: true });
  const journal = path.join(JOURNAUX, `${t.id}.jsonl`);
  let res = { reussi: false, resume: 'Aucun résumé reçu.' };
  try {
    res = await cerveau.executerTache({ consigne: consigne(p, t), dossier, interdits: interditsPour(dossier), journal, dureeMax: DUREE_MAX });
  } finally {
    // Ce qui n'a pas été enregistré par le cerveau l'est ici, puis on revient sur la branche de départ.
    try {
      if (git(dossier, 'status', '--porcelain')) {
        git(dossier, 'add', '-A');
        git(dossier, 'commit', '-q', '-m', `Janova : ${t.titre}`);
      }
      if (git(dossier, 'rev-parse', '--abbrev-ref', 'HEAD') !== origine) git(dossier, 'checkout', '-q', origine);
    } catch (e) {
      console.error('git après tâche :', e.message);
    }
  }

  const apres = git(dossier, 'rev-parse', BRANCHE);
  if (estJanova(dossier)) {
    const touches = touchesProtegees(git(dossier, 'diff', '--name-only', avant, apres).split('\n').filter(Boolean));
    if (touches.length) {
      return fin('bloquee', `Cette tâche a modifié les garde-fous de Janova (${touches.join(', ')}). Rien n'est appliqué : Janova te demandera ton oui avant toute mise à jour.\n\n${res.resume}`.slice(0, 4000), { commit_apres: apres, journal });
    }
  }
  fin(res.reussi ? 'terminee' : 'echec', res.resume.slice(0, 4000), { commit_apres: apres, journal });
}

const projetsPresents = () => projets.liste().filter((p) => p.present);

let occupe = false;
let premierTour = true;
async function tour() {
  if (occupe) return;
  occupe = true;
  try {
    // On ne reprend pas une tâche restée « en cours » après une coupure : on la signale.
    if (premierTour) {
      premierTour = false;
      for (const p of projetsPresents()) {
        for (const t of taches.lire(p)) {
          if (t.statut === 'en_cours') {
            taches.changer(p, t.id, { statut: 'echec', resultat: "Interrompue (l'ordinateur ou l'exécuteur s'est arrêté). Recoche-la pour la relancer." });
          }
        }
      }
    }
    // Une tâche à la fois, tous projets confondus.
    for (;;) {
      let suivante = null;
      for (const p of projetsPresents()) {
        const t = taches.lire(p).find((x) => x.cochee && x.statut === 'en_attente');
        if (t) { suivante = { p, t }; break; }
      }
      if (!suivante) break;
      const { p, t } = suivante;
      console.log('Tâche', p.nom, t.id, t.titre);
      try {
        await executer(p, t);
      } catch (e) {
        taches.changer(p, t.id, { statut: 'echec', resultat: 'Erreur de Janova : ' + e.message });
      }
    }
  } finally {
    occupe = false;
  }
}

console.log(`Exécuteur Janova démarré (cerveau : ${cerveau.nom}).`);
tour();
setInterval(tour, 15000);
