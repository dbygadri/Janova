// Les outils web de chaque projet (GitHub, Hostinger, Vercel, Play Console, Apple), ouverts dans Janova.
// Un projet peut préciser ses propres adresses dans la mémoire : projets/<id>/liens.json.
const memoire = require('./memoire');
const { COMPTE } = require('./projets');

const OUTILS = [
  { id: 'github', nom: 'GitHub' },
  { id: 'hostinger', nom: 'Hostinger' },
  { id: 'vercel', nom: 'Vercel' },
  { id: 'play', nom: 'Play Console' },
  { id: 'apple', nom: 'Apple' },
];

function liens(p) {
  const propres = p ? memoire.lireJson(memoire.chemin('projets', p.id, 'liens.json'), {}) : {};
  const depot = p && p.depots[0];
  const defauts = {
    github: depot ? `https://github.com/${COMPTE}/${depot}` : `https://github.com/${COMPTE}`,
    hostinger: 'https://hpanel.hostinger.com/',
    vercel: 'https://vercel.com/dashboard',
    play: 'https://play.google.com/console',
    apple: 'https://developer.apple.com/account',
  };
  return OUTILS.map((o) => ({ ...o, adresse: propres[o.id] || defauts[o.id] }));
}

module.exports = { OUTILS, liens };
