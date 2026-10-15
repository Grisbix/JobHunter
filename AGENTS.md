# AGENTS.md

Instructions pour tout agent de code travaillant sur ce dépôt. Source unique :
`CLAUDE.md` n'est qu'un import d'une ligne vers ce fichier.

Langue : **français**. Le code, les commentaires, les commits et les docs le sont déjà.

## Version partagée : le moteur ne connaît personne

Tout ce qui est PROPRE À LA PERSONNE vit dans `profil/profil.json`, lu par
`Scripts/profil.py` : identité, métiers visés (`domaines`), compétences, axes et
plafonds du scoring, filtres d'intitulé, niveau, familles retirées par le tri, zones,
mots-clés de collecte, textes des lettres et messages. **Aucun module ne code un
métier, une ville ou un nom.** Pour changer de cible, on change le profil.

- Créer le profil : `python Scripts/premier_lancement.py <cv.pdf|docx>`.
- Profil complet de référence : `profil/exemple_finance_esg.json` (junior en finance
  durable). C'est sur lui que tournent **tous les tests** — `_profil_test.py`, importé
  en tête de chaque `test_*.py`, force `PROFIL_JOBHUNTER` vers ce fichier.
- Une liste de mots du profil accepte `"mot"` (borné à gauche) ou `"re:motif"` (pris tel
  quel). `profil.motif()` les compile.
- Guide utilisateur : `README.md`. Paramétrage par Claude Code : `/configurer-profil` (`.claude/commands/configurer-profil.md`).
- Outils à double-clic (racine) : `installer.bat`, `lancer.bat` (CV pris dans `Mon_CV/`), `planifier.bat`
  (tâche planifiée quotidienne), `mettre_a_jour.bat` → `Scripts/mise_a_jour.py` (git pull, ou ZIP
  GitHub fichier par fichier : données jamais touchées, fichier modifié gardé + `.nouveau`,
  manifeste `.maj_manifeste.json`). **Monter `VERSION` à chaque publication** : c'est elle que
  la mise à jour compare.
- `langues_parlees` (profil) : annonce rédigée dans une autre langue plafonnée à 2, langue
  exigée à 4 (`ats_match.plafond_langue`).
- CI : `.github/workflows/tests.yml` passe les suites sans réseau à chaque push.

## À lire avant de toucher au code

**`Scripts/README.md`** — ce que fait chaque programme, et surtout sa section finale
« Pièges du code, appris à la dure ». Chaque piège y est un bug réel, mesuré, avec son
symptôme. Ne pas redécouvrir ces bugs. `README.md` à la racine s'adresse à l'utilisateur ;
l'historique des changements est dans les messages de commit.

## Commandes

```bash
# L'application — point d'entrée quotidien, à la racine
python JobHunter.pyw

# Collecte + fusion dans la file (voir --help : ~20 sources activables séparément)
python Scripts/job_sources.py --all
python Scripts/job_sources.py --linkedin --apec --efc
python Scripts/job_sources.py --efc --efc-sites monde --eures   # étranger : eFC ×9 sites, EURES

# Documents : CV + lettre par offre
python Scripts/generate_docs.py --top 30
python Scripts/generate_docs.py --all --dry
python Scripts/regenere_docs.py --cv        # régénère l'existant après un changement de gabarit
python Scripts/cv_auto.py --liste           # banque de faits du CV automatique (CV/Faits.json)
python Scripts/generate_docs.py --url <extrait>   # refait CV et lettre d'une offre

# Offres fermées : contrôle (API guest LinkedIn, 404/410) puis retrait, reprise auto sur 429
python Scripts/audit_dispo.py --supprime
python Scripts/audit_dispo.py --rapport     # bilan de l'état, sans réseau

# Candidature semi-automatique — DANS UN VRAI TERMINAL, il attend le clavier
python Scripts/apply_runner.py --canal linkedin
```

### Tests

