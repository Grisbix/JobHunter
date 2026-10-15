# Nouveautés de JobHunter

La mise à jour (`mettre_a_jour.bat`, `./mettre_a_jour.sh` ou le bouton de l'application)
affiche les sections plus récentes que ta version. Format : `## x.y.z — date`, la plus
récente en haut.

## 1.3.0 — 2026-10-15

- **Mise à jour depuis l'application** : quand une version sort, JobHunter propose de
  l'installer tout de suite, montre le déroulé, puis se relance. Aussi dans
  « 🔧 Maintenance ▾ → Accès & diagnostic → Mettre à jour JobHunter ».
- **Nouveautés affichées** avant et après chaque mise à jour (ce fichier).
- **Contrôle après installation** : tous les scripts sont compilés et les modules
  centraux chargés ; en cas d'échec, retour automatique à la version d'avant.
- **`--annuler`** : revient à la version d'avant la dernière mise à jour.
- **Tes modifications sont reconnues dès la première mise à jour** : la référence est le
  ZIP officiel de ta version. Un fichier que tu as changé n'est plus jamais écrasé.
- **Les fichiers retirés du programme sont enlevés** (s'ils n'ont pas été modifiés),
  avec copie dans la sauvegarde.
- **Nouveaux réglages du profil signalés** après la mise à jour.

## 1.2.0 — 2026-10-15

- Plus aucune lecture de boîte mail par programme : un code reçu par mail se saisit à la main.
- Dépendances bornées, tests automatiques sous Windows et Linux.
- Profil d'exemple entièrement fictif ; documentation nettoyée.
- Plafond de langue : une annonce dans une langue que tu ne parles pas ne monte plus à 10.
