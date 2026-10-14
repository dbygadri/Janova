# Janova

**Un noyau d'IA locale, ultra-efficace, inspiré du corps humain.**

Janova tourne entièrement sur ta machine. Plutôt qu'un seul énorme modèle qui fait tout, elle s'organise comme un corps : un cerveau minimal qui coordonne, des organes qui se spécialisent, des réflexes qui s'acquièrent avec l'expérience, et la capacité de grandir toute seule.

## Le principe fondamental : peu d'énergie, beaucoup de puissance

Le cerveau humain fonctionne avec environ **20 watts**, à peine une ampoule, et il reste pourtant plus polyvalent que n'importe quelle machine. Il n'y arrive pas en calculant plus fort, mais en **dépensant son énergie avec intelligence**.

Pour Janova, **l'énergie, ce sont toutes les ressources de la machine** :

| Ressource | Comment Janova la mesure |
|---|---|
| ⚡ Électricité | Le temps de calcul du processeur, qui lui est proportionnel, en microsecondes (µs) |
| 🧠 Mémoire vive (RAM) | Le pic de mémoire utilisé par chaque action, en kilo-octets (Ko) |
| 🎮 Carte graphique | Les organes qui en ont besoin. L'objectif est de s'en passer : ces organes passent toujours en dernier |
| 💾 Stockage | La place occupée sur le disque par ce que Janova a appris |

Janova suit les mêmes règles que le cerveau :

1. **Le moins cher d'abord.** Pour chaque étape, Janova essaie d'abord la solution la plus économe, et ne monte d'un cran que si c'est nécessaire :
   réflexe (presque gratuit) → organe spécialisé (léger) → raisonnement du noyau (plus coûteux) → aide extérieure, comme un grand modèle d'IA, en tout dernier recours.
2. **N'allumer que ce qui sert.** Comme le cerveau, qui n'active jamais tous ses neurones à la fois, les organes restent **endormis** tant qu'on n'a pas besoin d'eux. Ils ne consomment rien au repos.
3. **Apprendre pour économiser.** Chaque effort coûteux qui réussit devient un réflexe. La prochaine fois, la même tâche ne coûte presque plus rien. L'expérience rend Janova plus rapide **et** plus sobre.
4. **Se reposer pour se réorganiser.** Comme pendant le sommeil, Janova profite des moments où la machine ne fait rien pour trier ce qu'elle a appris : renforcer ce qui sert, compresser, oublier l'inutile.
5. **Mesurer pour progresser.** Chaque organe annonce ce qu'il coûte, et Janova compte toutes les ressources qu'elle dépense (commande `/bilan`). L'objectif est clair : **le coût moyen d'une tâche doit baisser avec le temps**.

Concrètement, Janova doit pouvoir tourner sur un ordinateur ordinaire, un téléphone ou un petit robot, sans carte graphique puissante.

## La vision

### 🧠 Le noyau : un raisonnement minimal qui coordonne
Le noyau ne sait pas tout faire, et c'est voulu. Son rôle est de **comprendre la tâche, la découper en étapes et confier chaque étape au bon organe**. Comme le cerveau, il décide et coordonne. Il reste petit pour rester rapide et économe.

### 🫀 Les organes : spécialisés et autonomes
Chaque organe fait **une chose et la fait bien** : calculer, se souvenir, comprendre le langage, voir, parler… Un organe fonctionne seul, avec ses propres règles, et on peut en ajouter ou en remplacer un sans toucher au reste. On n'utilise que les organes dont on a besoin, ce qui économise la puissance de la machine.

### ⚡ Les réflexes : appris avec l'expérience
Quand une même situation revient souvent, Janova n'a plus besoin d'y réfléchir : elle en fait un **réflexe**. La réponse devient alors immédiate et ne consomme presque rien, comme quand on retire la main d'une plaque chaude. Plus Janova sert, plus elle a de réflexes, et plus elle est rapide.

### 🌱 L'auto-extension : grandir toute seule
Face à une situation qu'aucun organe ne sait traiter, Janova peut **se donner une nouvelle capacité** : un nouveau réflexe, voire un nouvel organe. Elle grandit avec ce qu'elle vit.

