const $ = (s) => document.querySelector(s);
const el = (tag, cls, texte) => {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (texte != null) e.textContent = texte;
  return e;
};
const echapper = (s) => s.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
const dateCourte = (iso) =>
  iso ? new Date(iso).toLocaleString('fr-FR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : '';

let projet = null; // projet actuel
let tousProjets = [];
let discussion = null; // discussion affichée
let actuel = null; // réponse de Claude en cours d'écriture

// --- Panneaux redimensionnables ---
document.querySelectorAll('.separateur').forEach((sep) => {
  sep.addEventListener('mousedown', (e) => {
    const cible = document.getElementById(sep.dataset.cible);
    const depart = e.clientX;
    const largeur = cible.getBoundingClientRect().width;
    const bouger = (m) => {
      const delta = sep.dataset.inverse ? depart - m.clientX : m.clientX - depart;
      cible.style.flexBasis = Math.max(220, largeur + delta) + 'px';
      ajusterTerminal();
    };
    const lacher = () => { removeEventListener('mousemove', bouger); removeEventListener('mouseup', lacher); };
    addEventListener('mousemove', bouger);
    addEventListener('mouseup', lacher);
    e.preventDefault();
  });
});

// --- Terminal ---
const term = new Terminal({
  fontFamily: '"DejaVu Sans Mono", "Ubuntu Mono", monospace',
  fontSize: 13,
  cursorBlink: true,
  theme: { background: '#101216' },
});
const ajusteur = new FitAddon.FitAddon();
term.loadAddon(ajusteur);
term.open($('#terminal'));
ajusteur.fit();
term.onData((d) => janova.terminal.ecrire(d));
janova.terminal.surDonnees((d) => term.write(d));
janova.terminal.surFin(() => term.write('\r\n\x1b[90m[Terminal fermé. Clique sur « Relancer ».]\x1b[0m\r\n'));
function ajusterTerminal() {
  ajusteur.fit();
  janova.terminal.taille({ cols: term.cols, rows: term.rows });
}
new ResizeObserver(ajusterTerminal).observe($('#terminal'));
function demarrerTerminal() {
  term.reset();
  janova.terminal.demarrer({ cols: term.cols, rows: term.rows });
}
$('#terminal-relancer').onclick = () => { demarrerTerminal(); term.focus(); };

// --- Projets ---
async function chargerProjets() {
  const { projets, actuel: id } = await janova.projets.liste();
  tousProjets = projets;
  const sel = $('#projet');
  sel.innerHTML = '';
  for (const p of projets) sel.append(new Option(p.nom, p.id));
  sel.value = (projet && projet.id) || id;
  return sel.value || (projets[0] && projets[0].id);
}

async function choisirProjet(id) {
  if (actuel) { if (projet) $('#projet').value = projet.id; return; }
  $('#projet-etat').textContent = tousProjets.find((p) => p.id === id && !p.present) ? 'Téléchargement du projet…' : '';
  $('#projet').disabled = true;
  const r = await janova.projets.choisir(id);
  $('#projet').disabled = false;
  if (r.erreur) {
    $('#projet-etat').textContent = 'Impossible d\'ouvrir ce projet : ' + r.erreur;
    if (projet) $('#projet').value = projet.id;
    return;
  }
  $('#projet-etat').textContent = '';
  projet = r.ok;
  $('#projet').value = projet.id;
  demarrerTerminal();
  remplirDepots();
  chargerTaches();
  await nouvelleDiscussion(projet.id);
}

$('#projet').onchange = () => choisirProjet($('#projet').value);
janova.projets.surChangement(chargerProjets);

const dialogue = $('#dialogue-projet');
$('#projet-nouveau').onclick = () => ouvrirCreation();
function ouvrirCreation(nom = '', description = '') {
  $('#projet-nom').value = nom;
  $('#projet-description').value = description;
  $('#projet-erreur').textContent = '';
  dialogue.showModal();
}
$('#form-projet').onsubmit = async (e) => {
  if (e.submitter && e.submitter.value === 'annuler') return;
  e.preventDefault();
  const bouton = $('#projet-creer');
  bouton.disabled = true;
  $('#projet-erreur').textContent = '';
  bouton.textContent = 'Création…';
  const r = await janova.projets.creer({ nom: $('#projet-nom').value, description: $('#projet-description').value });
  if (!r.erreur) await ouvrirNouveauProjet(r.ok);
  bouton.disabled = false;
  bouton.textContent = 'Créer';
  if (r.erreur) $('#projet-erreur').textContent = r.erreur;
  else dialogue.close();
};
async function ouvrirNouveauProjet(p) {
  await chargerProjets();
  await choisirProjet(p.id);
}

// --- Rendu simple du texte de Claude (gras, code, listes, paragraphes) ---
function enLigne(s) {
  return echapper(s)
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
}
function rendreTexte(txt) {
  const html = [];
  txt.split(/```/).forEach((b, i) => {
    if (i % 2 === 1) {
      html.push('<pre><code>' + echapper(b.replace(/^[\w-]*\n/, '')) + '</code></pre>');
      return;
    }
    for (const para of b.split(/\n{2,}/)) {
      if (!para.trim()) continue;
      const lignes = para.split('\n');
      if (lignes.every((l) => /^\s*([-*]|\d+\.)\s/.test(l) || !l.trim())) {
        html.push('<ul>' + lignes.filter((l) => l.trim()).map((l) => '<li>' + enLigne(l.replace(/^\s*([-*]|\d+\.)\s/, '')) + '</li>').join('') + '</ul>');
      } else {
        html.push('<p>' + lignes.map(enLigne).join('<br>') + '</p>');
      }
    }
  });
  return html.join('');
}

// --- Chat ---
function afficherEnTete() {
  const p = discussion && discussion.projet ? tousProjets.find((x) => x.id === discussion.projet) : null;
  const contexte = p ? p.nom : 'Question générale';
  const titre = discussion && discussion.messages.length ? discussion.titre : 'Nouvelle discussion';
  $('#discussion-titre').textContent = contexte + ' · ' + titre;
  $('#discussion-titre').title = $('#discussion-titre').textContent;
}

function bulle(cls, texte) {
  const m = el('div', 'msg ' + cls, texte);
  $('#messages').append(m);
  $('#messages').scrollTop = 1e9;
  return m;
}

// Affiche un message de Claude ; les blocs janova-tache / janova-projet deviennent des cartes avec Oui / Non.
function afficherClaude(vue, fini) {
  const morceaux = vue.message.texte.split(/```janova-(tache|projet)\s*\n([\s\S]*?)(?:```|$)/);
  vue.el.innerHTML = '';
  let n = 0;
  for (let i = 0; i < morceaux.length; i += 3) {
    if (morceaux[i].trim()) vue.el.insertAdjacentHTML('beforeend', rendreTexte(morceaux[i]));
    if (i + 2 >= morceaux.length) break;
    const genre = morceaux[i + 1];
    vue.el.append(fini ? carte(genre, morceaux[i + 2], vue, n) : el('div', 'etat', genre === 'tache' ? 'Rédaction de la tâche…' : 'Préparation du projet…'));
    n++;
  }
  if (!fini && vue.outil) vue.el.append(el('div', 'etat', vue.outil));
  if (!vue.message.texte && !fini) vue.el.append(el('div', 'etat', 'Janova réfléchit…'));
  if (fini && vue.message.couche === 'noyau') vue.el.append(el('div', 'couche', '⚡ Janova a répondu seule, sans Claude'));
  $('#messages').scrollTop = 1e9;
}

function carte(genre, json, vue, n) {
  const c = el('div', 'carte-tache');
  let d;
  try { d = JSON.parse(json); } catch { c.append(el('div', 'etat', 'Illisible, demande à Claude de le réécrire.')); return c; }
  if (genre === 'tache') {
    c.append(el('div', 't', d.titre));
    if (d.dossier) c.append(el('div', 'd', 'Partie : ' + d.dossier));
    c.append(el('div', 'i', d.instructions));
  } else {
    c.append(el('div', 't', 'Nouveau projet : ' + d.nom), el('div', 'i', d.description || ''));
  }
  const boutons = el('div', 'boutons');
  const rep = (vue.message.reponses || {})[n];
  const repondre = async (r) => {
    vue.message.reponses = { ...(vue.message.reponses || {}), [n]: r };
    await janova.discussions.reponse({ message: vue.index, bloc: n, reponse: r });
    afficherClaude(vue, true);
  };
  if (rep) {
    const textes = {
      tache: { oui: '✔ Ajoutée et cochée : Claude Code va la faire.', non: '✖ Pas lancée.' },
      projet: { oui: '✔ Projet créé.', non: '✖ Pas créé.' },
    };
    boutons.append(el('span', 'etat', textes[genre][rep] || rep));
  } else if (genre === 'tache') {
    const oui = el('button', '', 'Oui, démarrer');
    oui.onclick = async () => {
      if (!projet || projet.id !== discussion.projet) return alert('Ouvre d\'abord ce projet dans le menu en haut.');
      await janova.taches.ajouter({ ...d, cochee: true });
      chargerTaches();
      repondre('oui');
    };
    const non = el('button', 'secondaire', 'Non');
    non.onclick = () => repondre('non');
    boutons.append(oui, non);
  } else {
    const oui = el('button', '', 'Oui, créer');
    oui.onclick = async () => {
      oui.disabled = true;
      oui.textContent = 'Création…';
      const r = await janova.projets.creer({ nom: d.nom, description: d.description });
      if (r.erreur) {
        oui.disabled = false;
        oui.textContent = 'Oui, créer';
        boutons.append(el('span', 'texte-erreur', r.erreur));
        return;
      }
      await repondre('oui');
      await ouvrirNouveauProjet(r.ok);
    };
    const non = el('button', 'secondaire', 'Non');
    non.onclick = () => repondre('non');
    boutons.append(oui, non);
  }
  c.append(boutons);
  return c;
}

function afficherDiscussion() {
  $('#messages').innerHTML = '';
  discussion.messages.forEach((m, index) => {
    if (m.role === 'moi') bulle('moi', m.texte);
    else afficherClaude({ el: bulle('claude', ''), message: m, index }, true);
  });
  afficherEnTete();
}

async function nouvelleDiscussion(projetId) {
  discussion = await janova.discussions.nouvelle(projetId || null);
  afficherDiscussion();
  fermerHistorique();
  $('#chat-saisie').focus();
}

function envoyerChat() {
  const txt = $('#chat-saisie').value.trim();
  if (!txt || actuel || !discussion) return;
  if (!discussion.messages.length) discussion.titre = txt.replace(/\s+/g, ' ').slice(0, 70);
  discussion.messages.push({ role: 'moi', texte: txt });
  bulle('moi', txt);
  const message = { role: 'claude', texte: '' };
  discussion.messages.push(message);
  actuel = { el: bulle('claude', ''), message, index: discussion.messages.length - 1 };
  afficherClaude(actuel, false);
  afficherEnTete();
  $('#chat-saisie').value = '';
  $('#chat-bouton').textContent = 'Arrêter';
  janova.chat.envoyer(txt);
}
$('#chat-form').onsubmit = (e) => {
  e.preventDefault();
  if (actuel) janova.chat.stop();
  else envoyerChat();
};
$('#chat-saisie').addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); envoyerChat(); }
});
$('#chat-nouveau').onclick = () => !actuel && nouvelleDiscussion(projet && projet.id);
janova.chat.surNouveauMessage(() => {
  const m = actuel && actuel.message;
  if (m && m.texte && !m.texte.endsWith('\n\n')) m.texte += '\n\n';
});
janova.chat.surTexte((t) => {
  if (!actuel) return;
  actuel.message.texte += t;
  actuel.outil = null;
  afficherClaude(actuel, false);
});
janova.chat.surOutil((nom) => {
  if (!actuel) return;
  actuel.outil = nom === 'Read' ? 'Claude lit un fichier…' : 'Claude cherche dans le projet…';
  afficherClaude(actuel, false);
});
janova.chat.surFin((erreur, couche) => {
  if (!actuel) return;
  if (couche) actuel.message.couche = couche;
  if (!actuel.message.texte) {
    actuel.el.remove();
    discussion.messages.pop();
  } else {
    afficherClaude(actuel, true);
  }
  if (erreur) bulle('erreur', erreur);
  actuel = null;
  $('#chat-bouton').textContent = 'Envoyer';
  $('#chat-saisie').focus();
});

// --- Historique des discussions ---
let filtre = 'projet';
function fermerHistorique() { $('#historique').hidden = true; }
$('#chat-historique').onclick = () => {
  if (actuel) return;
  const h = $('#historique');
  h.hidden = !h.hidden;
  if (!h.hidden) { remplirHistorique(); $('#historique-recherche').focus(); }
};
document.querySelectorAll('.onglet').forEach((b) => {
  b.onclick = () => {
    filtre = b.dataset.filtre;
    document.querySelectorAll('.onglet').forEach((x) => x.classList.toggle('actif', x === b));
    remplirHistorique();
  };
});
$('#historique-recherche').oninput = () => remplirHistorique();
$('#historique-general').onclick = () => nouvelleDiscussion(null);

async function remplirHistorique() {
  const f = { recherche: $('#historique-recherche').value };
  if (filtre === 'projet') f.projet = projet ? projet.id : null;
  if (filtre === 'general') f.projet = null;
  const liste = await janova.discussions.liste(f);
  const ul = $('#historique-liste');
  ul.innerHTML = '';
  if (!liste.length) ul.append(el('li', 'vide', f.recherche ? 'Aucune discussion trouvée.' : 'Aucune discussion pour l\'instant.'));
  for (const d of liste) {
    const li = el('li');
    const p = d.projet ? tousProjets.find((x) => x.id === d.projet) : null;
    li.append(el('div', 't', d.titre), el('div', 'm', dateCourte(d.maj) + ' · ' + (p ? p.nom : 'Question générale') + (d.extrait ? ' · ' + d.extrait : '')));
    li.onclick = () => ouvrirDiscussion(d.id);
    ul.append(li);
  }
}

// Rouvre une discussion ; si elle appartient à un autre projet, Janova bascule sur ce projet.
async function ouvrirDiscussion(id) {
  const d = await janova.discussions.ouvrir(id);
  if (!d) return;
  if (d.projet && (!projet || projet.id !== d.projet)) {
    await choisirProjet(d.projet);
    await janova.discussions.ouvrir(id);
  }
  discussion = d;
  afficherDiscussion();
  fermerHistorique();
  $('#chat-saisie').focus();
}

// --- Tâches ---
const STATUTS = { en_attente: 'en attente', prete: 'prête', en_cours: 'en cours…', terminee: 'terminée', echec: 'échec', bloquee: 'bloquée' };
const ouvertes = new Set();

function remplirDepots() {
  const sel = $('#tache-dossier');
  sel.innerHTML = '';
  sel.hidden = !projet.groupe;
  for (const nom of projet.depots) sel.append(new Option(nom, nom));
}

async function chargerTaches() {
  if (!projet) return;
  const liste = $('#taches');
  const toutes = await janova.taches.lire();
  liste.innerHTML = '';
  const ordre = (t) => (t.statut === 'terminee' ? 1 : 0);
  for (const t of [...toutes].sort((a, b) => ordre(a) - ordre(b))) liste.append(ligneTache(t));
  if (!toutes.length) liste.append(el('li', 'vide etat', 'Aucune tâche pour ce projet.'));
}

function ligneTache(t) {
  const li = el('li', t.statut);
  const ligne = el('div', 'ligne');
  const case_ = el('input');
  case_.type = 'checkbox';
  case_.checked = t.cochee;
  case_.disabled = t.statut === 'en_cours' || t.statut === 'terminee';
  case_.title = t.cochee ? 'Décocher pour mettre en pause' : 'Cocher pour que Claude Code la fasse';
  case_.onchange = async () => {
    const champs = { cochee: case_.checked };
    if (case_.checked && (t.statut === 'echec' || t.statut === 'bloquee')) Object.assign(champs, { statut: 'en_attente', resultat: null });
    await janova.taches.changer(t.id, champs);
    chargerTaches();
  };
  const nom = el('span', 'nom', t.titre);
  nom.onclick = () => { ouvertes.has(t.id) ? ouvertes.delete(t.id) : ouvertes.add(t.id); chargerTaches(); };
  ligne.append(case_, nom);
  if (t.statut !== 'en_cours') {
    const sup = el('button', 'supprimer', '✕');
    sup.title = 'Supprimer la tâche';
    sup.onclick = async () => { if (confirm('Supprimer « ' + t.titre + ' » ?')) { await janova.taches.supprimer(t.id); chargerTaches(); } };
    ligne.append(sup);
  }
  const statut = t.statut === 'en_attente' && t.cochee ? 'prete' : t.statut;
  const meta = el('div', 'meta');
  meta.append(el('span', 'badge ' + statut, STATUTS[statut]));
  if (projet.groupe) meta.append(el('span', '', t.dossier || 'aucune partie choisie'));
  if (t.fin) meta.append(el('span', '', dateCourte(t.fin) + (t.duree_s ? ' · ' + Math.max(1, Math.round(t.duree_s / 60)) + ' min' : '')));
  li.append(ligne, meta);
  if (ouvertes.has(t.id) || ((t.statut === 'bloquee' || t.statut === 'echec') && t.resultat)) {
    const det = el('div', 'details');
    if (t.resultat) det.append(el('h4', '', 'Résultat'), el('div', '', t.resultat));
    if (ouvertes.has(t.id) && t.instructions && t.instructions !== t.titre) det.append(el('h4', '', 'Instructions'), el('div', '', t.instructions));
    if (det.childNodes.length) li.append(det);
  }
  return li;
}

$('#tache-form').onsubmit = async (e) => {
  e.preventDefault();
  const titre = $('#tache-titre').value.trim();
  if (!titre || !projet) return;
  await janova.taches.ajouter({ titre, dossier: $('#tache-dossier').value, cochee: false });
  $('#tache-titre').value = '';
  chargerTaches();
};
janova.taches.surChangement(chargerTaches);

// --- Démarrage : on rouvre le dernier projet utilisé ---
(async () => {
  const id = await chargerProjets();
  if (id) await choisirProjet(id);
  janova.projets.actualiser();
})();

// --- Mises à jour de Janova elle-même ---
let etatMaj = null;
let versionPrete = null;
const dialogueMaj = $('#dialogue-maj');

async function verifierMaj() {
  const r = await janova.maj.etat();
  if (r.erreur) return;
  etatMaj = r.ok;
  const b = $('#maj-bouton');
  b.hidden = !etatMaj.candidat && !etatMaj.precedente;
  b.textContent = etatMaj.candidat ? 'Nouvelle version de Janova' : 'Version de Janova';
  b.classList.toggle('dispo', !!etatMaj.candidat);
}

function ouvrirMaj() {
  const c = etatMaj.candidat;
  versionPrete = null;
  const contenu = $('#maj-contenu');
  contenu.innerHTML = '';
  $('#maj-erreur').textContent = '';
  $('#maj-progres').hidden = true;
  $('#maj-progres').textContent = '';
  $('#maj-titre').textContent = c ? 'Nouvelle version de Janova' : 'Version de Janova';
  if (c) {
    contenu.append(el('p', '', 'Ce qui change :'));
    const ul = el('ul');
    for (const s of c.changements) ul.append(el('li', '', s));
    contenu.append(ul, el('p', 'aide', 'Janova teste d\'abord cette version. Ta version actuelle ne change pas tant que tu n\'as pas dit oui.'));
  } else {
    contenu.append(el('p', '', 'Janova est à jour.'));
  }
  $('#maj-accord-garde-fous').hidden = !(c && c.gardeFous.length);
  $('#maj-accord').checked = false;
  $('#maj-action').hidden = !c;
  $('#maj-action').disabled = false;
  $('#maj-action').textContent = 'Tester';
  const p = etatMaj.precedente;
  $('#maj-revenir').hidden = !p;
  if (p) $('#maj-revenir').textContent = 'Revenir à la version précédente (' + dateCourte(p.creee) + ')';
  dialogueMaj.showModal();
}

$('#maj-bouton').onclick = ouvrirMaj;
$('#maj-fermer').onclick = () => dialogueMaj.close();
janova.maj.surProgres((ligne) => {
  const pre = $('#maj-progres');
  pre.hidden = false;
  pre.textContent += ligne + '\n';
  pre.scrollTop = 1e9;
});

$('#maj-action').onclick = async () => {
  const c = etatMaj.candidat;
  if (c.gardeFous.length && !$('#maj-accord').checked) {
    $('#maj-erreur').textContent = 'Coche la case pour accepter le changement des garde-fous, ou clique sur « Plus tard ».';
    return;
  }
  const bouton = $('#maj-action');
  bouton.disabled = true;
  $('#maj-erreur').textContent = '';
  if (!versionPrete) {
    bouton.textContent = 'Test en cours…';
    const r = await janova.maj.preparer();
    bouton.disabled = false;
    if (r.erreur) { bouton.textContent = 'Tester'; $('#maj-erreur').textContent = r.erreur; return; }
    versionPrete = r.ok.version;
    const fin = c.ref === 'main' ? '' : ' Ces changements rejoindront aussi la version principale de Janova, envoyée sur ton GitHub.';
    $('#maj-contenu').append(el('p', '', '✔ Tests réussis. Janova va redémarrer avec la nouvelle version.' + fin));
    bouton.textContent = 'Installer';
    return;
  }
  bouton.textContent = 'Installation…';
  const r = await janova.maj.installer(versionPrete);
  if (r.erreur) { bouton.disabled = false; bouton.textContent = 'Installer'; $('#maj-erreur').textContent = r.erreur; }
};

$('#maj-revenir').onclick = async () => {
  if (!confirm('Revenir à la version précédente de Janova ? Elle va redémarrer.')) return;
  const r = await janova.maj.revenir();
  if (r.erreur) $('#maj-erreur').textContent = r.erreur;
};

verifierMaj();
janova.taches.surChangement(verifierMaj);
