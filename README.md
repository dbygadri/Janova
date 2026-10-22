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

## Une IA bio-inspirée

Janova copie le vivant à deux échelles : **son architecture** (noyau, organes, réflexes, sommeil) et **ses mécanismes** :

| Dans le vivant | Dans Janova |
|---|---|
| **Neurones à impulsions** : un neurone accumule des signaux, « tire » au-delà d'un seuil, et ne consomme rien au repos | L'organe **social** est un vrai petit réseau de neurones à impulsions. Il apprend par la règle de Hebb, un neurone inhibiteur freine les mots inconnus, et il reste silencieux s'il n'y a rien pour lui |
| **Homéostasie** : le corps régule son énergie, sa température, sa fatigue | Janova lit sa batterie, sa mémoire libre et sa température, puis passe en mode **économie** (plus d'aide extérieure) ou **survie** (seulement l'essentiel) |
| **Habituation** : on n'entend plus le tic-tac de l'horloge | Une tâche répétée 3 fois en une minute reçoit une réponse de mémoire immédiate |
| **Adrénaline** : l'urgence mobilise des réserves | Un mot d'urgence (« urgent », « vite »…) débloque l'aide extérieure en mode économie |
| **Courbe de l'oubli** : un souvenir s'efface, la répétition le renforce | Chaque réflexe a une force qui baisse de moitié en 7 jours. Chaque réutilisation allonge ce délai, et sous 10 % il s'efface pendant le sommeil |
| **Évolution** : variations au hasard, sélection des meilleures | Pendant le sommeil, les organes appris font évoluer leurs mots-clés pour éviter leurs fausses alertes, sans jamais perdre ce qu'ils savaient faire |

## La vision

### 🧠 Le noyau : un raisonnement minimal qui coordonne
Le noyau ne sait pas tout faire, et c'est voulu. Son rôle est de **comprendre la tâche, la découper en étapes et confier chaque étape au bon organe**. Comme le cerveau, il décide et coordonne. Il reste petit pour rester rapide et économe.

### 🫀 Les organes : spécialisés et autonomes
Chaque organe fait **une chose et la fait bien** : calculer, se souvenir, comprendre le langage, voir, parler… Un organe fonctionne seul, avec ses propres règles, et on peut en ajouter ou en remplacer un sans toucher au reste. On n'utilise que les organes dont on a besoin, ce qui économise la puissance de la machine.

### ⚡ Les réflexes : appris avec l'expérience
Quand une même situation revient souvent, Janova n'a plus besoin d'y réfléchir : elle en fait un **réflexe**. La réponse devient alors immédiate et ne consomme presque rien, comme quand on retire la main d'une plaque chaude. Plus Janova sert, plus elle a de réflexes, et plus elle est rapide.

### 🌱 L'auto-extension : grandir toute seule
Face à une situation qu'aucun organe ne sait traiter, Janova peut **se donner une nouvelle capacité** : un nouveau réflexe, voire un nouvel organe. Elle grandit avec ce qu'elle vit.

L'architecture complète et la feuille de route sont décrites dans [ARCHITECTURE.md](ARCHITECTURE.md).

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
| Raisonnement du noyau (niveau 3) | ✅ Relie une étape au résultat précédent (« multiplie le résultat par 4 ») |
| Aide extérieure (niveau 4) | ✅ Un modèle d'IA **local** via Ollama, en tout dernier recours |
| Auto-extension | ✅ L'IA écrit un nouvel organe, testé dans un bac à sable, gardé pour la suite |
| Neurones à impulsions | ✅ Organe `social` : salutations, remerciements, compliments, au revoir, « qui es-tu ? » |
| Homéostasie | ✅ Modes normal, économie et survie selon la batterie, la mémoire et la température (`/etat`) |
| Attention | ✅ Habituation aux tâches répétées, urgence qui débloque des ressources |
| Courbe de l'oubli | ✅ Les réflexes se renforcent à l'usage et s'effacent avec le temps |
| Évolution | ✅ Les organes appris améliorent leurs mots-clés pendant le sommeil |
| Décisions rapides (façon Jev) | ✅ Choisir, noter, oui/non, avec un % de confiance, appris par l'exemple |
| Carnet d'idées | ✅ Rangement automatique, notes Markdown reliées entre elles (graphe façon Obsidian) |
| Croissance | ✅ Taux d'autonomie et stade de vie : bébé, enfant, adulte (`/croissance`) |
| Mains (Linux) | ✅ Ranger, déplacer, ouvrir, fond d'écran, thème, corbeille, notifications ; tout s'annule (`/annuler`) |
| Confiance graduelle | ✅ Janova demande, puis agit seule après 3 accords ; la corbeille demande toujours |
| Recettes apprises | ✅ Le professeur traduit une demande nouvelle en gestes sûrs, gardés si tu acceptes |
| Routines | ✅ « tous les matins, change mon thème » |
| Yeux | ✅ Fermés par défaut ; repèrent tes habitudes et proposent des routines (`/yeux oui`) |
| Fenêtre sur le bureau | ✅ Zone de texte, boutons oui/non, démarrage avec la session |
| Codeur | ✅ Code des applications, les teste, se corrige seule et les installe dans le menu (`/applications`) |

