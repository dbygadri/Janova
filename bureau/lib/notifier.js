// Notifications : sur le bureau (notify-send) et, si possible, sur le téléphone (application gratuite ntfy).
// Le téléphone s'abonne à un « sujet » au nom secret, tiré au hasard. Les messages passent par le service
// public ntfy.sh : ils restent courts (projet, tâche, résultat) et ne contiennent jamais de détail sensible.
const { execFile } = require('child_process');
const crypto = require('crypto');
const https = require('https');
const memoire = require('./memoire');

function sujetTelephone() {
  let { ntfy } = memoire.reglages();
  if (!ntfy) {
    ntfy = { sujet: 'janova-' + crypto.randomBytes(12).toString('hex'), actif: true };
    memoire.changerReglages({ ntfy });
  }
  return ntfy;
}

function telephone(titre, message, urgent) {
  const { sujet, actif } = sujetTelephone();
  if (!actif || process.env.JANOVA_SANS_TELEPHONE) return Promise.resolve(false);
  // Envoi au format JSON : accents et émojis passent sans souci.
  const corps = JSON.stringify({
    topic: sujet, title: titre, message: message.slice(0, 300), priority: urgent ? 4 : 3, tags: [urgent ? 'warning' : 'white_check_mark'],
  });
  return new Promise((resolve) => {
    const req = https.request('https://ntfy.sh/', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, timeout: 10000,
    }, (res) => { res.resume(); resolve(res.statusCode === 200); });
    req.on('error', () => resolve(false));
    req.on('timeout', () => { req.destroy(); resolve(false); });
    req.end(corps);
  });
}

function bureau(titre, message, urgent) {
  return new Promise((resolve) =>
    execFile('notify-send', ['-a', 'Janova', '-u', urgent ? 'critical' : 'normal', titre, message.slice(0, 300)], () => resolve()));
}

// Prévient l'utilisateur, partout où c'est possible.
async function prevenir(titre, message, { urgent = false } = {}) {
  await Promise.all([bureau(titre, message, urgent), telephone(titre, message, urgent)]);
}

module.exports = { prevenir, sujetTelephone };
