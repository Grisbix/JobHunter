# Nouveautés de JobHunter

La mise à jour (`mettre_a_jour.bat`, `./mettre_a_jour.sh` ou le bouton de l'application)
affiche les sections plus récentes que ta version. Format : `## x.y.z — date`, la plus
récente en haut.

## 2.15.0 — 2026-10-19

- **« Pourquoi ce fit »** dans la fiche de chaque offre : les compétences trouvées par
  axe, la note de vocabulaire, le plafond et sa raison (intitulé du cœur de cible,
  métier visé en second, veto HSE ou hors cible), les bonus et malus de l'intitulé, la
  langue de l'annonce et l'expérience demandée. La note ne change pas : c'est le même
  calcul, raconté (`scoring.fit.expliquer`).

## 2.14.0 — 2026-10-19

- **Relecture des lettres** (`jobhunter relecture`, ou Maintenance → Documents →
  « Relire les lettres ») : une seconde passe qui signale, sans rien réécrire, ce qui
  cloche dans une lettre — candidat qui se dévalorise, superlatif creux, « excellent »
  pour une langue, tiret cadratin ou barre oblique, redites, autre entreprise nommée
  (copier-coller), destinataire que l'annonce ne nomme pas, et ce qu'une annonce piégée
  aurait pu glisser dans une lettre écrite par IA (consigne au modèle, adresse inconnue).
- **Contrôle des dossiers** : un intitulé entre crochets (« [Open to internal and
  external applicants] ») n'est plus pris pour un gabarit oublié.
- Menu Maintenance : « Contrôler les dossiers » ajouté ; « Tests live » relancé (il
  pointait vers un fichier retiré en 2.0).

## 2.13.0 — 2026-10-19

- **Annuaire de 3 600 entreprises** dans le panneau Entreprises : tape un nom (« Alan »,
  « Qonto »…) dans le champ d'ajout ou clique « Annuaire », choisis, et l'entreprise est
  suivie par l'API publique de Lever, Ashby ou Greenhouse dès la prochaine collecte.
  Aucune recherche sur le web : les annuaires viennent du projet jobsync (licence MIT),
  livrés avec l'application. Une entreprise déjà suivie est marquée.
- **Interface en anglais, journal compris** : les messages de l'application (sélection,
  annulation, sauvegarde, mises à jour, relances…) et ses boîtes de dialogue suivent
  le réglage de langue. La sortie des programmes lancés reste en français.

## 2.12.0 — 2026-10-19

- **Clés d'API saisies dans l'application, au bon endroit.** Panneau Accès : choisir
  France Travail, Adzuna ou Jooble, puis « Saisir la clé » (ou double-clic). Une petite
  fenêtre demande les champs, masque le secret, et écrit le fichier que la source lit
  vraiment (`Scripts/francetravail.json`, `adzuna.json`, `jooble.json`). Avant, le
  bouton France Travail rangeait la clé dans `api_keys.json`, qu'aucune source ne lit :
  elle n'était jamais utilisée. `jobhunter acces --set-key francetravail` suit la même
  règle.
- **Collecter une source seule** depuis le panneau Accès, pour essayer une clé tout de
  suite. Une source refusée il y a moins de 30 jours reste bloquée ; une API officielle
  qui refuse la clé affiche « clé refusée — vérifie-la » et se réessaie dès la clé
  corrigée.
- Panneau Accès en deux onglets, « Collecte des offres » et « Connexions pour
  candidater » : le second tableau ne sort plus de l'écran.
- Panneau Entreprises : un filtre (nom, outil, adresse) et un champ d'ajout qui dit quoi
  coller.
- L'application sans console (`JobHunter.pyw`, l'exe) ne peut plus tomber sur un module
  qui règle l'encodage de la console au chargement.

## 2.11.0 — 2026-10-19

- **Lever en Europe.** Certaines entreprises sont hébergées dans la région européenne de
  Lever : leur flux répondait « introuvable » et leurs offres manquaient. La collecte les
  cherche désormais aussi sur `api.eu.lever.co`.
- **Aucune donnée personnelle ne peut entrer dans le dépôt public** : un contrôle
  (`outils/donnees_perso.py`, lancé avant chaque commit et par la CI) refuse profil, file,
  suivi, lettres, CV et clés d'API, même ajoutés de force.
- Dépôt : modèles d'issue et de PR, revue des dépendances (une vulnérabilité connue bloque
  la PR), signalement privé des failles activé.

## 2.10.1 — 2026-10-19

Sécurité, sans changement visible :

- seules les adresses `http(s)` sont ouvertes : une adresse `file://` venue d'une page ou
  d'un réglage ne peut plus faire lire un fichier de ta machine ;
