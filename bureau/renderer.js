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
// Le terminal n'est lancé qu'à la première ouverture de son onglet, ou par « Relancer ».
let terminalDemarre = false;
function demarrerTerminal() {
  terminalDemarre = true;
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
  terminalDemarre = false;
  montrerOnglet('journal');
  remplirDepots();
  chargerTaches();
  chargerOnglets();
  chargerNotes();
  verifierDeploiement();
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

// Affiche un message de Claude ; les blocs janova-tache / -projet / -destination deviennent des cartes avec Oui / Non.
function afficherClaude(vue, fini) {
  const morceaux = vue.message.texte.split(/```janova-(tache|projet|destination)\s*\n([\s\S]*?)(?:```|$)/);
  vue.el.innerHTML = '';
  let n = 0;
  for (let i = 0; i < morceaux.length; i += 3) {
    if (morceaux[i].trim()) vue.el.insertAdjacentHTML('beforeend', rendreTexte(morceaux[i]));
    if (i + 2 >= morceaux.length) break;
    const genre = morceaux[i + 1];
    const attente = { tache: 'Rédaction de la tâche…', projet: 'Préparation du projet…', destination: 'Préparation de la mise en ligne…' };
    vue.el.append(fini ? carte(genre, morceaux[i + 2], vue, n) : el('div', 'etat', attente[genre]));
    n++;
  }
  if (!fini && vue.outil) vue.el.append(el('div', 'etat', vue.outil));
  if (!vue.message.texte && !fini) vue.el.append(el('div', 'etat', 'Janova réfléchit…'));
  if (fini && vue.message.couche === 'noyau') vue.el.append(el('div', 'couche', '⚡ Janova a répondu seule, sans Claude'));
  if (fini && vue.message.retenu) vue.el.append(el('div', 'couche', 'Retenu : Janova répondra seule la prochaine fois.'));
  else if (fini && vue.message.retenable) vue.el.append(boutonRetenir(vue));
  $('#messages').scrollTop = 1e9;
}

// « Retenir » : la réponse de Claude devient un réflexe du noyau (rien n'est retenu sans ce clic).
function boutonRetenir(vue) {
  const b = el('button', 'lien retenir', 'Retenir');
  b.title = 'Janova gardera cette réponse et répondra seule à la même question';
  b.onclick = async () => {
    b.disabled = true;
    const r = await janova.chat.retenir(vue.index);
    if (r && r.appris) {
      vue.message.retenu = true;
      b.replaceWith(el('div', 'couche', 'Retenu : Janova répondra seule la prochaine fois.'));
    } else {
      b.disabled = false;
      b.after(el('div', 'etat', (r && r.erreur) || 'Impossible de retenir cette réponse.'));
    }
  };
  return b;
}