## Organisation des fichiers

```
Janova/
├── janova/              le code de Janova
│   ├── __main__.py      la démonstration (python -m janova)
│   ├── energie.py       le compteur d'énergie : électricité, mémoire, carte graphique, stockage
│   ├── decision.py      les décisions rapides façon Jev : choisir parmi des options, avec confiance
│   ├── idees.py         le carnet d'idées : rangement automatique et graphe de notes
│   ├── croissance.py    le taux d'autonomie et les stades de vie
│   ├── mains/           agir sur Linux : gestes sûrs (primitives), confiance graduelle, recettes
│   ├── codeur/          coder des applications : modèles, contrôle qualité, auto-correction, installation
│   ├── yeux.py          remarquer tes habitudes (fermés par défaut, tout reste local)
│   ├── routines.py      les tâches à heure fixe (« tous les matins… »)
│   ├── conversation.py  tout ce que tu écris, dans le terminal comme dans la fenêtre
│   ├── fenetre.py       la fenêtre de Janova sur le bureau
│   ├── installer.py     démarrage automatique avec ta session
│   ├── noyau/           le cerveau : reçoit une tâche, la découpe, coordonne
│   │   ├── decoupage.py    découpage d'une tâche en étapes
│   │   ├── coordination.py les 4 niveaux, du moins cher au plus cher ; réveil des organes ; sommeil
│   │   └── raisonnement.py relie une étape au résultat de la précédente
│   ├── organes/         les organes spécialisés
│   │   ├── base.py         le modèle commun : nom, coût, carte graphique, réflexe possible
│   │   ├── calcul.py       résout les opérations (sans eval, donc sans danger)
│   │   ├── texte.py        majuscules, minuscules, compter les mots, à l'envers
│   │   └── neurones.py     l'organe social, un réseau de neurones à impulsions
│   ├── aide_exterieure.py le modèle d'IA local (Ollama), en dernier recours
│   ├── homeostasie.py   signes vitaux (batterie, mémoire, température) et modes économie / survie
│   ├── attention.py     habituation et urgence
│   ├── reflexes/        les réflexes appris
│   │   └── memoire.py      apprendre, retrouver, garder sur le disque, courbe de l'oubli
│   └── extension/       l'auto-extension
│       ├── createur.py     fait écrire un organe par l'IA, le teste, l'enregistre
│       ├── evolution.py    variation et sélection des mots-clés des organes appris
│       └── bac_a_sable.py  vérifie et exécute sans danger le code écrit par l'IA
├── donnees/             ce que Janova apprend sur ta machine (créé tout seul, pas envoyé sur GitHub)
├── tests/               les tests automatiques
├── requirements.txt     les bibliothèques nécessaires (aucune pour l'instant)
├── ARCHITECTURE.md      l'architecture « corps vivant » et la feuille de route
└── README.md            ce fichier
```

## Installer sur Linux (recommandé)

```bash
sudo apt install git python3 python3-venv python3-tk
git clone https://github.com/dbygadri/Janova.git
cd Janova
python3 -m janova --installer
python3 -m janova --bureau
```

La 4e ligne fait démarrer Janova avec ta session et l'ajoute au menu des applications. La 5e ouvre sa fenêtre tout de suite. Ensuite, parle-lui :

```
toi > range mes téléchargements
Je propose : ranger un dossier par type de fichier (téléchargements). D'accord ? (oui / non)
toi > oui
2 fichier(s) rangé(s) dans Téléchargements : 1 Documents, 1 Images.
toi > tous les matins, change mon thème
C'est noté : tous les jours à 08:00 : change mon thème.
```

### Janova code

```
toi > crée-moi une calculatrice
toi > oui
J'ai codé et testé « Calculatrice » (de mémoire, sans professeur). Elle est dans ton menu des applications.
toi > modifie calculatrice : ajoute une touche racine carrée
```

