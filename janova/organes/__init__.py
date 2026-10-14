"""Les organes : des modules spécialisés et autonomes.

Chacun sait faire une chose et la fait bien. Le noyau leur confie les étapes qui les concernent,
en commençant toujours par le moins coûteux (règle 1).

Pour ajouter un organe : créer un fichier dans ce dossier (en s'inspirant de calcul.py),
puis l'ajouter à la liste TOUS_LES_ORGANES ci-dessous.
"""

from janova.organes.base import Organe
from janova.organes.calcul import OrganeCalcul
from janova.organes.texte import OrganeTexte

TOUS_LES_ORGANES: list[type[Organe]] = [OrganeCalcul, OrganeTexte]

__all__ = ["Organe", "OrganeCalcul", "OrganeTexte", "TOUS_LES_ORGANES"]