- un plan de site XML avec DOCTYPE ou entités est refusé (bombe XML) ;
- une archive de mise à jour ne peut plus écrire hors du dossier du programme ;
- l'application installée ignore le crochet de test `JOBHUNTER_ACTION` ;
- CI : actions épinglées par empreinte, droits en lecture seule sauf la publication,
  analyse CodeQL ; l'installateur est publié avec son empreinte SHA-256 et une attestation
  de provenance signée (`gh attestation verify`). Politique : `SECURITY.md`.

## 2.10.0 — 2026-10-19

- **L'interface en anglais.** Maintenance → « Langue : English », puis relance
  JobHunter : la navigation, les boutons, les panneaux et les en-têtes passent en anglais
  (« Language: français » pour revenir). Le profil, les lettres et les statuts du suivi
  gardent leur langue. Un texte pas encore traduit reste en français.
- **Le dépôt GitHub se présente en anglais** (`README.md`) ; la version française est dans
  `README.fr.md`.

*English: the interface can now be switched to English (Maintenance → “Langue : English”,
then restart). The repository README is in English; the French one is `README.fr.md`.*

## 2.9.0 — 2026-10-19

- **JobHunter s'installe sans Python.** `JobHunterSetup.exe`, attaché à chaque version sur
  GitHub, installe l'application pour toi seul, sans droits d'administrateur, avec un
  raccourci au menu Démarrer. Tes données vivent dans `Documents\JobHunter` : ni la mise à
  jour ni la désinstallation n'y touchent. Le code source reste téléchargeable pour qui veut
  personnaliser.
- **Plus besoin du navigateur de Playwright pour collecter.** S'il n'est pas installé, la
  collecte utilise Chrome ou Edge, déjà sur ta machine.
- Dans l'application installée, « Mettre à jour » ouvre la page de la nouvelle version, où
  tu télécharges le nouvel installateur.

## 2.8.0 — 2026-10-19

Les panneaux « Entreprises », « Accès » et « Mes CV » montrent enfin des chiffres justes.

- **Entreprises** : une ligne par entreprise réellement suivie, avec l'outil qui lit ses
  offres (Workday, Lever, SuccessFactors… ou son site carrière), le nombre d'offres de ta
  file qui en viennent, le meilleur fit et la date de la dernière. Les comptes sont exacts :
  l'ancien panneau comptait par bout d'adresse (546 offres pour « Bil », à cause de
  « mobilité ») et laissait la colonne ATS vide.
  - Colle l'adresse d'une page carrière et clique **Suivre** : un Greenhouse, Lever, Ashby,
    Recruitee, SmartRecruiters, Teamtailor, Workable ou Workday est reconnu et lu par son
    API dès la prochaine collecte ; un autre site est lu par le navigateur.
  - **Ne plus suivre** retire l'entreprise de la collecte.
- **Accès** : chaque source de la collecte, ce qu'il lui faut (rien, ou une clé
  d'API) et l'état de sa dernière collecte (ok, refusé jusqu'à telle date, limité, clé à
  créer). Adzuna et Jooble y figurent ; Indeed, sorti de la collecte, n'y est plus. Les
  connexions pour candidater sont dans un second tableau. Aucune clé ni aucun mot de passe
  n'est lu : seule la présence du fichier compte.
- **Mes CV** : un dossier par offre, CV et lettre ensemble, les mieux classées d'abord,
  avec son état (✓ prêt, ⚠ PDF à refaire, ✗ incomplet). Le bouton **CV ⇄ lettre** passe
  de l'un à l'autre, **Faits du CV** affiche ta banque de faits. Avant : deux listes de
  1 983 et 1 200 fichiers à plat.
- L'en-tête de la fenêtre porte le nom de la page ouverte, au lieu de « Suivi des
  candidatures » partout.

## 2.7.0 — 2026-10-19

- **Dix programmes en moins.** Des outils de réparation ponctuelle, déjà passés sur les
  données ou remplacés par mieux, quittaient rarement leur dossier et brouillaient la liste.
  Ils sont retirés :
  - `audit_fraicheur` et `verify_links` : remplacés par le contrôle de disponibilité
    (`audit_dispo`) ;
  - `offres_depuis_site`, `probe_ats_esg` et `homepages_linkedin` : remplacés par les flux
    ATS suivis et `probe_ats_queue` ;
  - `deplace_docs`, `reclasse_domaines`, `redetecte_contrats`, `refresh_desc_efc` et
    `fix_wtj_urls` : réparations faites une fois, devenues inutiles. L'entrée « Fix WTJ »
    quitte le menu Maintenance.

  Le code reste dans l'historique git pour qui en aurait besoin.

## 2.6.0 — 2026-10-19