Pas de pytest, pas de configuration. Chaque suite est un programme autonome qui compte
ses `✅`/`❌` et sort en code non nul si l'un échoue :

```bash
cd Scripts
python test_sources.py       # 126 cas — arbitrage des doublons, accord des lexiques
python test_patterns.py      #  68 cas — formulaires, recherche d'offre, remplissage
python test_scoring.py       # 128 cas — fit_score, fit_fin, plafond ESG, finance classique, langue, vetos, malus
python test_titres.py        #  39 cas — nettoyage d'intitulé, élision, idempotence
python test_appel.py         #  41 cas — formule d'appel, destinataires multiples
python test_lettre.py        #  57 cas — clôture, paragraphe agricole, corps sur mesure, langue
python test_contrats.py      #  47 cas — déduction du type de contrat, « étudiant » = stage
python test_queue_io.py      #  25 cas — exclusion entre processus, atomicité
python test_liens.py         #  22 cas — classement des URLs
python test_suivi.py         #  14 cas — une candidature ne disparaît jamais
python test_zones.py         # 119 cas — zone, pays, région et lieu affiché (IDF = Paris)
python test_audit_dispo.py   #  30 cas — boucle 429, refus 403, source, rythme, sauvegarde
python test_cv_auto.py       #  21 cas — faits valides seuls, déclencheurs, modèles FR/EN (synthétiques)
python test_agregateurs.py   #  21 cas — Adzuna/Jooble : refus, 429, la clé ne fuit jamais
python test_glassdoor_refus.py # 12 cas — Glassdoor : arrêt au premier 403, 429 attendu
python test_rejets_tri.py    #  11 cas — une offre retirée par le tri ne revient pas
python test_tri_file.py      #  52 cas — quant, data, outils de dev, doublons, non-offres, étudiant
python test_site_final.py    #  30 cas — intitulé strict, identité Workday, resondage, coquilles ATS
python test_metriques_hebdo.py # 26 cas — bilan hebdo : dates du suivi, relances, journaux
python test_lecteurs_ats.py  #  65 cas — chaque lecteur d'ATS / page carrière (job_sources), refus 403/404
```

Ces vingt-là tournent **sans réseau** : 954 cas en moins d'une minute, tous au vert
sur le profil d'exemple. Ce sont ceux à passer après une modification.

`test_scoring` génère un cas « sans backspace » **par motif du module** : ajouter un
motif à `ats_match` fait monter son compte sans qu'aucun test ait été écrit.

`test_web_nav_mock.py` (20 cas) mocke réseau et Ollama. `test_web_nav.py` (45 cas) est
synthétique. Tous deux au vert au 2026-09-23.
`test_live_nav.py` et `test_acces_sites.py` sortent vraiment sur le web — ne pas les
lancer machinalement.

Il n'y a pas de sélection par nom de cas : la granularité est le fichier.

> Les comptes ci-dessus sont **mesurés**. Ceux du tableau de `Scripts/README.md` ont
> dérivé (il annonce 24 cas pour `test_sources`, qui en fait 126) et il ne mentionne ni
> `test_scoring.py` ni `test_liens.py`. Recompter plutôt que recopier.

## Architecture

### Trois fichiers de données, trois contrats d'accès

```
Scripts/apply_queue.json    les offres          → passer par queue_io
Scripts/descriptions.json   leur texte, à part  → queue_io le réinjecte, transparent
Scripts/suivi.json          les candidatures    → passer par suivi_io
```

**Ne jamais lire ou écrire ces fichiers en `json.load`/`json.dump` direct.**

- `queue_io.charger()` lit sans verrou (les écritures sont atomiques, donc une lecture ne
  voit jamais un fichier à moitié écrit) et réinjecte les descriptions.
  `queue_io.transaction()` est le seul chemin d'écriture : verrou, **relecture fraîche à
  l'intérieur du verrou**, écriture atomique à la sortie, annulation si le bloc lève.
