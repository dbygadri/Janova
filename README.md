# Janova

**Un noyau d'IA locale, ultra-efficace, inspiré du corps humain.**

Janova tourne entièrement sur ta machine. Plutôt qu'un seul énorme modèle qui fait tout, elle s'organise comme un corps : un cerveau minimal qui coordonne, des organes qui se spécialisent, des réflexes qui s'acquièrent avec l'expérience, et la capacité de grandir toute seule.

## Le principe fondamental : peu d'énergie, beaucoup de puissance

Le cerveau humain fonctionne avec environ **20 watts**, à peine une ampoule, et il reste pourtant plus polyvalent que n'importe quelle machine. Il n'y arrive pas en calculant plus fort, mais en **dépensant son énergie avec intelligence**. Janova suit les mêmes règles :

1. **Le moins cher d'abord.** Pour chaque étape, Janova essaie d'abord la solution la plus économe, et ne monte d'un cran que si c'est nécessaire :
   réflexe (presque gratuit) → organe spécialisé (léger) → raisonnement du noyau (plus coûteux) → aide extérieure, comme un grand modèle d'IA, en tout dernier recours.
2. **N'allumer que ce qui sert.** Comme le cerveau, qui n'active jamais tous ses neurones à la fois, les organes restent **endormis** tant qu'on n'a pas besoin d'eux. Ils ne consomment rien au repos.
3. **Apprendre pour économiser.** Chaque effort coûteux qui réussit devient un réflexe. La prochaine fois, la même tâche ne coûte presque plus rien. L'expérience rend Janova plus rapide **et** plus sobre.
4. **Se reposer pour se réorganiser.** Comme pendant le sommeil, Janova profite des moments où la machine ne fait rien pour trier ce qu'elle a appris : renforcer ce qui sert, compresser, oublier l'inutile.
5. **Mesurer pour progresser.** Chaque organe annonce ce qu'il coûte, et Janova compte l'énergie qu'elle dépense, c'est-à-dire le temps de calcul. L'objectif est clair : **le coût moyen d'une tâche doit baisser avec le temps**.

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
| Noyau : découper une tâche en étapes | ✅ Première version, sans IA (mots de liaison et ponctuation) |
| Organes | ⏳ À venir |
| Réflexes | ⏳ À venir |
| Auto-extension | ⏳ À venir |

## Organisation des fichiers

```
Janova/
├── janova/              le code de Janova
│   ├── __main__.py      petite démonstration (python -m janova)
│   ├── noyau/           le cerveau : reçoit une tâche, la découpe, coordonne
│   │   └── decoupage.py découpage d'une tâche en étapes
│   ├── organes/         les organes spécialisés
│   ├── reflexes/        les réflexes appris
│   └── extension/       l'auto-extension
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
Quelle tâche dois-je découper ? Ouvre le fichier, puis lis la première ligne. Ensuite compte les mots, et enfin affiche le résultat.
Voici les étapes :
  1. Ouvre le fichier
  2. lis la première ligne
  3. compte les mots
  4. affiche le résultat
```