## Où en est le projet ?

| Partie | État |
|---|---|
| Noyau : découper une tâche en étapes | ✅ Sans IA (mots de liaison et ponctuation) |
| Noyau : confier chaque étape au moins cher (règle 1) | ✅ Réflexe, puis organes rangés par coût, carte graphique en dernier |
| Organes endormis par défaut (règle 2) | ✅ Réveillés seulement quand on leur confie du travail |
| Organes | ✅ `calcul` et `texte` (majuscules, minuscules, compter les mots, à l'envers) |
| Réflexes appris (règle 3) | ✅ Chaque réussite d'un organe devient un réflexe, gardé sur le disque |
| Sommeil (règle 4) | ✅ `/dormir` endort les organes et oublie les réflexes inutiles |
| Compteur d'énergie (règle 5) | ✅ Électricité, mémoire, carte graphique, stockage |
| Raisonnement du noyau (combiner des organes) | ⏳ À venir |
| Aide extérieure (grand modèle d'IA, en dernier recours) | ⏳ À venir |
| Auto-extension | ⏳ À venir |

## Organisation des fichiers

```
Janova/
├── janova/              le code de Janova
│   ├── __main__.py      la démonstration (python -m janova)
│   ├── energie.py       le compteur d'énergie : électricité, mémoire, carte graphique, stockage
│   ├── noyau/           le cerveau : reçoit une tâche, la découpe, coordonne
│   │   ├── decoupage.py    découpage d'une tâche en étapes
│   │   └── coordination.py le moins cher d'abord, réveil des organes, sommeil
│   ├── organes/         les organes spécialisés
│   │   ├── base.py         le modèle commun : nom, coût, carte graphique, réflexe possible
│   │   ├── calcul.py       résout les opérations (sans eval, donc sans danger)
│   │   └── texte.py        majuscules, minuscules, compter les mots, à l'envers
│   ├── reflexes/        les réflexes appris
│   │   └── memoire.py      apprendre, retrouver, garder sur le disque, oublier en dormant
│   └── extension/       l'auto-extension (à venir)
├── donnees/             ce que Janova apprend sur ta machine (créé tout seul, pas envoyé sur GitHub)
├── tests/               les tests automatiques
├── requirements.txt     les bibliothèques nécessaires (aucune pour l'instant)
└── README.md            ce fichier
```

## Installer et lancer (Windows)

```bash
# 1. Récupérer le projet
git clone https://github.com/dbygadri/Janova.git
cd Janova

# 2. Créer l'environnement virtuel (une seule fois)
python -m venv .venv

# 3. L'activer (à chaque nouvelle console)
.venv\Scripts\activate

# 4. Essayer le noyau
python -m janova

# 5. Lancer les tests
python -m unittest
```

Sur Linux ou macOS, l'étape 3 s'écrit `source .venv/bin/activate`.

## Exemple

```
toi > calcule 12 * (3 + 4), puis mets en majuscules : bonjour. Ensuite ouvre le fichier
  1. calcule 12 * (3 + 4) → 12 * (3 + 4) = 84   [organe calcul, 825 µs, 25.2 Ko]
  2. mets en majuscules : bonjour → BONJOUR   [organe texte, 20 µs, 1.6 Ko]
  3. ouvre le fichier → je ne sais pas encore faire cette étape
Énergie dépensée : 845 µs de calcul, pic de 25.2 Ko de mémoire

toi > calcule 12 * (3 + 4)
  1. calcule 12 * (3 + 4) → 12 * (3 + 4) = 84   [réflexe, 24 µs, 0.3 Ko]
Énergie dépensée : 24 µs de calcul, pic de 0.3 Ko de mémoire
```

La deuxième fois, c'est un **réflexe** : environ 34 fois moins de calcul et 80 fois moins de mémoire. Les chiffres varient selon la machine.

Commandes : `/bilan` (toutes les ressources dépensées), `/reflexes`, `/dormir`, `/aide`, `/quitter`.
