// Garde-fous de Janova. Fichier protégé : Claude Code ne peut pas le modifier seul ;
// toute mise à jour qui y touche demande un oui explicite de l'utilisateur.

// Branche git où le cerveau travaille, sans jamais toucher à la branche principale.
const BRANCHE = 'janova/travail';

// Ce que le cerveau n'a jamais le droit de faire seul : publier, déployer, se connecter au serveur, changer de branche.
const INTERDITS = [
  'Bash(git push:*)', 'Bash(git checkout:*)', 'Bash(git switch:*)', 'Bash(git merge:*)',
  'Bash(git rebase:*)', 'Bash(git reset:*)', 'Bash(vercel:*)', 'Bash(npx vercel:*)',
  'Bash(ssh:*)', 'Bash(scp:*)', 'Bash(rsync:*)', 'Bash(sftp:*)', 'Bash(gh:*)',
  'Bash(systemctl:*)',
];

// Fichiers du dépôt Janova que le cerveau ne modifie jamais seul (chemins depuis la racine du dépôt).
const PROTEGES = [
  'bureau/lib/garde-fous.js',
  'bureau/lib/mise-a-jour.js',
  'bureau/runner.js',
  'bureau/lib/deploiement.js',
  'bureau/cerveau/',
  '.claude/',
];

const REGLES = `Règles à respecter absolument :
- Tu es sur la branche git « ${BRANCHE} ». Ne change pas de branche.
- Ne publie rien et ne déploie rien : pas de git push, pas de Vercel, pas de connexion au serveur, pas de Play Store ni d'App Store.
- Ne lis pas et ne modifie pas les fichiers de clés ou de mots de passe.
- Ne modifie jamais les garde-fous de Janova : ${PROTEGES.join(', ')}. Si la tâche l'exige, arrête-toi et explique pourquoi.
- Enregistre ton travail avec des commits git clairs, en français.
- S'il te manque une information ou si tu es bloqué, arrête-toi et explique pourquoi.`;

// Mise en ligne : permise seulement pour une tâche de déploiement qui a reçu le feu vert de l'utilisateur.
// Le cerveau peut alors publier et se connecter au serveur, mais jamais réécrire l'historique ni forcer.
const INTERDITS_DEPLOIEMENT = [
  'Bash(git checkout:*)', 'Bash(git switch:*)', 'Bash(git reset:*)', 'Bash(git rebase:*)',
  'Bash(git push --force:*)', 'Bash(git push -f:*)', 'Bash(gh:*)', 'Bash(systemctl:*)',
];

const REGLES_DEPLOIEMENT = `Règles à respecter absolument :
- L'utilisateur a donné son feu vert pour cette mise en ligne précise, et seulement celle-ci. Ne mets rien d'autre en ligne.
- Mets en ligne la version principale (branche main), telle quelle. Ne modifie pas le code.
- Garde toujours la version précédente pour pouvoir revenir en arrière, et note comment y revenir.
- Vérifie que ça marche après la mise en ligne. Si ça ne marche pas, reviens à la version précédente et explique.
- Ne force jamais rien (pas de git push --force), ne supprime pas d'anciennes versions.
- Ne montre jamais de clé ni de mot de passe dans ta réponse.`;

// Le dépôt est-il celui de Janova elle-même ?
const fs = require('fs');
const path = require('path');
const memoire = require('./memoire');
const estJanova = (dossier) => fs.existsSync(path.join(dossier, 'bureau', 'lib', 'garde-fous.js'));

// Règles d'outils qui bloquent l'écriture des fichiers protégés (chemins absolus : « // »).
// La mémoire (où sont notés les feux verts) n'est jamais modifiée par le cerveau pendant une tâche.
function interditsPour(dossier, base = INTERDITS) {
  const absolus = ['/' + memoire.MEMOIRE + '/**'];
  if (estJanova(dossier)) absolus.push(...PROTEGES.map((p) => '/' + path.join(dossier, p) + (p.endsWith('/') ? '**' : '')));
  return [...base, ...absolus.flatMap((p) => [`Edit(${p})`, `Write(${p})`])];
}

// Parmi des fichiers modifiés, lesquels sont protégés ?
function touchesProtegees(fichiers) {
  return fichiers.filter((f) => PROTEGES.some((p) => (p.endsWith('/') ? f.startsWith(p) : f === p)));
}

module.exports = {
  BRANCHE, INTERDITS, INTERDITS_DEPLOIEMENT, PROTEGES, REGLES, REGLES_DEPLOIEMENT, estJanova, interditsPour, touchesProtegees,
};
