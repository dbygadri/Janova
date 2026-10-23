// Cerveau « en couches » : le noyau Janova d'abord (presque gratuit), Claude seulement pour le neuf.
// Au début presque tout va à Claude ; plus le noyau apprend, moins Claude est appelé.
const claude = require('./claude');
const noyau = require('./noyau');

// « contexte » : ce que le noyau a répondu seul depuis le dernier passage par Claude,
// pour que Claude garde le fil de la discussion.
function discuter(demande, ecoute = {}) {
  let arrete = false;
  let enCours = null;
  const fin = (async () => {
    const r = await noyau.demander(demande.message);
    if (arrete) return { session: demande.session, erreur: null, couche: null };
    if (r) {
      ecoute.surNouveauMessage && ecoute.surNouveauMessage();
      ecoute.surTexte && ecoute.surTexte(r.reponse);
      return { session: demande.session, erreur: null, couche: 'noyau', niveaux: r.niveaux };
    }
    let message = demande.message;
    if (demande.contexte && demande.contexte.length) {
      const avant = demande.contexte.map((e) => `- Moi : ${e.question}\n  Janova : ${e.reponse}`).join('\n');
      message = `(Entre-temps, Janova a répondu seule à ceci :\n${avant})\n\n${message}`;
    }
    enCours = claude.discuter({ ...demande, message }, ecoute);
    const res = await enCours.fin;
    return { ...res, couche: 'claude' };
  })();
  return {
    arreter: () => { arrete = true; if (enCours) enCours.arreter(); },
    fin,
  };
}

// Les tâches sont du travail neuf sur du code : elles vont directement à Claude Code.
module.exports = { nom: 'Janova + Claude', ENV: claude.ENV, discuter, executerTache: claude.executerTache };