Elle sait déjà coder une calculatrice, un minuteur et un bloc-notes sans aide. Pour tout le reste (« code un jeu de morpion », « fais-moi un programme qui convertit des euros »), elle demande à son professeur, essaie le programme, lui renvoie les erreurs jusqu'à ce que ça marche (4 essais maximum), puis l'installe. Chaque application passe une lecture de sécurité : pas de réseau, pas de commandes système, rien qui efface des fichiers. Pour lui donner son professeur de code :

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5-coder:3b
```

Après 3 « oui » pour un même geste, Janova le fait seule. Elle ne supprime jamais rien définitivement (au pire, la corbeille, et elle demande toujours), et `/annuler` défait sa dernière action. Pour qu'elle remarque tes habitudes : `/yeux oui`.

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

## L'aide extérieure et l'auto-extension (facultatif)

Sans IA, Janova fonctionne déjà avec ses réflexes, ses organes et son raisonnement. Pour qu'elle puisse **apprendre de nouveaux organes**, installe [Ollama](https://ollama.com) (gratuit, tout reste sur ta machine), puis un petit modèle économe :

```bash
ollama pull qwen2.5:1.5b
```

Quand aucune autre partie ne sait traiter une étape, Janova demande au modèle d'écrire un **organe** pour ce genre d'étape. Si ce n'est pas possible, le modèle répond directement. L'organe proposé n'est gardé que s'il :
1. passe la **lecture de sécurité** : pas de fichiers, pas de réseau, pas de code caché ;
2. réussit **ses propres tests**, exécutés dans un **bac à sable** (programme séparé, limites de temps et de mémoire) ;
3. traite bien l'étape d'origine.

Il est ensuite enregistré dans `donnees/organes_appris/` : **la fois suivante, plus besoin de l'IA**. Pour utiliser un autre modèle : variable d'environnement `JANOVA_MODELE`. Si Ollama n'est pas lancé, Janova continue sans lui.

> ⚠️ Le compteur d'énergie ne mesure que Janova. Ollama et le bac à sable tournent à part : leur consommation réelle, surtout celle d'Ollama, est plus élevée que ce qui s'affiche.

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

Avec le raisonnement, l'aide extérieure et l'auto-extension (ici, Ollama est lancé) :

```
toi > calcule 2 + 3, puis multiplie le résultat par 4. Ensuite convertis 20 celsius en fahrenheit
  1. calcule 2 + 3 → 2 + 3 = 5   [organe calcul, …]
  2. multiplie le résultat par 4 → 5 * 4 = 20   [raisonnement + organe calcul, …]
  3. convertis 20 celsius en fahrenheit → 68 °F   [aide extérieure → nouvel organe « celsius_fahrenheit », …]

toi > convertis 37 celsius en fahrenheit
  1. convertis 37 celsius en fahrenheit → 98.6 °F   [organe celsius_fahrenheit, …]
```

Les mécanismes bio-inspirés en action :

```
toi > Bonjour ! Comment vas-tu ?
  1. Bonjour → Bonjour ! Je suis Janova. Que puis-je faire pour toi ?   [organe social, …]
  2. Comment vas-tu → Je vais bien, merci ! Mes réserves d'énergie sont au vert.   [organe social, …]

toi > calcule 2 + 3, puis multiplie le résultat par 4      (3e fois en une minute)
Tâche répétée : réponse de mémoire immédiate (habituation).
  1. calcule 2 + 3 → 2 + 3 = 5   [habituation, …]
  2. multiplie le résultat par 4 → 5 * 4 = 20   [habituation, …]
```

Le carnet d'idées et la croissance :

```
toi > /idee alkestore : ajouter le paiement mobile
Idée n°1 rangée dans « alkestore » [toi, 100%]
  importance moyenne, action « à faire »

toi > /idee paiement mobile alkestore avec Orange Money
Idée n°2 rangée dans « alkestore » [réflexe, 100%]
  importance basse, action « à faire », reliée aux idées n°1

toi > /croissance
Stade : bébé   (autonomie 100% sur 2 étape(s))
```

Chaque idée est une note Markdown dans `donnees/idees/` : ouvre ce dossier dans [Obsidian](https://obsidian.md) pour voir le graphe. Si Janova n'est pas sûre de la catégorie, elle demande au professeur (Ollama) et retient la leçon ; sans professeur, l'idée attend que tu la classes avec `/classer`.

Commandes : `/idee`, `/idees`, `/classer`, `/croissance`, `/bilan` (toutes les ressources dépensées), `/etat` (signes vitaux et mode), `/organes`, `/reflexes`, `/dormir`, `/aide`, `/quitter`.
