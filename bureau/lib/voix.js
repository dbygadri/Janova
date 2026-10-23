// Commande vocale : la voix est transcrite sur le PC (whisper.cpp), jamais envoyée sur internet.
const { execFile } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');
const projets = require('./projets');

const MOTEUR = process.env.JANOVA_WHISPER || path.join(os.homedir(), '.local', 'opt', 'whisper.cpp', 'build', 'bin', 'whisper-cli');
const MODELE = path.join(projets.DONNEES, 'voix', 'ggml-base-q5_1.bin');

const disponible = () => fs.existsSync(MOTEUR) && fs.existsSync(MODELE);

// Reçoit un enregistrement WAV (16 kHz, mono) et renvoie le texte dicté.
function transcrire(wav) {
  if (!disponible()) return Promise.reject(new Error("La commande vocale n'est pas installée sur ce PC."));
  const fichier = path.join(os.tmpdir(), `janova-voix-${process.pid}-${Date.now()}.wav`);
  fs.writeFileSync(fichier, Buffer.from(wav));
  return new Promise((resolve, reject) => {
    execFile(MOTEUR, ['-m', MODELE, '-f', fichier, '-l', 'fr', '-nt', '-np', '-t', String(Math.min(4, os.cpus().length))],
      { timeout: 120000 }, (err, out) => {
        fs.rmSync(fichier, { force: true });
        if (err) return reject(new Error("Je n'ai pas réussi à comprendre l'enregistrement."));
        resolve(out.replace(/\[[^\]]*\]/g, '').replace(/\s+/g, ' ').trim());
      });
  });
}

module.exports = { disponible, transcrire };