- Les descriptions vivent à part parce qu'elles pesaient 64 % du fichier que treize
  programmes réécrivaient en entier pour changer un seul champ. `transaction(descriptions=False)`
  saute leur lecture quand on ne touche qu'à un `fit` ou un statut.
- `suivi.json` est la donnée **la moins reconstituable** du projet : une offre perdue, le
  scan la retrouve demain ; une candidature perdue ne revient jamais. `suivi_io.poser()`
  écrit une entrée sous verrou sur l'état relu — jamais un instantané mémoire.
- **Seul `suivi.json` est versionné.** La file, les descriptions et les scans sont hors
  git depuis le 2026-09-23 : `pipeline_quotidien.sauvegarder()` les copie chaque jour dans
  `Scripts/_sauvegardes/<date>/`, avant toute étape, sept jours glissants. Les documents
  générés sont hors git depuis le 20/09 ; l'historique complet d'avant la purge, 978 Mo,
  est dans `../_sauvegardes/Recherche_emploi_historique_complet_2026-09-23.bundle`.

L'identité d'une offre est `queue_io.oid(offre)` = `"entreprise|poste"`. Surtout pas
l'URL : elle change quand un doublon mieux classé la promeut.

### Le verrou, et le code de sortie 3

Exclusion inter-processus par fichier (`jutil.prendre_verrou` / `rendre_verrou` / `garder`).
**Un programme qui trouve la file occupée sort en code 3 sans rien modifier.** Un verrou
vivant ne se casse jamais ; toute requête réseau passe par les fonctions bornées.
Détail (réentrance, PID recyclés, double verrou de `job_sources`, timeouts httpx) :
`.claude/rules/verrous.md`.