- **Le bon exemplaire d'un poste publié dans plusieurs villes.** Quand une entreprise
  publie le même poste à Paris, Lyon et Berlin, un seul entre dans ta file. Jusqu'ici,
  c'était le premier vu, au hasard ; c'est désormais celui de ta zone la plus prioritaire.
  Les autres villes sont notées, et la fiche les affiche (« Aussi à : »).
- **Les intitulés retouchés ne s'accumulent plus.** Quand un employeur renomme son annonce
  (même lien, nouveau titre), les anciennes versions restées dans la file sont retirées au
  tri. Seule la version actuelle reste, sauf si tu as déjà agi sur une autre : celle de
  ton suivi est toujours gardée.

## 2.5.0 — 2026-10-19

- **Ton classement face à tes choix.** `python JobHunter.pyw evaluation` compare la note de
  chaque offre à ce que tu en as fait : postulé ou à postuler d'un côté, « mauvaise » ou
  « pas intéressé » de l'autre. Il dit si les offres que tu retiens sont bien mieux notées
  que celles que tu écartes (avec la marge d'incertitude), et lesquelles le classement
  surestime ou sous-estime le plus. `--enregistrer` garde le résultat pour comparer plus
  tard. Plus tu marques d'offres, plus le chiffre est fiable.

## 2.4.3 — 2026-10-19

- **Configuration d'exemple** : 10 des 16 comptes Greenhouse ne répondaient plus (404) :
  ces entreprises recrutent ailleurs désormais. 7 ont été retrouvées et suivent leur
  nouvel outil (Lever : Pigment, Swile, Vestiaire Collective ; Ashby : Back Market,
  Sweep ; SmartRecruiters : EcoVadis ; Recruitee : iBanFirst). ClarityAI, Payfit et
  Spendesk sont retirés. Si ta configuration les contient encore,
  `python JobHunter.pyw probe_ats --slugs <nom>` cherche leur nouvel outil.
- En coulisse : les sources sont testées sur de vraies réponses enregistrées, rejouées sans
  réseau.

## 2.4.2 — 2026-10-19

- En coulisse, rien de visible : chaque fonction publique du moteur est documentée au même
  format, et l'outil de contrôle l'exige désormais.

## 2.4.1 — 2026-10-19

- En coulisse : le dossier de tes données (`Scripts/`) n'est plus ajouté au chemin
  d'import de Python. C'était un reste de l'ancienne organisation : un fichier `.py`
  déposé là pouvait passer avant un module du programme portant le même nom. Rien ne
  change à l'usage.

## 2.4.0 — 2026-10-19

- **Ce que rapporte chaque source.** À la fin de chaque collecte, une ligne par source :
  offres ramenées, nouvelles, pertinentes (fit ≥ 8), temps passé, et un verdict qui dit
  POURQUOI : « ok », « rien à prendre » (journée calme), « limité » (le site a demandé de
  ralentir), « partiel » (erreurs en route) ou « refusé » (accès refusé, CAPTCHA). Une
  collecte vide ne ressemble plus à une journée sans nouveauté.
- `python JobHunter.pyw rendement` : le bilan des 14 derniers jours (`--jours 30` pour
  plus), les sources les plus rentables d'abord ; une source refusée à chaque collecte est
  signalée. Aucun contournement : la retirer se décide à la main.

## 2.3.0 — 2026-10-19

- **Chaque dossier est contrôlé avant de partir.** Pour le CV et la lettre qui seront
  vraiment joints : le fichier existe, s'ouvre, contient du texte, tient sur une page,
  porte ton nom, ton courriel et ton téléphone, et aucun gabarit n'est resté vide
  (« [nom du poste] »…). Le panneau Candidatures l'affiche pour chaque offre, la fiche
  aussi ; un dossier à revoir ne bloque rien, c'est toi qui décides.
- **Le bon fichier est joint** : quand une offre pointait sur la lettre en .docx alors que
  son PDF à jour existait à côté, c'est désormais le PDF qui part.
- `python JobHunter.pyw controle` : bilan de tous les dossiers, sans rien modifier. La
  routine quotidienne le fait aussi après les dossiers et t'alerte s'il y en a à revoir.

## 2.2.0 — 2026-10-19

- **Postuler depuis l'application, sans console.** Coche des offres, « Postuler la
  sélection » : un panneau s'ouvre. Pour chaque offre, JobHunter ouvre la page dans
  Chrome, remplit le formulaire, joint CV et lettre et surligne le bouton d'envoi. Tu
  vérifies, **tu cliques Envoyer dans Chrome**, puis « J'ai envoyé » dans le panneau.
  Boutons : Sauter, Re-remplir, Rouvrir l'offre, Arrêter. Un CAPTCHA ou une connexion
  t'est signalé : c'est à toi, JobHunter ne contourne rien.
- **Une preuve, pas seulement une déclaration.** Après « J'ai envoyé », JobHunter regarde
  la page — sans rien cliquer — et note dans ton suivi :
  - « envoi confirmé » si le site affiche sa confirmation (« Merci pour votre
    candidature », « Application submitted »…) ;
  - « envoi non confirmé » sinon : vérifie ta boîte mail ou ton espace candidat. Rien
    n'est jamais renvoyé automatiquement.
  Une capture de la page est gardée dans `Scripts/_preuves/` ; la fiche de l'offre montre
  l'état et l'extrait.
- Plus de double confirmation : « J'ai envoyé » suffit, la candidature passe à « postulé ».
  « Confirmer une candidature envoyée… » (fiche, clic droit) reste là pour un envoi fait
  ailleurs.

## 2.1.1 — 2026-10-19

- **Mac et Linux** : les boutons qui ouvrent un document ou un dossier (CV, lettres,
  dossier du projet) plantaient — ils appelaient une fonction propre à Windows. Ils
  passent maintenant par l'application du système (`open` sur Mac, `xdg-open` sur
  Linux). Rien ne change sous Windows.
