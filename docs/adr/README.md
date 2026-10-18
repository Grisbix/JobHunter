# Décisions d'architecture (ADR)

Une décision par fichier : contexte, décision, conséquences. Le code garde une ou deux
lignes et renvoie ici. Vue d'ensemble : [`../architecture.md`](../architecture.md).

| N° | Décision |
|---|---|
| [0001](0001-facades-alias.md) | Les anciens modules deviennent des alias du paquet |
| [0002](0002-trois-fichiers-trois-contrats.md) | Trois fichiers de données, trois contrats d'accès |
| [0003](0003-verrou-fichier-code-3.md) | Verrou par fichier, et le code de sortie 3 |
| [0004](0004-429-attendre-403-arreter.md) | Une limite de débit s'attend, un refus d'entrée s'arrête |
| [0005](0005-aucune-soumission-automatique.md) | Aucune soumission automatique, aucun mot de passe manipulé |
| [0006](0006-banc-de-non-regression.md) | Un banc de non-régression avant toute refonte |
| [0007](0007-valeurs-du-profil-paresseuses.md) | Ce qui vient du profil se calcule à la première lecture |
| [0008](0008-programmes-dans-le-paquet.md) | Tout le code dans le paquet ; `JobHunter.pyw` lance sans installation |

Nouvelle décision : `NNNN-titre-court.md`, numéro suivant, statut et date en tête.