**La collecte du pipeline est en cinq passes, fusionnées chacune** (ATS/Workday/V.I.E ;
LinkedIn ; eFC/EURES ; APEC/France Travail/Adzuna/Jooble ; Glassdoor/WTJ en dernier).
Talent et Indeed sont hors de `--all` depuis le 2026-10-03 (0 offre, 403) ; Adzuna et
Jooble passent par leur API officielle, clé dans les fichiers adzuna.json / jooble.json du dossier Scripts
(ignorés par git, à créer par l'utilisateur ; absents = source ignorée).
`job_sources` ne fusionne qu'à la fin de sa passe : en une seule passe `--all`, un
dépassement de durée perdait toute la collecte du jour — quatre matins sur cinq du 24 au
28/09/2026 ; en trois passes, deux dépassaient encore le 30/09.

**`_req_borne` réutilise les connexions.** Appelée avec le module `httpx`, elle passe par
un `httpx.Client` partagé : rouvrir une connexion TLS par requête triplait la durée
(talan 8 min → 1,7 ; un flux Workday 7,8 → 1,6). Talent ne recharge plus les fiches déjà
dans la file.

**Une limite de débit s'attend, un refus d'entrée s'arrête.** Un 429 dit « reviens plus
tard » : `audit_dispo` fait une pause (Retry-After, sinon 15 min doublées jusqu'à 60),
reprend où il s'était arrêté, et garde son état dans `_audit_dispo.json` pour reprendre
d'une exécution à l'autre. Un 403/999/CAPTCHA (APEC derrière DataDome) est un refus :
pas de boucle dessus, et pas de nouvelle tentative avant 30 jours. Dans le pipeline,
l'étape 4b n'a droit qu'à une pause et rend le code 4 si elle n'a pas fini — normal.

### Règles chargées à la demande

Le détail par domaine vit dans `.claude/rules/`. Chaque fichier déclare en
frontmatter `paths:` les fichiers qu'il gouverne, et Claude Code ne l'injecte que
quand on touche l'un d'eux — donc zéro coût de contexte le reste du temps. Les autres
agents (Codex, Cursor) les lisent en suivant le lien.

| Règle | Se déclenche sur |
|---|---|
| `.claude/rules/scoring.md` | `ats_match.py`, `tri_file.py` — `fit_score`, plafond ESG, malus sur l'intitulé seul |
| `.claude/rules/motifs.md` | `ats_match.py`, `job_sources.py`, `tri_file.py` — regex, heredoc, sous-chaînes, `\b` final |
| `.claude/rules/documents.md` | `tailor_application.py`, `generate_docs.py`, `regenere_docs.py`, `sync_docs.py`, `chemins.py` |
| `.claude/rules/navigation-web.md` | `web_nav.py`, `site_strategies.py`, `apply_runner.py`, `acces.py` |
| `.claude/rules/app-bureau.md` | `JobHunter.pyw` |
| `.claude/rules/verrous.md` | `jutil.py`, `job_sources.py`, `linkedin_desc.py`, `pipeline_quotidien.py`, `audit_dispo.py` |

## Limites qui sont des décisions, pas des manques

Elles tiennent depuis le début du projet et ne se rediscutent pas au détour d'une tâche.
Le détail est dans `.claude/rules/navigation-web.md` ; la version courte, qui vaut partout :

- **Aucune soumission automatique.** Le clic final d'envoi est celui de l'utilisateur.
  N'ajouter aucun drapeau `--auto` / `--submit` à `apply_runner.py`, ni ailleurs.
- **Aucun contournement anti-bot**, aucune résolution de CAPTCHA.
  Ni moteur furtif, ni masquage de l'automatisation, ni profil Chrome personnel :
  le navigateur se présente comme automatisé (détail : `.claude/rules/navigation-web.md`).
- **Aucun mot de passe manipulé par les programmes.**
- **Aucune création de compte automatique**, aucune lecture de boîte mail par programme.
- Le dépôt est **local, sans remote**, parce qu'il contient des données personnelles.

## Invariants à ne pas casser

**Ne jamais coder une racine en dur.** Les chemins du projet ont bougé quatre fois en deux
jours et tout ce qui codait une racine a cassé en silence — dont une veille qui s'est
déclarée `success` pendant deux mois en ne suivant plus que 2 comptes sur 44. Détecter par
marqueur : le premier dossier candidat, en remontant, qui contient réellement un fichier
témoin. `JobHunter.pyw::_racine()` cherche `Scripts/apply_queue.json` et fonctionne donc
où qu'on le place.

**Les regex ne s'écrivent pas via un heredoc shell** — détail et pièges de motifs dans
`.claude/rules/motifs.md`.

**Toute suppression automatique doit épargner les offres présentes dans `suivi.json`.**
Une annonce ferme *après* qu'on y a postulé : sans cette garde, la purge efface en priorité
celles auxquelles l'utilisateur a candidaté.

**`sys.stdout.reconfigure(encoding="utf-8", errors="replace")` en tête de tout programme
qui affiche un emoji ou un accent.** Sans lui, la sortie redirigée — tuyau, log, tâche
planifiée — retombe sur cp1252 et lève `UnicodeEncodeError` à la première ligne.

**Windows ignore la casse des noms de fichiers.** Deux noms qui ne diffèrent que par la
casse sont un seul fichier : toute déduplication de noms groupe en minuscules.

**Vérifier un import en chargeant le module, jamais en parsant l'AST.** `ast.parse` passe
sur un `import` manquant ; l'erreur ne sort qu'à l'exécution.

**Une collecte vide a deux causes opposées** — rien à prendre, ou refus d'entrée.
`job_sources.INCIDENTS` compte les refus et `main()` les affiche, pour qu'un scan
entièrement bridé ne ressemble pas à une journée calme (et qu'on ne le relance pas, ce qui
est exactement ce qu'il ne faut pas faire face à un quota).

## Environnement

Python par défaut : `C:\Python314\python.exe`. Dépendances dans `requirements.txt`
(customtkinter, playwright, python-docx, openpyxl, PyMuPDF, httpx).
Pas de venv dans ce dépôt : les programmes tournent sur l'interpréteur système.
