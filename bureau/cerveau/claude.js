// Cerveau « Claude » : le chat passe par Claude, les tâches par Claude Code (abonnement déjà connecté sur ce PC).
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');

const CLAUDE = path.join(os.homedir(), '.local', 'bin', 'claude');
const ENV = {
  ...process.env,
  PATH: `${path.join(os.homedir(), '.local', 'bin')}:${process.env.PATH}`,
  // git n'a pas d'identité configurée sur ce PC : même auteur que les commits déjà présents.
  GIT_AUTHOR_NAME: 'dbygadri', GIT_AUTHOR_EMAIL: 'dby.perso@gmail.com',
  GIT_COMMITTER_NAME: 'dbygadri', GIT_COMMITTER_EMAIL: 'dby.perso@gmail.com',
};

// Lit la sortie « stream-json » de Claude ligne par ligne.
function lignes(flux, fn) {
  let reste = '';
  flux.on('data', (b) => {
    reste += b.toString();
    const ls = reste.split('\n');
    reste = ls.pop();
    for (const l of ls) {
      try { fn(JSON.parse(l), l); } catch {}
    }
  });
}

function discuter({ message, session, dossier, consigne, outils = ['Read', 'Glob', 'Grep'] }, ecoute = {}) {
  const args = [
    '-p', message,
    '--output-format', 'stream-json', '--verbose', '--include-partial-messages',
    '--tools', outils.join(','), '--allowedTools', outils.join(','),
    '--append-system-prompt', consigne,
  ];
  if (session) args.push('--resume', session);
  const proc = spawn(CLAUDE, args, { cwd: dossier, env: ENV, stdio: ['ignore', 'pipe', 'pipe'] });
  let erreur = '';
  lignes(proc.stdout, (ev) => {
    if (ev.session_id) session = ev.session_id;
    if (ev.type === 'stream_event' && ev.event.type === 'content_block_delta' && ev.event.delta.type === 'text_delta') {
      ecoute.surTexte && ecoute.surTexte(ev.event.delta.text);
    } else if (ev.type === 'stream_event' && ev.event.type === 'message_start') {
      ecoute.surNouveauMessage && ecoute.surNouveauMessage();
    } else if (ev.type === 'assistant') {
      for (const c of ev.message.content || []) if (c.type === 'tool_use') ecoute.surOutil && ecoute.surOutil(c.name);
    } else if (ev.type === 'result' && ev.is_error) {
      erreur = ev.result || 'Erreur inconnue';
    }
  });
  proc.stderr.on('data', (b) => (erreur += b.toString()));
  const fin = new Promise((resolve) =>
    proc.on('close', (code) => resolve({
      session,
      erreur: code === 0 && !erreur ? null : erreur.trim().slice(-500) || `Claude s'est arrêté (code ${code}).`,
    })));
  return { arreter: () => proc.kill('SIGTERM'), fin };
}

function executerTache({ consigne, dossier, interdits, journal, dureeMax }) {
  return new Promise((resolve) => {
    const args = [
      '-p', consigne,
      '--output-format', 'stream-json', '--verbose',
      '--dangerously-skip-permissions',
      '--disallowedTools', ...interdits,
    ];
    const proc = spawn(CLAUDE, args, { cwd: dossier, env: ENV, stdio: ['ignore', 'pipe', 'pipe'] });
    const sortie = fs.createWriteStream(journal);
    let final = null;
    proc.stdout.on('data', (b) => sortie.write(b));
    lignes(proc.stdout, (ev) => { if (ev.type === 'result') final = ev; });
    proc.stderr.on('data', (b) => sortie.write(b));
    const minuteur = setTimeout(() => proc.kill('SIGTERM'), dureeMax);
    proc.on('close', (code) => {
      clearTimeout(minuteur);
      sortie.end();
      resolve({
        reussi: code === 0 && !!final && !final.is_error,
        resume: (final && final.result) || 'Aucun résumé reçu.',
      });
    });
  });
}

module.exports = { nom: 'Claude', ENV, discuter, executerTache };
