# JANOVA

Le noyau d'une IA locale qui naît presque vide et apprend de son entourage, les LLM, pour s'en passer peu à peu.

- **Léger** : Python standard uniquement, aucune dépendance. Une seule base SQLite pour toute la mémoire. Prévu pour tourner sur un PC, un téléphone (Termux) ou un petit robot (Raspberry Pi).
- **Apprend en faisant** : quand elle ne sait pas, elle demande à ses professeurs. Elle garde ensuite ce qu'elle a appris (du code testé, des connaissances vérifiées) et le réutilise **sans LLM**.
- **Vérifiable** : chaque apprentissage est inscrit dans un journal chaîné par empreintes SHA-256, comme une blockchain. `/verifier` détecte toute modification en douce.

## Lancer

```bash
# 1. Un professeur local (facultatif mais nécessaire pour apprendre)
ollama pull mistral
# et un petit modèle de sens (46 Mo, facultatif) pour reconnaître les demandes reformulées
ollama pull all-minilm

# 2. JANOVA
python -m janova                 # mode conversation
python -m janova "20 celsius en fahrenheit"   # une seule demande
```

La mémoire est dans `~/.janova/` (ou dans le dossier `JANOVA_HOME`). Les réglages et la liste des professeurs se trouvent dans `~/.janova/config.json`. Mettre plusieurs professeurs (par exemple `mistral`, `qwen2.5`, `llama3.2`) permet le consensus :

```json
{"teachers": [
  {"type": "ollama", "model": "mistral"},
  {"type": "ollama", "model": "qwen2.5"},
  {"type": "ollama", "model": "llama3.2", "url": "http://192.168.1.20:11434"}
]}
```

## Comment elle traite une demande

1. **Commande** (`/aide`, `/etat`, `/bon`, `/mauvais`, `/verifier`…).
2. **Compétence connue** : elle exécute le code qu'elle a appris, dans un bac à sable, sans LLM. Elle reconnaît la demande à ses mots et, si le modèle de sens est disponible, à son sens : « Quelle température en Fahrenheit pour 25 °C ? » retrouve la compétence apprise avec « convertis 20 celsius en fahrenheit ».
3. **Connaissance connue** : elle répond de mémoire, sans LLM.
4. **Sinon, elle demande à son entourage** et apprend :
   - *compétence* : un professeur écrit un programme et ses tests. JANOVA exécute les tests et renvoie les erreurs au professeur jusqu'à ce que tout passe (3 essais au maximum). Le code n'est gardé que s'il est correct ;
   - *connaissance* : elle pose la question à **tous** les professeurs et ne mémorise la réponse que si la majorité est d'accord ;
   - *conversation* : elle répond, sans rien mémoriser comme vérité.

## Son cerveau, façon Obsidian

Tout ce que JANOVA apprend devient une **note Markdown reliée aux autres**, dans `~/.janova/cerveau/` :

```
cerveau/
├── Janova.md                 la note d'accueil
├── graphe.html               la vue graphe, à ouvrir dans n'importe quel navigateur (téléphone compris)
├── competences/c1 celsius_vers_fahrenheit.md
└── connaissances/f1 Quelle est la capitale de la France.md
```

Ouvre ce dossier comme coffre dans **Obsidian** (ou Logseq) pour naviguer dans ses connaissances, ou ouvre simplement `graphe.html`, qui fonctionne sans rien installer. Les liens viennent de trois sources :

- **proche** : JANOVA relie d'elle-même ce qui parle de la même chose ;
- **lien choisi** : `/lier c1 f2`, inscrit au journal chaîné ;
- **tes notes** : la section « Mes notes » de chaque note est à toi. JANOVA la garde même si le dossier est effacé, l'inscrit au journal (donc `/verifier` la protège) et suit les `[[liens]]` que tu y écris.

Le cerveau se met à jour tout seul à chaque apprentissage et à chaque démarrage ; `/cerveau` le force. SQLite reste la mémoire de référence : le reste de chaque note est régénéré à partir d'elle.

`/etat` affiche son **taux d'autonomie**, c'est-à-dire la part des demandes traitées sans aucun LLM. Les avis `/bon` et `/mauvais` la corrigent : une compétence qui se trompe deux fois est abandonnée, puis réapprise autrement à la demande suivante.

## Organisation

| Fichier | Rôle |
|---|---|
| `janova/core.py` | Le noyau : la boucle de vie (percevoir, chercher en soi, apprendre, répondre) |
| `janova/store.py` | La mémoire (compétences, connaissances, épisodes) et le journal chaîné |
| `janova/cerveau.py` | Le cerveau : notes Markdown reliées (compatibles Obsidian) et vue graphe |
| `janova/sandbox.py` | L'exécution isolée des compétences apprises |
| `janova/teachers.py` | L'entourage : les professeurs LLM et le consensus |
| `janova/meaning.py` | La comparaison par le sens (petit modèle d'embeddings, vecteurs gardés en cache) |
| `janova/text.py` | La comparaison par les mots, sans modèle |
| `janova/config.py` | Les réglages |
| `janova/__main__.py` | L'interface texte |

## Tests

```bash
python -m unittest discover -s tests
```

## Limites connues

- Le bac à sable (analyse du code, processus séparé, limites de temps et de mémoire) est un garde-fou raisonnable, pas une prison parfaite.
- Le modèle de sens rapproche les demandes de même sujet, pas forcément de même sens exact : « 20 °F en Celsius » peut ressembler à une compétence « Celsius vers Fahrenheit ». Le seuil `meaning_threshold` (0,8 par défaut, dans `config.json`) règle cette prudence, et `/mauvais` corrige les erreurs.
- Sans modèle de sens, la reconnaissance se fait par les mots seulement. Une formulation très différente repasse alors par un professeur.
- Les licences d'OpenAI, d'Anthropic, de Google… interdisent d'entraîner un modèle concurrent avec leurs réponses. Le jour où JANOVA entraînera son propre petit modèle, il faudra n'utiliser que des professeurs dont la licence le permet.

## Prochaines étapes

1. Laisser JANOVA combiner plusieurs compétences pour résoudre une tâche nouvelle.
2. Entraîner un petit cerveau à elle (0,5 à 2 Go) sur ses propres épisodes.
3. Synchroniser les connaissances entre appareils (nœud léger qui télécharge à la demande et vérifie par empreinte).
4. Ajouter les sens et les actions d'un robot : voix, caméra, moteurs.
