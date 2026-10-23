// Curiosité : quand l'ordinateur est inactif, le bureau demande au noyau UNE recherche sur internet,
// gratuite et sans Claude (python3 -m janova.curiosite), et suit son avancement ligne par ligne.
// Conditions : curiosité en marche, ordinateur inactif depuis assez longtemps, aucune tâche Claude Code
// en cours, et pas plus d'une recherche par intervalle. Les réglages sont dans la mémoire unique.
const { spawn, execFile } = require('child_process');
const fs = require('fs');
const path = require('path');
const memoire = require('./memoire');
const { RACINE_NOYAU } = require('./reflexes');

const DEFAUTS = { active: true, inactiviteMin: 10, intervalleMin: 10 };
const DUREE_MAX = 5 * 60 * 1000; // une recherche qui dépasse 5 minutes est arrêtée

const dossier = () => memoire.chemin('noyau', 'curiosite');

// En marche par défaut ; l'utilisateur peut la mettre en pause (curiosite_active: false), et ce choix est gardé.
function reglages() {
  const r = memoire.reglages();
  const minutes = (v, d) => (Number.isFinite(Number(v)) && Number(v) >= 1 ? Number(v) : d);
  return {
    active: r.curiosite_active !== false,
    inactiviteMin: minutes(r.curiosite_inactivite_min, DEFAUTS.inactiviteMin),
    intervalleMin: minutes(r.curiosite_intervalle_min, DEFAUTS.intervalleMin),
  };
}
const activer = (oui) => memoire.changerReglages({ curiosite_active: !!oui });

// Peut-on lancer une recherche maintenant ? (tout est fourni en paramètre : facile à tester)
function peutLancer({ reglages: r, inactifS, tacheEnCours, enCours, derniere, maintenant }) {
  if (!r.active || enCours || tacheEnCours) return false;
  if (inactifS < r.inactiviteMin * 60) return false;
  return !derniere || maintenant - derniere >= r.intervalleMin * 60 * 1000;
}

function noyau(args, delai = 15000) {
  const racine = RACINE_NOYAU();
  if (!racine) return Promise.reject(new Error('Le noyau de Janova est introuvable.'));
  return new Promise((resolve, reject) => {
    execFile('python3', ['-m', 'janova.curiosite', ...args], {
      cwd: racine, env: { ...process.env, JANOVA_MEMOIRE: memoire.MEMOIRE }, timeout: delai,
    }, (err, out) => {
      if (err) return reject(new Error('Le noyau n’a pas répondu.'));
      try { resolve(JSON.parse(out.trim().split('\n').pop())); } catch { reject(new Error('Réponse illisible du noyau.')); }
    });
  });
}

const sujets = () => noyau(['--sujets']).then((r) => r.sujets || []);
const ecarter = (nom) => noyau(['--ecarter', String(nom)]);
const suggerer = (nom) => noyau(['--suggerer', String(nom).slice(0, 200)]);

// Les dernières découvertes, les plus récentes en haut (lues dans les fichiers AAAA-MM-JJ.jsonl).
function decouvertes(nombre = 30, fichiers = null) {
  let noms = [];
  try { noms = fichiers || fs.readdirSync(dossier()).filter((f) => /^\d{4}-\d{2}-\d{2}\.jsonl$/.test(f)).sort().reverse(); } catch {}
  const res = [];
  for (const f of noms) {
    let lignes = [];
    try { lignes = fs.readFileSync(path.join(dossier(), f), 'utf8').split('\n').filter(Boolean); } catch {}
    for (const l of lignes.reverse()) {
      try { res.push(JSON.parse(l)); } catch {}
      if (res.length >= nombre) return res;
    }
  }
  return res;
}

// Les découvertes faites entre deux instants (pour le compte rendu du matin).
function decouvertesEntre(debut, fin) {
  const jour = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}.jsonl`;
  const fichiers = [...new Set([jour(fin), jour(debut)])];
  return decouvertes(1000, fichiers).filter((d) => {
    const t = new Date(d.date).getTime();
    return t >= debut.getTime() && t < fin.getTime();
  }).reverse();
}

// Lance une recherche ; surEvenement reçoit chaque ligne JSON (sujet, lecture, erreur, resultat, rien).
function lancer(surEvenement = () => {}) {
  const racine = RACINE_NOYAU();
  if (!racine) return Promise.resolve({ etape: 'rien', raison: 'Le noyau de Janova est introuvable.' });
  return new Promise((resolve) => {
    const p = spawn('python3', ['-m', 'janova.curiosite'], {
      cwd: racine, env: { ...process.env, JANOVA_MEMOIRE: memoire.MEMOIRE }, stdio: ['ignore', 'pipe', 'ignore'],
    });
    let reste = '';
    let derniere = { etape: 'rien', raison: 'La recherche s’est arrêtée sans rien dire.' };
    const minuteur = setTimeout(() => p.kill(), DUREE_MAX);
    p.stdout.on('data', (morceau) => {
      reste += morceau;
      const lignes = reste.split('\n');
      reste = lignes.pop();
      for (const l of lignes) {
        try { derniere = JSON.parse(l); surEvenement(derniere); } catch {}
      }
    });
    p.on('error', () => {});
    p.on('close', () => { clearTimeout(minuteur); resolve(derniere); });
  });
}

// Surveille l'inactivité chaque minute et lance une recherche quand tout est réuni.
// inactiviteS() : secondes depuis la dernière action de l'utilisateur (powerMonitor.getSystemIdleTime).
function surveiller({ inactiviteS, tacheEnCours, surEvenement = () => {}, intervalle = 60 * 1000 }) {
  const etat = { enCours: null, derniere: 0 };
  const essayer = async (forcer = false) => {
    if (etat.enCours) return false;
    const ok = forcer || peutLancer({
      reglages: reglages(), inactifS: inactiviteS(), tacheEnCours: tacheEnCours(), enCours: false,
      derniere: etat.derniere, maintenant: Date.now(),
    });
    if (!ok) return false;
    etat.derniere = Date.now();
    etat.enCours = { debut: new Date().toISOString(), evenements: [] };
    surEvenement({ etape: 'debut' });
    await lancer((e) => { etat.enCours.evenements.push(e); surEvenement(e); });
    etat.enCours = null;
    surEvenement({ etape: 'fin' });
    return true;
  };
  const minuteur = setInterval(() => essayer().catch(() => {}), intervalle);
  return { etat, essayer, arreter: () => clearInterval(minuteur) };
}

module.exports = { DEFAUTS, reglages, activer, peutLancer, sujets, ecarter, suggerer, decouvertes, decouvertesEntre, lancer, surveiller };