function carte(genre, json, vue, n) {
  const c = el('div', 'carte-tache');
  let d;
  try { d = JSON.parse(json); } catch { c.append(el('div', 'etat', 'Illisible, demande à Claude de le réécrire.')); return c; }
  if (genre === 'tache') {
    c.append(el('div', 't', d.titre));
    if (d.dossier) c.append(el('div', 'd', 'Partie : ' + d.dossier));
    c.append(el('div', 'i', d.instructions));
  } else if (genre === 'destination') {
    c.append(el('div', 't', 'Mise en ligne : ' + d.nom), el('div', 'd', (d.type || '') + (d.verification ? ' · ' + d.verification : '')), el('div', 'i', d.description || ''));
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
      destination: { oui: '✔ Enregistrée : le bouton « Mettre en ligne » la propose.', non: '✖ Pas enregistrée.' },
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
  } else if (genre === 'destination') {
    const oui = el('button', '', 'Oui, enregistrer');
    oui.onclick = async () => {
      if (!projet || projet.id !== discussion.projet) return alert('Ouvre d\'abord ce projet dans le menu en haut.');
      const r = await janova.deploiement.enregistrer(d);
      if (r.erreur) return boutons.append(el('span', 'texte-erreur', r.erreur));
      verifierDeploiement();
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
janova.chat.surFin((erreur, couche, retenable) => {
  if (!actuel) return;
  if (couche) actuel.message.couche = couche;
  if (retenable) actuel.message.retenable = true;
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
  // Une mise en ligne ne se recoche pas : elle demande un nouveau feu vert, par le bouton « Mettre en ligne ».
  case_.disabled = t.statut === 'en_cours' || t.statut === 'terminee' || !!t.type;
  case_.title = t.cochee ? 'Décocher pour mettre en pause' : 'Cocher pour que Claude Code la fasse';
  case_.onchange = async () => {
    await janova.taches.changer(t.id, { cochee: case_.checked, relancer: case_.checked });
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
  if (t.proposee) {
    const idee = el('span', 'badge idee', 'Idée de Claude');
    idee.title = 'Proposée par Claude Code après une tâche. Coche-la si tu la veux, ✕ pour la rejeter.';
    meta.append(idee);
  }
  if (projet.groupe) meta.append(el('span', '', t.dossier || 'aucune partie choisie'));
  if (t.fin) meta.append(el('span', '', dateCourte(t.fin) + (t.duree_s ? ' · ' + Math.max(1, Math.round(t.duree_s / 60)) + ' min' : '')));
  li.append(ligne, meta);
  if (ouvertes.has(t.id) || ((t.statut === 'bloquee' || t.statut === 'echec') && t.resultat)) {
    const det = el('div', 'details');
    if (t.resultat) det.append(el('h4', '', 'Résultat'), el('div', '', t.resultat));
    if (ouvertes.has(t.id) && t.instructions && t.instructions !== t.titre) det.append(el('h4', '', 'Instructions'), el('div', '', t.instructions));
    if (det.childNodes.length) li.append(det);
  }
  // Retour en arrière en un clic : défaire une tâche qui a cassé quelque chose.
  if (t.annulation) {
    const textes = { demandee: 'Annulation en cours…', faite: '↩ ' + (t.annulation_resultat || 'Tâche annulée.'), impossible: '⚠ ' + (t.annulation_resultat || 'Annulation impossible.') };
    li.append(el('div', 'etat', textes[t.annulation]));
  } else if (t.statut === 'terminee' && !t.type && t.commit_apres && t.commit_apres !== t.commit_avant && ouvertes.has(t.id)) {
    const b = el('button', 'annuler', '↩ Annuler cette tâche');
    b.onclick = async () => {
      if (!confirm('Défaire tout ce que cette tâche a changé ?')) return;
      await janova.taches.annuler(t.id);
      chargerTaches();
    };
    li.append(b);
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

// --- Onglets du centre : terminal, journal, notes, et les outils web du projet ---
// Une fenêtre web n'est chargée qu'au moment où on l'ouvre (peu d'énergie), et fermée au changement de projet.
let ongletActif = 'journal';
let outilsWeb = [];
const vuesWeb = new Map();

function montrerOnglet(id) {
  ongletActif = id;
  document.querySelectorAll('#onglets .onglet').forEach((b) => b.classList.toggle('actif', b.dataset.onglet === id));
  $('#vue-terminal').hidden = id !== 'terminal';
  $('#vue-journal').hidden = id !== 'journal';
  $('#vue-notes').hidden = id !== 'notes';
  $('#vue-recherche').hidden = id !== 'recherche';
  $('#terminal-relancer').hidden = id !== 'terminal';
  const outil = outilsWeb.find((o) => o.id === id);
  $('#outils-web').hidden = !outil;
  if (outil && !vuesWeb.has(id)) {
    const w = document.createElement('webview');
    w.setAttribute('partition', 'persist:web');
    w.setAttribute('src', outil.adresse);
    $('#vues-web').append(w);
    vuesWeb.set(id, w);
  }
  for (const [cle, w] of vuesWeb) w.hidden = cle !== id;
  if (id === 'terminal') setTimeout(() => { ajusterTerminal(); if (!terminalDemarre) demarrerTerminal(); }, 0);
  if (id === 'journal') rafraichirJournal();
  if (id === 'recherche') rafraichirRecherche();
}

async function chargerOnglets() {
  for (const w of vuesWeb.values()) w.remove();
  vuesWeb.clear();
  outilsWeb = await janova.liens.lire();
  const zone = $('#onglets-web');
  zone.innerHTML = '';
  for (const o of outilsWeb) {
    const b = el('button', 'onglet', o.nom);
    b.dataset.onglet = o.id;
    b.title = o.adresse;
    zone.append(b);
  }
  document.querySelectorAll('#onglets .onglet').forEach((b) => { b.onclick = () => montrerOnglet(b.dataset.onglet); });
  if (!['terminal', 'journal', 'notes', 'recherche'].includes(ongletActif)) montrerOnglet('journal');
}
$('#web-retour').onclick = () => { const w = vuesWeb.get(ongletActif); if (w && w.canGoBack()) w.goBack(); };
$('#web-recharger').onclick = () => { const w = vuesWeb.get(ongletActif); if (w) w.reload(); };

// --- Journal en direct ---
let suivi = { id: null, fichier: null, position: 0, lignes: [] };
const minutes = (s) => (s < 60 ? `${Math.max(1, Math.round(s))} s` : `${Math.round(s / 60)} min`);

async function rafraichirJournal() {
  const { enCours, taches } = await janova.journal.historique();
  document.querySelector('[data-onglet=journal]').classList.toggle('tourne', !!enCours);
  if (ongletActif !== 'journal') return;
  const direct = $('#journal-direct');
  if (!enCours) {
    suivi = { id: null, fichier: null, position: 0, lignes: [] };
    direct.className = 'etat';
    direct.textContent = 'Rien ne tourne en ce moment.';
  } else {
    if (suivi.id !== enCours.id) suivi = { id: enCours.id, fichier: enCours.journal, position: 0, lignes: [] };
    if (suivi.fichier) {
      const r = await janova.journal.lire({ fichier: suivi.fichier, position: suivi.position });
      suivi.position = r.position;
      suivi.lignes.push(...r.lignes);
    }
    direct.className = '';
    direct.innerHTML = '';
    const depuis = (Date.now() - new Date(enCours.debut).getTime()) / 1000;
    direct.append(el('div', 'tete', `${enCours.projetNom} · ${enCours.titre} · depuis ${minutes(depuis)}`));
    const ol = el('ol');
    for (const l of suivi.lignes.slice(-60)) ol.append(el('li', l.genre, l.texte.length > 300 ? l.texte.slice(0, 300) + '…' : l.texte));
    if (!suivi.lignes.length) ol.append(el('li', 'texte', 'Démarrage…'));
    direct.append(ol);
    ol.scrollTop = 1e9;
  }
  const ul = $('#journal-historique');
  const ouverts = new Set([...ul.querySelectorAll('li.ouvert')].map((li) => li.dataset.id));
  ul.innerHTML = '';
  for (const t of taches.slice(0, 100)) {
    const li = el('li');
    li.dataset.id = t.id;
    const l1 = el('div', 'l1');
    l1.append(el('span', 'badge ' + t.statut, STATUTS[t.statut] || t.statut), el('span', 't', t.titre));
    li.append(l1, el('div', 'l2', [t.projetNom, dateCourte(t.fin || t.debut), t.duree_s ? minutes(t.duree_s) : ''].filter(Boolean).join(' · ')));
    if (ouverts.has(t.id) && t.resultat) { li.classList.add('ouvert'); li.append(el('div', 'res', t.resultat)); }
    li.onclick = () => { li.classList.toggle('ouvert'); rafraichirJournal(); };
    ul.append(li);
  }
  if (!taches.length) ul.append(el('li', 'etat', 'Aucune tâche faite pour l\'instant.'));
}
setInterval(rafraichirJournal, 2000);
janova.telephone.sujet().then((sujet) => {
  $('#telephone').textContent = `Notifications sur ton téléphone : installe l'application gratuite « ntfy », puis abonne-toi au sujet ${sujet}`;
});

// --- Notes et mémoire du projet (enregistrées toutes seules) ---
let minuteurNotes = null;
async function chargerNotes() {
  const d = await janova.notes.lire();
  if (!d) return;
  $('#notes-perso').value = d.notes;
  $('#notes-contexte').value = d.contexte;
}
for (const [id, champ] of [['#notes-perso', 'notes'], ['#notes-contexte', 'contexte']]) {
  $(id).addEventListener('input', () => {
    clearTimeout(minuteurNotes);
    minuteurNotes = setTimeout(() => janova.notes.ecrire({ [champ]: $(id).value }), 700);
  });
}

// --- Recherche : la curiosité de Janova (gratuite, sans Claude) ---
// Tout ce qui vient d'internet est affiché comme du texte (textContent), jamais comme du code.
let rechercheDirecte = null; // les étapes de la recherche en cours
const lienWeb = (adresse, texte) => {
  const a = el('a', 'lien-web', texte || adresse);
  a.href = '#';
  a.title = adresse;
  a.onclick = (e) => { e.preventDefault(); janova.liens.ouvrir(adresse); };
  return a;
};

function afficherDirect() {
  const zone = $('#recherche-direct');
  zone.innerHTML = '';
  if (!rechercheDirecte) {
    zone.className = 'etat';
    zone.textContent = 'Aucune recherche en cours.';
    return;
  }
  zone.className = '';
  const ol = el('ol');
  for (const e of rechercheDirecte) {
    if (e.etape === 'sujet') zone.append(el('div', 'tete', `Je cherche : ${e.sujet}`), el('div', 'pourquoi', `Pourquoi : ${e.pourquoi}`));
    if (e.etape === 'lecture') { const li = el('li', 'texte', 'Je lis '); li.append(lienWeb(e.adresse, new URL(e.adresse).hostname)); ol.append(li); }
    if (e.etape === 'erreur') ol.append(el('li', 'erreur', `${e.source} : ${e.message}`));
    if (e.etape === 'resultat') ol.append(el('li', 'fin', 'Terminé : découverte enregistrée.'));
    if (e.etape === 'rien') ol.append(el('li', 'fin', e.raison));
  }
  if (!rechercheDirecte.length) ol.append(el('li', 'texte', 'Démarrage…'));
  zone.append(ol);
}

function afficherDecouverte(d) {
  const li = el('li');
  const l1 = el('div', 'l1');
  l1.append(el('span', 't', d.sujet), el('span', 'quand', dateCourte(d.date)));
  li.append(l1, el('div', 'pourquoi', 'Pourquoi : ' + d.pourquoi));
  const ul = el('ul', 'appris');
  for (const l of (d.appris || []).slice(0, 5)) ul.append(el('li', '', l));
  li.append(ul);
  const sources = el('div', 'sources');
  for (const s of (d.sources || []).filter((s) => /^https:\/\//.test(s.adresse || ''))) {
    sources.append(lienWeb(s.adresse, `${s.source} : ${s.titre}`));
  }
  li.append(sources);
  if (d.resume_par === 'ollama') li.append(el('div', 'couche', 'Résumé par le modèle local (Ollama)'));
  return li;
}

// Une fiche de connaissances : le sujet en titre, et en dépliant ce qui est appris et les sources.
function afficherFiche(f) {
  const li = el('li');
  const details = el('details');
  const resume = el('summary');
  const n = f.explorations || 0;
  resume.append(el('span', 't', f.nom), el('span', 'quand', `${n} exploration${n > 1 ? 's' : ''}, la dernière ${dateCourte(f.derniere)}`));
  details.append(resume);
  const ul = el('ul', 'appris');
  for (const l of f.appris || []) ul.append(el('li', '', l));
  const sources = el('div', 'sources');
  for (const s of (f.sources || []).filter((s) => /^https:\/\//.test(s.adresse || ''))) {
    sources.append(lienWeb(s.adresse, `${s.source} : ${s.titre}`));
  }
  details.append(ul, sources);
  li.append(details);
  return li;
}

// Une piste pour m'améliorer : la phrase de Janova, le lien, et deux boutons. Rien n'est créé sans clic.
function afficherPiste(p) {
  const li = el('li');
  const l1 = el('div', 'l1');
  const inspirer = el('button', 'petit', 'M\'en inspirer');
  inspirer.title = 'Ajouter au projet Janova une tâche non cochée pour étudier ce projet';
  const ecarter = el('button', 'petit', 'Écarter');
  ecarter.title = 'Ne plus me proposer cette piste';
  const agir = (bouton, fn) => async () => {
    inspirer.disabled = ecarter.disabled = true;
    $('#pistes-erreur').textContent = '';
    const r = await fn(p.id);
    if (r.erreur) { $('#pistes-erreur').textContent = r.erreur; inspirer.disabled = ecarter.disabled = false; return; }
    if (bouton === inspirer) $('#pistes-erreur').textContent = 'Tâche ajoutée (non cochée) au projet Janova.';
    rafraichirRecherche();
  };
  inspirer.onclick = agir(inspirer, janova.curiosite.inspirer);
  ecarter.onclick = agir(ecarter, janova.curiosite.ecarterPiste);
  l1.append(el('span', 't', p.phrase), inspirer, ecarter);
  const details = [p.source, p.source === 'GitHub' ? `${p.etoiles} étoile${p.etoiles > 1 ? 's' : ''}` : '', p.licence ? `licence ${p.licence}` : (p.source === 'GitHub' ? 'licence inconnue' : '')];
  const sources = el('div', 'sources');
  if (/^https:\/\//.test(p.adresse || '')) sources.append(lienWeb(p.adresse, p.titre));
  li.append(l1, el('div', 'pourquoi', details.filter(Boolean).join(' · ')), sources);
  return li;
}

const afficherSituation = (s) => { $('#curiosite-situation').textContent = s ? s.texte : ''; };

async function rafraichirRecherche() {
  const etat = await janova.curiosite.etat();
  const active = etat.reglages.active;
  const bouton = $('#curiosite-interrupteur');
  bouton.textContent = active ? 'Curiosité : en marche' : 'Curiosité : en pause';
  bouton.classList.toggle('actif', active);
  $('#curiosite-explication').textContent = active
    ? `Je cherche quand l'ordinateur est inactif depuis ${etat.reglages.inactiviteMin} min, jamais pendant une tâche : une recherche après l'autre, au plus ${etat.reglages.maxParHeure} par heure (sur batterie, une toutes les ${etat.reglages.intervalleMin} min).`
    : 'En pause : je ne lis rien sur internet tout seul.';
  rechercheDirecte = etat.enCours ? etat.enCours.evenements : rechercheDirecte && rechercheDirecte.some((e) => e.etape === 'resultat' || e.etape === 'rien') ? rechercheDirecte : null;
  $('#curiosite-chercher').disabled = !!etat.enCours;
  afficherSituation(etat.situation);
  afficherDirect();
  const ulF = $('#recherche-fiches');
  ulF.innerHTML = '';
  for (const f of etat.connaissances || []) ulF.append(afficherFiche(f));
  if (!(etat.connaissances || []).length) ulF.append(el('li', 'etat', 'Aucune fiche pour l\'instant.'));
  const ulP = $('#recherche-pistes');
  ulP.innerHTML = '';
  for (const p of etat.pistes || []) ulP.append(afficherPiste(p));
  if (!(etat.pistes || []).length) ulP.append(el('li', 'etat', 'Aucune piste pour l\'instant.'));
  const ulS = $('#recherche-sujets');
  ulS.innerHTML = '';
  for (const s of etat.sujets.slice(0, 12)) {
    const li = el('li');
    const l1 = el('div', 'l1');
    const barre = el('span', 'interet');
    barre.append(el('span'));
    barre.firstChild.style.width = Math.round(s.interet * 100) + '%';
    barre.title = `Intérêt : ${Math.round(s.interet * 100)} %`;
    const ecarter = el('button', 'petit', 'Écarter');
    ecarter.title = 'Ne plus chercher sur ce sujet';
    ecarter.onclick = async () => { ecarter.disabled = true; await janova.curiosite.ecarter(s.nom); rafraichirRecherche(); };
    l1.append(el('span', 't', s.nom), barre, ecarter);
    li.append(l1, el('div', 'pourquoi', s.pourquoi));
    ulS.append(li);
  }
  if (!etat.sujets.length) ulS.append(el('li', 'etat', 'Aucun sujet pour l\'instant.'));
  const ulD = $('#recherche-decouvertes');
  ulD.innerHTML = '';
  for (const d of etat.decouvertes) ulD.append(afficherDecouverte(d));
  if (!etat.decouvertes.length) ulD.append(el('li', 'etat', 'Aucune découverte pour l\'instant.'));
}

$('#curiosite-interrupteur').onclick = async () => {
  const { active } = (await janova.curiosite.etat()).reglages;
  await janova.curiosite.activer(!active);
  rafraichirRecherche();
};
$('#curiosite-chercher').onclick = async () => {
  $('#curiosite-chercher').disabled = true;
  if (!(await janova.curiosite.chercher())) {
    $('#curiosite-chercher').disabled = false;
    $('#sujet-erreur').textContent = 'Pas maintenant : une recherche ou une tâche de Claude Code est en cours.';
  }
};
$('#sujet-form').onsubmit = async (e) => {
  e.preventDefault();
  const nom = $('#sujet-saisie').value.trim();
  $('#sujet-erreur').textContent = '';
  if (!nom) return;
  const r = await janova.curiosite.suggerer(nom);
  const res = r.ok || {};
  if (r.erreur || !res.ok) { $('#sujet-erreur').textContent = r.erreur || res.erreur; return; }
  $('#sujet-saisie').value = '';
  rafraichirRecherche();
};
janova.curiosite.surEvenement((e) => {
  if (e.etape === 'situation') { if (ongletActif === 'recherche') afficherSituation(e); return; }
  if (e.etape === 'debut') rechercheDirecte = [];
  else if (e.etape !== 'fin' && rechercheDirecte) rechercheDirecte.push(e);
  document.querySelector('[data-onglet=recherche]').classList.toggle('tourne', e.etape !== 'fin');
  if (ongletActif !== 'recherche') return;
  if (e.etape === 'fin') rafraichirRecherche();
  else afficherDirect();
});

// --- Commande vocale : la voix est transcrite sur le PC, rien ne part sur internet ---
let enregistrement = null;

function enWav(morceaux, frequence) {
  // Rassemble l'enregistrement, le ramène à 16 kHz mono et l'emballe en WAV (ce que lit le moteur de voix).
  const total = morceaux.reduce((n, m) => n + m.length, 0);
  const brut = new Float32Array(total);
  let i = 0;
  for (const m of morceaux) { brut.set(m, i); i += m.length; }
  const pas = frequence / 16000;
  const n = Math.floor(total / pas);
  const donnees = new DataView(new ArrayBuffer(44 + n * 2));
  const ecrireTexte = (o, t) => [...t].forEach((c, k) => donnees.setUint8(o + k, c.charCodeAt(0)));
  ecrireTexte(0, 'RIFF'); donnees.setUint32(4, 36 + n * 2, true); ecrireTexte(8, 'WAVE'); ecrireTexte(12, 'fmt ');
  donnees.setUint32(16, 16, true); donnees.setUint16(20, 1, true); donnees.setUint16(22, 1, true);
  donnees.setUint32(24, 16000, true); donnees.setUint32(28, 32000, true); donnees.setUint16(32, 2, true); donnees.setUint16(34, 16, true);
  ecrireTexte(36, 'data'); donnees.setUint32(40, n * 2, true);
  for (let k = 0; k < n; k++) {
    const v = Math.max(-1, Math.min(1, brut[Math.floor(k * pas)]));
    donnees.setInt16(44 + k * 2, v < 0 ? v * 0x8000 : v * 0x7fff, true);
  }
  return donnees.buffer;
}

async function demarrerMicro() {
  const flux = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true } });
  const ctx = new AudioContext();
  const source = ctx.createMediaStreamSource(flux);
  const capteur = ctx.createScriptProcessor(4096, 1, 1);
  const morceaux = [];
  capteur.onaudioprocess = (e) => morceaux.push(new Float32Array(e.inputBuffer.getChannelData(0)));
  source.connect(capteur);
  capteur.connect(ctx.destination);
  enregistrement = { flux, ctx, capteur, morceaux };
}

async function arreterMicro() {
  const { flux, ctx, capteur, morceaux } = enregistrement;
  enregistrement = null;
  capteur.disconnect();
  flux.getTracks().forEach((t) => t.stop());
  const frequence = ctx.sampleRate;
  await ctx.close();
  return enWav(morceaux, frequence);
}

$('#micro').onclick = async () => {
  const b = $('#micro');
  if (!enregistrement) {
    try {
      await demarrerMicro();
    } catch {
      return alert('Je n\'ai pas accès au micro. Vérifie qu\'il est branché et autorisé.');
    }
    b.classList.add('enregistre');
    b.textContent = '■ Finir';
    return;
  }
  b.classList.remove('enregistre');
  b.textContent = 'Écoute…';
  b.disabled = true;
  const r = await janova.voix.transcrire(await arreterMicro());
  b.disabled = false;
  b.textContent = '🎤 Parler';
  if (r.erreur) return alert(r.erreur);
  const zone = $('#chat-saisie');
  zone.value = (zone.value.trim() ? zone.value.trim() + ' ' : '') + r.ok;
  zone.focus();
};
janova.voix.disponible().then((ok) => { $('#micro').hidden = !ok; });

// --- Mise en ligne : Janova montre ce qui va partir, et attend le feu vert ---
const dialogueDeployer = $('#dialogue-deployer');
let destinationsProjet = [];
let destinationChoisie = null;

async function verifierDeploiement() {
  destinationsProjet = await janova.deploiement.destinations();
  $('#deployer-bouton').hidden = !destinationsProjet.length;
}

function ouvrirDeploiement() {
  const choix = $('#deployer-choix');
  choix.innerHTML = '';
  $('#deployer-resume').innerHTML = '';
  $('#deployer-erreur').textContent = '';
  $('#deployer-go').disabled = true;
  $('#deployer-revenir').hidden = true;
  destinationChoisie = null;
  for (const d of destinationsProjet) {
    const label = el('label');
    const radio = el('input');
    radio.type = 'radio';
    radio.name = 'destination';
    radio.onchange = () => choisirDestination(d);
    label.append(radio, document.createTextNode(d.nom + (d.derniere ? ` (en ligne depuis le ${dateCourte(d.derniere.date)})` : '')));
    choix.append(label);
  }
  dialogueDeployer.showModal();
}

async function choisirDestination(d) {
  destinationChoisie = d;
  const zone = $('#deployer-resume');
  zone.innerHTML = '';
  $('#deployer-erreur').textContent = '';
  $('#deployer-go').disabled = true;
  const r = await janova.deploiement.resume(d.id);
  if (r.erreur) { $('#deployer-erreur').textContent = r.erreur; return; }
  const s = r.ok;
  zone.append(el('p', '', s.description));
  if (s.changements.length) {
    zone.append(el('p', '', s.premiere ? 'Dernières modifications :' : 'Ce qui va changer en ligne :'));
    const ul = el('ul');
    for (const c of s.changements) ul.append(el('li', '', c));
    zone.append(ul);
  } else {
    zone.append(el('p', 'aide', 'Rien de nouveau depuis la dernière mise en ligne.'));
  }
  if (s.aFusionner) zone.append(el('p', 'aide', `Le travail de Claude Code (${s.aFusionner} enregistrement(s)) rejoindra d'abord la version principale.`));
  zone.append(el('p', 'aide', 'La version actuellement en ligne est gardée : tu pourras y revenir en un clic.'));
  $('#deployer-go').disabled = false;
  $('#deployer-revenir').hidden = !s.precedente;
}

$('#deployer-bouton').onclick = ouvrirDeploiement;
$('#deployer-fermer').onclick = () => dialogueDeployer.close();
async function donnerFeuVert(retour) {
  if (!destinationChoisie) return;
  const r = await janova.deploiement.feuVert({ id: destinationChoisie.id, retour });
  if (r.erreur) { $('#deployer-erreur').textContent = r.erreur; return; }
  dialogueDeployer.close();
  chargerTaches();
  montrerOnglet('journal');
}
$('#deployer-go').onclick = () => donnerFeuVert(false);
$('#deployer-revenir').onclick = () => {
  if (confirm('Remettre en ligne la version précédente de « ' + destinationChoisie.nom + ' » ?')) donnerFeuVert(true);
};
