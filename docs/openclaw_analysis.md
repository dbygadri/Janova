# Analyse rapide d'OpenClaw (concepts réutilisables)

Cette base JANOVA réutilise uniquement des **concepts d'architecture** inspirés d'un assistant local de type OpenClaw, sans copier son implémentation:

1. **Noyau orchestrateur** : un composant central route les demandes vers LLM, modules ou agents.
2. **Séparation des responsabilités** : UI, logique core, agents et modules sont isolés.
3. **Registres persistants JSON** : historique, agents, modules et état sont stockés localement.
4. **Extensions pluggables** : modules dynamiques chargés à l'exécution.
5. **Travail asynchrone local** : tâches longues déléguées à des workers pour garder l'UI réactive.

Adaptation JANOVA:
- Priorité Windows + Tkinter + Ollama local.
- Génération d'applications tkinter via agent codeur.
- Mémoire d'apprentissage séparée du chat.
