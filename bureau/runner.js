// Exécuteur de tâches (fichier protégé) : tourne en fond, prend les tâches cochées une par une,
// tous projets confondus, et les confie au cerveau. Il s'occupe aussi des annulations de tâches
// et des mises en ligne qui ont reçu le feu vert.
const { execFileSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const taches = require('./lib/taches');
const projets = require('./lib/projets');
const memoire = require('./lib/memoire');
const deploiement = require('./lib/deploiement');
const { prevenir } = require('./lib/notifier');
const cerveau = require('./cerveau');
const {
  BRANCHE, REGLES, REGLES_DEPLOIEMENT, INTERDITS_DEPLOIEMENT, estJanova, interditsPour, touchesProtegees,
} = require('./lib/garde-fous');

const DUREE_MAX = 2 * 60 * 60 * 1000; // 2 heures par tâche
const JOURNAUX = path.join(projets.ETAT, 'journaux');
const STATUTS = { terminee: 'terminée', echec: 'en échec', bloquee: 'bloquée' };

function git(dossier, ...args) {
  return execFileSync('git', args, { cwd: dossier, env: cerveau.ENV, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }).trim();
}
const existe = (dossier, ref) => { try { git(dossier, 'rev-parse', '--verify', '-q', ref); return true; } catch { return false; } };

const FIN_CONSIGNE = `Termine ta réponse par un résumé de 2 à 4 phrases en français simple, pour quelqu'un qui ne code pas : ce que tu as fait, et ce qui reste à faire.
Puis, s'il y en a, ajoute ces lignes (une idée par ligne) pour tenir à jour la mémoire du projet :
DÉCISION : une décision importante prise pendant ce travail
RESTE : une chose qui reste à faire sur le projet`;

function consigne(p, t) {
  return `Tu travailles seul, sans personne devant l'écran, pour le projet « ${p.nom} ».

Voici la mémoire du projet (ce qui a été fait, ce qui reste, les décisions prises) :
${memoire.contexteCourt(p)}

Tâche : ${t.titre}

Instructions :
${t.instructions}

${REGLES}

${FIN_CONSIGNE}`;
}

function consigneDeploiement(p, t, d, precedente, sha) {
  const quoi = t.type === 'retour'
    ? `Remets en ligne la version précédente de « ${d.nom} ». Version actuellement en ligne : ${precedente ? precedente.sha : 'inconnue'}.`
    : `Mets en ligne « ${d.nom} » : la version ${sha.slice(0, 7)} de la branche main.` +
      ` Version en ligne avant toi : ${precedente ? precedente.sha.slice(0, 7) + ' (du ' + precedente.date.slice(0, 10) + ')' : 'aucune connue'}.`;
  return `Tu fais une mise en ligne pour le projet « ${p.nom} ». L'utilisateur a donné son feu vert.

${quoi}

Ce que c'est : ${d.description}
Adresse à vérifier après la mise en ligne : ${d.verification || '(aucune)'}

Comment faire :
${t.instructions}

Mémoire du projet :
${memoire.contexteCourt(p)}

${REGLES_DEPLOIEMENT}

Termine par un résumé de 2 à 4 phrases en français simple : ce qui est en ligne, si la vérification est bonne, et comment revenir en arrière si besoin.`;
}

// Lit les lignes « DÉCISION : » et « RESTE : » du résumé, pour la mémoire du projet.
function lireMemoire(resume) {
  const decisions = [];
  const reste = [];
  const texte = [];
  for (const l of resume.split('\n')) {
    const m = l.match(/^\s*[-*]?\s*\**(D[ÉE]CISION|RESTE)\**\s*:\s*(.+)$/i);
    if (!m) { texte.push(l); continue; }
    (/^RESTE/i.test(m[1]) ? reste : decisions).push(m[2].trim());
  }
  return { texte: texte.join('\n').trim(), decisions, reste: reste.length ? reste : null };
}

async function fin(p, t, debut, statut, resultat, extra = {}) {
  taches.changer(p, t.id, {
    statut, resultat, fin: new Date().toISOString(), duree_s: Math.round((Date.now() - debut) / 1000), ...extra,
  });
  await prevenir(`${p.nom} : tâche ${STATUTS[statut] || statut}`, t.titre, { urgent: statut !== 'terminee' });
}

function verifierDossier(p, t, dossier) {
  if (!fs.existsSync(path.join(dossier, '.git'))) {
    return p.groupe
      ? `Le dépôt « ${t.dossier || '(aucun)'} » n'est pas sur ce PC. Choisis un dépôt pour cette tâche.`
      : "Ce projet n'est pas encore un dépôt git sur ce PC. Ouvre-le une fois dans Janova.";
  }
  if (git(dossier, 'status', '--porcelain')) {
    return 'Ce dossier contient des modifications non enregistrées. Enregistre-les (commit) ou annule-les, puis recoche la tâche.';
  }
  return null;
}

function journalDe(t) {
  fs.mkdirSync(JOURNAUX, { recursive: true });
  return path.join(JOURNAUX, `${t.id}.jsonl`);
}

async function executer(p, t) {
  const dossier = projets.dossierDepot(p, t.dossier);
  const debut = Date.now();
  const probleme = verifierDossier(p, t, dossier);
  if (probleme) return fin(p, t, debut, 'bloquee', probleme);

  // Point de sauvegarde : le commit de départ est noté, pour pouvoir annuler la tâche en un clic.
  const origine = git(dossier, 'rev-parse', '--abbrev-ref', 'HEAD');
  if (existe(dossier, BRANCHE)) git(dossier, 'checkout', '-q', BRANCHE);
  else git(dossier, 'checkout', '-q', '-b', BRANCHE);
  const avant = git(dossier, 'rev-parse', 'HEAD');
  const journal = journalDe(t);
  taches.changer(p, t.id, { statut: 'en_cours', debut: new Date().toISOString(), branche: BRANCHE, commit_avant: avant, journal });

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
  const lu = lireMemoire(res.resume);
  memoire.mettreAJourContexte(p, {
    fait: `${t.titre}${p.groupe ? ` (${t.dossier})` : ''}${res.reussi ? '' : ' (pas terminé)'}`,
    decisions: lu.decisions,
    reste: lu.reste,
  });
  if (estJanova(dossier)) {
    const touches = touchesProtegees(git(dossier, 'diff', '--name-only', avant, apres).split('\n').filter(Boolean));
    if (touches.length) {
      return fin(p, t, debut, 'bloquee', `Cette tâche a modifié les garde-fous de Janova (${touches.join(', ')}). Rien n'est appliqué : Janova te demandera ton oui avant toute mise à jour.\n\n${lu.texte}`.slice(0, 4000), { commit_apres: apres });
    }
  }
  await fin(p, t, debut, res.reussi ? 'terminee' : 'echec', lu.texte.slice(0, 4000), { commit_apres: apres });
}

// Mise en ligne (ou retour à la version précédente), seulement avec le feu vert de l'utilisateur.
async function deployer(p, t) {
  const debut = Date.now();
  const d = deploiement.destination(p, t.destination);
  if (!t.feuVert || !d) return fin(p, t, debut, 'bloquee', 'Pas de feu vert valable pour cette mise en ligne. Relance-la depuis le bouton « Mettre en ligne ».');
  const dossier = projets.dossierDepot(p, t.dossier);
  const probleme = verifierDossier(p, t, dossier);
  if (probleme) return fin(p, t, debut, 'bloquee', probleme);

  const origine = git(dossier, 'rev-parse', '--abbrev-ref', 'HEAD');
  const precedente = deploiement.derniere(p, d.id);
  let sha;
  try {
    // Le travail validé rejoint la version principale avant de partir en ligne.
    if (origine !== 'main') git(dossier, 'checkout', '-q', 'main');
    if (t.type !== 'retour' && existe(dossier, BRANCHE) && git(dossier, 'rev-list', '--count', `main..${BRANCHE}`) !== '0') {
      try {
        git(dossier, 'merge', '--no-edit', BRANCHE);
      } catch {
        try { git(dossier, 'merge', '--abort'); } catch {}
        throw new Error("Les changements de Claude Code ne s'assemblent pas avec la version principale. Demande à Claude de les reprendre.");
      }
    }
    sha = git(dossier, 'rev-parse', 'HEAD');
  } catch (e) {
    try { if (git(dossier, 'rev-parse', '--abbrev-ref', 'HEAD') !== origine) git(dossier, 'checkout', '-q', origine); } catch {}
    return fin(p, t, debut, 'bloquee', e.message);
  }

  const journal = journalDe(t);
  taches.changer(p, t.id, { statut: 'en_cours', debut: new Date().toISOString(), journal, commit_avant: sha });
  let res = { reussi: false, resume: 'Aucun résumé reçu.' };
  try {
    res = await cerveau.executerTache({
      consigne: consigneDeploiement(p, t, d, precedente, sha), dossier,
      interdits: interditsPour(dossier, INTERDITS_DEPLOIEMENT), journal, dureeMax: DUREE_MAX,
    });
  } finally {
    try { if (git(dossier, 'rev-parse', '--abbrev-ref', 'HEAD') !== origine) git(dossier, 'checkout', '-q', origine); } catch {}
  }
  const statut = res.reussi ? 'terminee' : 'echec';
  // Après un retour, c'est la version d'avant qui est en ligne.
  const enLigne = t.type === 'retour'
    ? (deploiement.historique(p).find((h) => h.destination === d.id && h.statut === 'terminee' && h.sha !== (precedente && precedente.sha)) || {}).sha
    : sha;
  if (res.reussi && enLigne) {
    deploiement.noter(p, { date: new Date().toISOString(), destination: d.id, sha: enLigne, statut, type: t.type, tache: t.id });
  }
  memoire.mettreAJourContexte(p, { fait: `${t.titre}${res.reussi ? '' : ' (échec)'}` });
  await fin(p, t, debut, statut, res.resume.slice(0, 4000));
}

// Annuler une tâche : ses changements sont défaits sur la branche de travail (un nouveau commit, rien n'est effacé).
async function annuler(p, t) {
  const dossier = projets.dossierDepot(p, t.dossier);
  const resultat = (r, statut = 'faite') => taches.changer(p, t.id, { annulation: statut, annulation_resultat: r });
  const probleme = verifierDossier(p, t, dossier);
  if (probleme) return resultat(probleme, 'impossible');
  if (!t.commit_avant || !t.commit_apres || t.commit_avant === t.commit_apres) return resultat("Cette tâche n'avait rien changé.");
  const origine = git(dossier, 'rev-parse', '--abbrev-ref', 'HEAD');
  try {
    git(dossier, 'checkout', '-q', BRANCHE);
    try {
      git(dossier, 'revert', '--no-edit', `${t.commit_avant}..${t.commit_apres}`);
    } catch {
      try { git(dossier, 'revert', '--abort'); } catch {}
      throw new Error("D'autres tâches ont modifié les mêmes endroits depuis : demande à Claude de défaire ce travail.");
    }
    const deja = git(dossier, 'branch', '--contains', t.commit_apres, '--list', 'main');
    resultat(deja
      ? "Tâche annulée sur la copie de travail. Elle était déjà dans la version principale : fais une mise en ligne (ou une mise à jour) pour que l'annulation y arrive aussi."
      : 'Tâche annulée : son travail est défait.');
    memoire.mettreAJourContexte(p, { fait: `Annulé : ${t.titre}` });
    await prevenir(`${p.nom} : tâche annulée`, t.titre);
  } catch (e) {
    resultat(e.message, 'impossible');
  } finally {
    try { if (git(dossier, 'rev-parse', '--abbrev-ref', 'HEAD') !== origine) git(dossier, 'checkout', '-q', origine); } catch {}
  }
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
    // Une chose à la fois, tous projets confondus : d'abord les annulations demandées, puis les tâches.
    for (;;) {
      let suivante = null;
      for (const p of projetsPresents()) {
        const liste = taches.lire(p);
        const t = liste.find((x) => x.annulation === 'demandee') || liste.find((x) => x.cochee && x.statut === 'en_attente');
        if (t) { suivante = { p, t }; break; }
      }
      if (!suivante) break;
      const { p, t } = suivante;
      console.log('Tâche', p.nom, t.id, t.titre);
      try {
        if (t.annulation === 'demandee') await annuler(p, t);
        else if (t.type === 'deploiement' || t.type === 'retour') await deployer(p, t);
        else await executer(p, t);
      } catch (e) {
        if (t.annulation === 'demandee') taches.changer(p, t.id, { annulation: 'impossible', annulation_resultat: e.message });
        else taches.changer(p, t.id, { statut: 'echec', resultat: 'Erreur de Janova : ' + e.message });
      }
    }
  } finally {
    occupe = false;
  }
}

console.log(`Exécuteur Janova démarré (cerveau : ${cerveau.nom}).`);
tour();
setInterval(tour, 15000);
