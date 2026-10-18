# Nouveautés de JobHunter

La mise à jour (`mettre_a_jour.bat`, `./mettre_a_jour.sh` ou le bouton de l'application)
affiche les sections plus récentes que ta version. Format : `## x.y.z — date`, la plus
récente en haut.

## 1.13.0 — 2026-10-18

Rien ne change dans ce que fait JobHunter.

- Charger le moteur ne crée plus de dossiers : ils le sont au moment d'écrire un CV, une
  lettre ou un message.
- Le socle (stockage, profil, réseau) est entièrement typé, vérifié par mypy en CI.
- Documentation : `docs/architecture.md` et les décisions d'architecture (`docs/adr/`).

## 1.12.0 — 2026-10-18

Une entrée unique pour tous les programmes : `python -m jobhunter` liste les commandes
(`collecte`, `documents`, `postuler`, `pipeline`, `maj`…). Les anciennes lignes
(`python Scripts/generate_docs.py …`) marchent toujours.

## 1.11.0 — 2026-10-18

- L'application rejoint le paquet `src/jobhunter/app` ; `JobHunter.pyw` (double-clic)
  ne fait plus que la lancer. Rien ne change à l'écran.
- La mise à jour vérifie aussi que l'application et la navigation se chargent, et revient
  en arrière sinon.

## 1.10.0 — 2026-10-18

Rien ne change dans ce que fait JobHunter. La navigation web (`web_nav.py`, près de
4 000 lignes) et `site_strategies.py` rejoignent le paquet `src/jobhunter/navigation`,
une section par module ; les anciens noms restent valables.

## 1.9.0 — 2026-10-18

- CV, lettre et message court rejoignent le paquet `src/jobhunter/documents` ;
  `tailor_application.py`, `message_offre.py` et `cv_auto.py` restent valables.
- Correctif : lire la file par un chemin relatif (`apply_queue.json` depuis `Scripts/`)
  rendait les offres sans leur description.

## 1.8.0 — 2026-10-18

Rien ne change dans ce que fait JobHunter. La collecte (`job_sources.py`, près de
5 000 lignes) est découpée en un module par source dans `src/jobhunter/sources` ;
`python Scripts/job_sources.py ...` marche comme avant, et `python -m jobhunter.sources`
aussi.

## 1.7.0 — 2026-10-18

Rien ne change dans ce que fait JobHunter. Le calcul des notes, de la langue, des zones et
le tri des offres rejoignent le paquet `src/jobhunter/scoring` ; les anciens noms de
programme (`tri_file.py`, `zones.py`…) restent valables, en ligne de commande comme dans
le code.

## 1.6.0 — 2026-10-18

Rien ne change dans ce que fait JobHunter. Le profil et les requêtes réseau (limitées en
durée totale, pour qu'un site lent ne bloque jamais la collecte) rejoignent le paquet
`src/jobhunter/`. Ces requêtes ont maintenant leurs propres tests, et un nouveau contrôle
vérifie que chaque fonction qu'un programme appelle sur un autre existe bien.

## 1.5.0 — 2026-10-18

Rien ne change dans ce que fait JobHunter. Le code de stockage (la file d'offres, le suivi
des candidatures, l'écriture sûre et le verrou entre programmes) part dans un nouveau
dossier `src/jobhunter/` : première étape du découpage du moteur en paquet. La mise à jour
ajoute ce dossier ; les anciens noms (`queue_io`, `suivi_io`, `jutil`) restent valables.
Les tests sont désormais écrits avec pytest (1 155 tests).

## 1.4.0 — 2026-10-17

Version « atelier » : rien ne change dans ce que fait JobHunter, mais le code est
désormais vérifié comme un logiciel professionnel (voir `docs/plan-professionnalisation.md`).

- **Banc de non-régression** : 384 offres fictives dont chaque décision (note, tri, zone,
  langue, message, lettre) est comparée à une référence à chaque modification.
- Code mis en forme et vérifié automatiquement (ruff), contrôles avant chaque commit,
  environnement de développement reproductible (uv), tests lancés par pytest.
- Deux séries de tests qui ne tournaient jamais (relances, navigation) sont branchées.
- La mise à jour remplacera presque tous les fichiers du programme (mise en forme) : un
  fichier que tu as modifié est gardé, la nouvelle version posée à côté en `.nouveau`.

## 1.3.2 — 2026-10-17

- **LinkedIn : la collecte ne perd plus les pages limitées.** Depuis le 13/10, LinkedIn
  répond « trop de requêtes » (429) dès les premières pages ; chaque page refusée était
  perdue, et la collecte LinkedIn était tombée à quelques offres par jour. Désormais les
  pages sont espacées, et un 429 fait attendre puis redemander la même page ; la passe
  LinkedIn s'arrête proprement au bout de 45 min. Un refus (403/999) arrête LinkedIn pour la journée.

## 1.3.1 — 2026-10-15

- L'installeur note l'empreinte des fichiers installés : une installation faite depuis
  le ZIP de `main` (entre deux versions) reconnaît, elle aussi, tes modifications.
- Dans une copie sans fichier `VERSION`, la mise à jour le dit et ne tente rien.
- Un fichier que tu as modifié et que la nouvelle version ne change pas n'est plus
  signalé, et aucun `.nouveau` inutile n'est posé à côté.

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
- Un clone git neuf sous Windows ne voit plus les `.bat` comme modifiés (le premier
  `git pull` échouait).
- customtkinter 6 accepté (testé : l'application s'ouvre et fonctionne avec la 5 et la 6).

## 1.2.0 — 2026-10-15

- Plus aucune lecture de boîte mail par programme : un code reçu par mail se saisit à la main.
- Dépendances bornées, tests automatiques sous Windows et Linux.
- Profil d'exemple entièrement fictif ; documentation nettoyée.
- Plafond de langue : une annonce dans une langue que tu ne parles pas ne monte plus à 10.
