# Janova — Architecture « Corps vivant »

Janova devient un corps vivant numérique : un cerveau minuscule, des réflexes, des organes, une mémoire, et surtout un sommeil qui la fait grandir chaque nuit. Le principe central : **chaque demande prend le chemin le moins cher qui marche**, et chaque nuit Janova transforme ce qui a coûté cher en quelque chose de gratuit.

Trois règles guident tout :

- **Économie d'abord** : un réflexe avant un organe, un organe avant le noyau, le noyau avant un professeur.
- **Savoir qu'on ne sait pas** : chaque décision a un score de confiance, comme Jev. Sous le seuil, Janova monte d'un étage au lieu d'inventer.
- **Grandir en dormant** : ce qui a été résolu plusieurs fois devient un réflexe, ce qui a manqué devient un organe, ce que le professeur a appris est distillé dans Janova.

## Les parties du corps

| Partie | Rôle | Inspiré de | Dans le code |
| --- | --- | --- | --- |
| **Réflexes** (moelle épinière) | Réponses déjà apprises, et décisions en quelques millisecondes : choisir parmi des options, noter, oui/non, avec un % de confiance | Jev (TypeSafe AI, 2026), Système 1 de Kahneman | `reflexes/`, `decision.py` ✅ |
| **Noyau** (cerveau) | Découpe une tâche en étapes et coordonne, sans faire le travail lui-même | Tiny Recursive Model (7 M de paramètres) | `noyau/` ✅ (sans IA pour l'instant) |
| **Organes** (compétences) | Dossiers autonomes : du code, ses tests, une description | Voyager, EvoSkill, SAGE | `organes/`, `extension/` ✅ |
| **Mémoire** (hippocampe) | Graphe de connaissances façon Obsidian : chaque idée est une note, reliée aux idées proches | Letta/MemGPT, Jev-Mem | `idees.py` ✅ (idées) |
| **Sommeil** (rêve) | La nuit : trier, relier, oublier, faire évoluer les organes | « Dreaming », courbe de l'oubli | `dormir()` ✅ |
| **Professeurs** (école) | Un modèle d'IA appelé seulement pour un « trou ». Chaque leçon est retenue | Distillation (2015) | `aide_exterieure.py` ✅ |
| **Système immunitaire** | Teste chaque nouvel organe dans un bac à sable avant de le garder | Sécurité des agents | `extension/bac_a_sable.py` ✅ |
| **Métabolisme** | Mesure ce que coûte chaque chemin, s'économise selon la batterie | Mélange d'experts, homéostasie | `energie.py`, `homeostasie.py` ✅ |
| **Croissance** | Journal de qui a résolu chaque étape, taux d'autonomie, stade de vie | — | `croissance.py` ✅ |

## Le parcours d'une demande

```
demande ─► 1. réflexes ──sûr──► réponse ─► journal ─► sommeil (la nuit)
             │ pas sûr                                    │
             ▼                                            │ crée réflexes
           2. organes ──sûr──► réponse                    │ et organes
             │ pas sûr                                    │
             ▼                                            ▼
           3. noyau ────sûr──► réponse           (Janova grandit)
             │ pas sûr
             ▼
           4. professeur ─────► réponse + leçon retenue
```

Exemple réel avec le carnet d'idées (`/idee`) : la première idée sur la SCI est rangée par le professeur, qui répond « immobilier ». Janova retient la leçon. La deuxième idée sur la SCI est rangée par **réflexe**, sans professeur.

## Le cycle de croissance

Chaque nuit, Janova « dort » :

1. **Relire la journée** : chaque étape est notée avec qui l'a résolue (`/croissance`).
2. **Ranger la mémoire** : relier les idées proches, oublier les réflexes inutiles.
3. **Faire naître des réflexes** : une tâche réussie devient un réflexe.
4. **Faire pousser des organes** : un « trou » donne un nouvel organe, gardé seulement s'il réussit ses tests.
5. **Apprendre un peu** : plus tard, réentraîner légèrement le noyau (LoRA) avec les leçons des professeurs.

La règle des trous : trou rare = solution jetable, trou fréquent et simple = réflexe, trou fréquent et complexe = organe permanent.

## Stades de vie

Mesurés par le **taux d'autonomie** : la part des étapes résolues sans professeur.

| Stade | Autonomie | Ce qu'elle sait faire |
| --- | --- | --- |
| **Bébé** | moins de 50 % (ou moins de 20 étapes) | Presque tout passe par les professeurs ; elle note et range |
| **Enfant** | au moins 50 % | Les tâches courantes passent par réflexes et organes |
| **Adulte** | au moins 90 % | Fonctionne hors ligne pour l'essentiel |

Seuils provisoires, à ajuster avec les premières vraies mesures.

## Feuille de route

1. ✅ **Mémoire + professeur** : carnet d'idées en notes Markdown reliées, professeur local (Ollama).
2. ✅ **Décisions façon Jev** : choisir, noter, oui/non, avec confiance. Premier usage : ranger les idées.
3. ✅ **Échelle d'escalade + métabolisme** : réflexe → organe → noyau → professeur, coût mesuré.
4. ✅ **Organes + système immunitaire** : organes écrits par l'IA, testés dans un bac à sable.
5. 🔜 **Rétrograder** les réflexes et organes qui se trompent souvent.
6. 🔜 **Janova sur Linux** : voir plus bas.
7. 🔜 **Apprentissage du noyau** (PC avec carte graphique) : réentraînement léger LoRA.
8. 🧪 **Noyau récursif** : tester l'approche TRM sur le découpage de tâches.
9. 🤖 **Corps** (robot, Raspberry Pi) : réflexes moteurs avec des réseaux « liquides ».

## Janova sur Linux : un système géré par l'IA

L'objectif : Janova tourne en permanence sur l'ordinateur et s'occupe de la machine.

- **Un service de fond** (systemd) : Janova démarre avec l'ordinateur et dort quand la machine ne fait rien.
- **Des organes système** : lire l'état de la machine (disque, mémoire, mises à jour), ranger les fichiers, surveiller.
- **Des réflexes système** : « disque presque plein → proposer un nettoyage », décidés en millisecondes.
- **Un système immunitaire renforcé** : Janova propose, tu valides. Aucune commande qui supprime ou modifie le système sans ton accord. Tout est noté et réversible.

## Limites honnêtes

- **Le noyau minuscule n'existe pas encore pour le langage** : TRM brille sur des puzzles, pas en conversation.
- **Jev est un service en ligne** : on recrée son principe en local, pas le modèle lui-même.
- **L'auto-extension est le plus dur** : un organe mal testé peut casser Janova. D'où le bac à sable.
- **Simple d'abord** : le corps humain sert de carte, pas de plan à copier.

## Sources

- [Jev — Next](https://next.ink/257219/ia-le-nouveau-modele-jev-se-veut-le-champion-des-decisions-typees/)
- [Jev-Mem (arXiv)](https://arxiv.org/pdf/2609.23986)
- [Tiny Recursive Model — GitHub](https://github.com/Flast-Solution/Tiny-Recursive-Models)
- [EvoSkill (arXiv)](https://arxiv.org/abs/2603.02766)
- [SAGE, agent à bibliothèque de compétences (arXiv)](https://arxiv.org/abs/2512.17102v2)
- [Dynamic Agent Skills (arXiv)](https://arxiv.org/abs/2607.10113)
- [LOCAL, apprentissage sur l'appareil (arXiv)](https://arxiv.org/pdf/2608.15241)
- [Mémoire d'agent et « dreaming » — Red Hat](https://next.redhat.com/2026/06/01/from-context-to-dreams-architecting-memory-for-ai-agents)
- [Réseaux liquides — VNTU](https://ir.lib.vntu.edu.ua/handle/123456789/52968)
