"""L'auto-extension : la capacité de Janova à se donner de nouveaux organes.

- createur.py   demande à l'aide extérieure d'écrire un organe, le teste, l'enregistre ;
- bac_a_sable.py vérifie et exécute sans danger le code de ces organes.
"""

from janova.extension.createur import CreateurOrganes

__all__ = ["CreateurOrganes"]
