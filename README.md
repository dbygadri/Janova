# JANOVA

Le noyau d'une IA locale qui naît presque vide et apprend de son entourage, les LLM, pour s'en passer peu à peu.

- **Léger** : Python standard uniquement, aucune dépendance. Une seule base SQLite pour toute la mémoire. Prévu pour tourner sur un PC, un téléphone (Termux) ou un petit robot (Raspberry Pi).
- **Apprend en faisant** : quand elle ne sait pas, elle demande à ses professeurs. Elle garde ensuite ce qu'elle a appris (du code testé, des connaissances vérifiées) et le réutilise **sans LLM**.
- **Vérifiable** : chaque apprentissage est inscrit dans un journal chaîné par empreintes SHA-256, comme une blockchain. `/verifier` détecte toute modification en douce.

## Lancer

```bash
# 1. Un professeur local (facultatif mais nécessaire pour apprendre)
ollama pull mistral

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
2. **Compétence connue** : elle exécute le code qu'elle a appris, dans un bac à sable, sans LLM.
3. **Connaissance connue** : elle répond de mémoire, sans LLM.
4. **Sinon, elle demande à son entourage** et apprend :
   - *compétence* : un professeur écrit un programme et ses tests. JANOVA exécute les tests et renvoie les erreurs au professeur jusqu'à ce que tout passe (3 essais au maximum). Le code n'est gardé que s'il est correct ;
   - *connaissance* : elle pose la question à **tous** les professeurs et ne mémorise la réponse que si la majorité est d'accord ;
   - *conversation* : elle répond, sans rien mémoriser comme vérité.

`/etat` affiche son **taux d'autonomie**, c'est-à-dire la part des demandes traitées sans aucun LLM. Les avis `/bon` et `/mauvais` la corrigent : une compétence qui se trompe deux fois est abandonnée, puis réapprise autrement à la demande suivante.

## Organisation

| Fichier | Rôle |
|---|---|
| `janova/core.py` | Le noyau : la boucle de vie (percevoir, chercher en soi, apprendre, répondre) |
| `janova/store.py` | La mémoire (compétences, connaissances, épisodes) et le journal chaîné |
| `janova/sandbox.py` | L'exécution isolée des compétences apprises |
| `janova/teachers.py` | L'entourage : les professeurs LLM et le consensus |
| `janova/text.py` | La comparaison de textes sans modèle |
| `janova/config.py` | Les réglages |
| `janova/__main__.py` | L'interface texte |

## Tests

```bash
python -m unittest discover -s tests
```

## Limites connues

- Le bac à sable (analyse du code, processus séparé, limites de temps et de mémoire) est un garde-fou raisonnable, pas une prison parfaite.
- Pour reconnaître une demande, la comparaison des mots est simple. Une formulation très différente d'une compétence connue repassera par un professeur, qui ajoutera un exemple.
- Les licences d'OpenAI, d'Anthropic, de Google… interdisent d'entraîner un modèle concurrent avec leurs réponses. Le jour où JANOVA entraînera son propre petit modèle, il faudra n'utiliser que des professeurs dont la licence le permet.

## Prochaines étapes

1. Reconnaître les demandes par le sens (petit modèle d'embeddings local) plutôt que par les mots.
2. Laisser JANOVA combiner plusieurs compétences pour résoudre une tâche nouvelle.
3. Entraîner un petit cerveau à elle (0,5 à 2 Go) sur ses propres épisodes.
4. Synchroniser les connaissances entre appareils (nœud léger qui télécharge à la demande et vérifie par empreinte).
5. Ajouter les sens et les actions d'un robot : voix, caméra, moteurs.
