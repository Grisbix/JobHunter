# 0011 — Une application autonome pour l'utilisateur, le code source pour qui le modifie

**Statut** : accepté le 2026-10-19 (étape F4 de la feuille de route, JobHunter 2.9.0).

## Contexte

Installer JobHunter demandait Python 3.12+, un ZIP à dézipper, `installer.bat` (bibliothèques
et navigateur Chromium), puis `lancer.bat`. C'est raisonnable pour qui veut modifier le code,
dissuasif pour qui veut seulement chercher un emploi. L'utilisateur voulait un bouton
« Télécharger » qui donne un installateur, comme le projet Ibaraki, sans Python obligatoire,
le code restant téléchargeable pour qui veut personnaliser.

Contraintes :
- l'application lance ses programmes en sous-processus, par `[PY, "-m", module]` : sans
  Python, il faut un exécutable qui comprenne `-m` ;
- les données de l'utilisateur ne doivent jamais vivre dans le dossier du programme, que la
  mise à jour remplace ;
- embarquer Chromium alourdirait l'installateur d'environ 150 Mo.

## Décision

- **Deux exécutables compilés par PyInstaller, dans un même dossier** :
  `JobHunter.exe` (fenêtre, sans console) et `jobhunter-cli.exe` (console). Le second sert
  d'interpréteur aux sous-processus : il comprend `-m module`, `-c code` et les commandes de
  `jobhunter` (`jobhunter.gele.aiguiller`). `jobhunter.gele.interpreteur()` le désigne ;
  sous Python, c'est `python.exe` (jamais `pythonw.exe`, sans sortie standard).
- **Données dans `Documents/JobHunter`** (ou `JOBHUNTER_RACINE`). Au premier lancement, le
  squelette livré y est copié (profils d'exemple, réglages des sources, dossier du CV),
  sans jamais remplacer un fichier présent.
- **Installateur Inno Setup**, pour l'utilisateur seul et sans droits d'administrateur
  (`%LOCALAPPDATA%\Programs\JobHunter`). Il remplace le dossier du programme en entier ; la
  désinstallation ne touche pas aux données.
- **Construit par la CI** (`.github/workflows/installateur.yml`) à chaque release, contrôlé
  (installation silencieuse, premier lancement), et attaché à la release. Le README pointe
  sur `releases/latest/download/JobHunterSetup.exe`.
- **Pas de Chromium embarqué** : sans le Chromium de Playwright, la collecte lance Chrome ou
  Edge du système (`navigation.navigateur.lancer`) ; Edge est présent sur tout Windows 10/11.
  La candidature et les connexions utilisaient déjà Chrome.
- **Mise à jour** : l'application installée ne remplace pas ses fichiers un par un ; elle
  annonce la nouvelle version et ouvre la page de la release, où l'on télécharge le nouvel
  installateur.

## Conséquences

- Deux publics, deux chemins : l'installateur pour l'usage, le code source (ZIP ou clone,
  avec Python) pour personnaliser ; le README présente les deux.
- L'application installée occupe environ 245 Mo (Python, Playwright, bibliothèques).
- La tâche planifiée du matin (`planifier.bat`) reste réservée à l'installation depuis le
  code source ; l'application installée collecte depuis son bouton « Actualiser les offres ».
- Les programmes de test réseau (`test_*`) lisent la file à l'import : ils sont exclus du
  contrôle de chargement de l'exécutable.