- En coulisse, rien de visible : tout le programme est désormais vérifié par l'outil de
  typage, et chaque décision de conception est reliée au code qui l'applique.

## 2.1.0 — 2026-10-18

- **Les offres fermées sont enfin retirées.** Le contrôle de disponibilité était coupé
  chaque matin au bout de 45 min, avant d'arriver à la suppression : il trouvait 30 à 60
  offres fermées par jour et n'en retirait aucune. Il s'arrête maintenant de lui-même à
  temps, puis retire ce qu'il a trouvé.
- **Une fois par semaine, le dimanche**, au lieu de chaque jour : la collecte des autres
  jours dure ~45 min de moins. `python JobHunter.pyw pipeline --dispo-jour 2` le déplace
  au mercredi ; `--dispo` le lance aujourd'hui.
- Les tests n'écrivent plus dans le fichier d'état du contrôle de disponibilité de ton
  dossier quand on les lance chez toi.

## 2.0.0 — 2026-10-18

Rien ne change dans ce que fait JobHunter ; ce qui change, c'est la façon de lancer les
commandes à la main. Passe par la 1.15 avant (la mise à jour le fait d'elle-même si tu
es à jour).

- Tout le programme vit maintenant dans `src/jobhunter` ; `Scripts/` ne garde que tes
  données (file d'offres, suivi, réglages, journaux).
- Les commandes se lancent par `python JobHunter.pyw <commande>` : `collecte`,
  `documents`, `postuler`, `pipeline`, `maj`… (`python JobHunter.pyw aide` les liste), et
  tout autre programme par son nom (`python JobHunter.pyw probe_ats`). Les anciennes
  lignes `python Scripts/xxx.py` ne marchent plus.
- Double-clic, `lancer.bat`, `mettre_a_jour.bat` : rien ne change.
- **Collecte planifiée** : si tu l'avais programmée avec `planifier.bat` ou
  `./planifier.sh`, relance-le une fois — l'ancienne tâche vise un fichier qui n'existe
  plus. La mise à jour te le signale si c'est le cas.

## 1.15.0 — 2026-10-18

Version de passage vers la 2.0 : installe-la avant la 2.0. Rien ne change dans ce que
fait JobHunter.

- La mise à jour vérifie la nouvelle version avec le code de cette nouvelle version.
  Sans cela, la 2.0, qui range autrement les programmes, serait refusée à tort.
- Le moteur, les tests et l'application n'utilisent plus les anciens fichiers de
  `Scripts/` (`job_sources.py`, `queue_io.py`…), qui disparaîtront en 2.0.

## 1.14.0 — 2026-10-18

Rien ne change dans ce que fait JobHunter.

- Charger le moteur ne lit plus aucun fichier : ce qui vient du profil se calcule au
  premier usage. Changer de profil (premier lancement) vaut aussitôt partout.
- Le pipeline du matin écrit, à côté de son journal habituel, un journal du moteur
  horodaté (`Scripts/_logs/pipeline_<date>_<heure>_moteur.log`).
- `python Scripts/chemins.py` remarche (il levait une erreur).

## 1.13.0 — 2026-10-18

Rien ne change dans ce que fait JobHunter.

- Charger le moteur ne crée plus de dossiers : ils le sont au moment d'écrire un CV, une
  lettre ou un message.
- Le socle (stockage, profil, réseau) et le calcul des notes sont entièrement typés,
  vérifiés par mypy en CI.
- Documentation : `docs/architecture.md` et les décisions d'architecture (`docs/adr/`).
- Le moteur s'installe comme un paquet (`pip install -e .`) : la commande `jobhunter` existe
  alors directement.

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
