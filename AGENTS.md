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
  fichier retiré enlevé s'il est intact, contrôle de chargement puis retour arrière automatique,
  `--annuler`). **À chaque publication : monter `VERSION`, ajouter sa section en tête de
  `CHANGELOG.md`, et créer la release `v<version>`** — l'étiquette sert de référence à la
  première mise à jour d'une installation par ZIP (sans elle, un fichier modifié par
  l'utilisateur ne peut pas être reconnu).
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

### Tests et contrôles

```bash
uv sync                                  # venv .venv, versions verrouillées (uv.lock)
uv run pytest -q                         # 1 142 tests sans réseau (~2 min)
uv run pytest -q tests/test_scoring.py   # un fichier ; -k mot pour filtrer les cas
uv run pytest -q --cov --cov-report=term # avec la couverture (seuil en CI)
uv run python outils/banc.py comparer outils/banc_reference.json   # non-régression
uv run ruff check . && uv run ruff format --check .
```

**Le banc de non-régression** (`outils/banc.py`) enregistre ce que le moteur décide sur
384 offres fictives — filtre d'intitulé, fit, fit_fin, domaine, tri, zone, pays, contrat,
langue, message, et le texte de lettres. Il doit rester à **0 écart** à chaque commit. Si
un changement de comportement est voulu, régénérer la référence (`banc.py enregistrer …`)
**dans le même commit**, et dire pourquoi dans le message.

**Les tests vivent dans `tests/`**, en pytest (les 27 anciennes suites de `Scripts/` y ont
été converties le 2026-10-18, cas pour cas). `tests/conftest.py` fixe le profil d'exemple
AVANT tout import du moteur et fournit les fixtures : `faux_reseau` (doublure de
`_get_borne`/`_post_borne`), `horloge` (temps et pauses simulés), `file_temporaire` et
`suivi_temporaire` (file et suivi jetables), `navigateur`/`page` (un Chromium headless par
session, une page neuve par test). **Jamais d'affectation directe d'une globale du moteur
dans un test : `monkeypatch`**, sinon l'état fuit d'un test à l'autre. Un test qui lit les
données réelles d'un utilisateur porte la marque `donnees_reelles` et ne tourne qu'à la
demande (`pytest -m donnees_reelles`). `tests/test_pas_de_suite_historique.py` refuse tout
nouveau `Scripts/test_*.py`. `Scripts/test_live_nav.py` et `Scripts/test_acces_sites.py`
sortent vraiment sur le web — hors pytest, ne pas les lancer machinalement.

`test_scoring` génère un cas « sans backspace » **par motif du module** : ajouter un
motif à `ats_match` fait monter son compte sans qu'aucun test ait été écrit.

## Architecture

### Le paquet `src/jobhunter` (phase 3 du plan, en cours)

Le moteur migre de `Scripts/` vers `src/jobhunter`, une couche à la fois
(`docs/plan-professionnalisation.md`). Fait :

| Paquet | Contenu (ancien nom) |
|---|---|
| `jobhunter.stockage` | `atomique`, `verrou`, `file` (`queue_io`), `suivi` (`suivi_io`) |
| `jobhunter.scoring` | `fit` (`ats_match`), `langue`, `zones`, `tri` (`tri_file`), `lexique`, `domaines` |
| `jobhunter.sources` | `job_sources` : une source par module, `commun`, `fusion`, `cli` — affectation routée au propriétaire |
| `jobhunter` | `racine`, `profil`, `reseau` (requêtes bornées), `chemins`, `texte` |

Dépendances à sens unique, vérifiées en test : le stockage et le scoring se chargent sans
`Scripts/` ni `tailor_application` (les cycles `jutil`↔`queue_io` et `ats_match`↔`tailor`
ont disparu). Imports différés restants, assumés, vers `doublons`/`rejets_tri`/`exclusions`/`wtj_desc`.
**Façades** : chaque ancien `Scripts/x.py` déplacé est un ALIAS (`sys.modules`) du module
du paquet — `import ats_match` *est* `jobhunter.scoring.fit`, un `monkeypatch` touche le
vrai code ; lancé directement, il exécute le module (`runpy`). `test_coherence_imports.py`
vérifie que chaque `module.nom` utilisé entre modules existe.

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

Développement : **uv** (`uv sync` crée `.venv` depuis `pyproject.toml` et `uv.lock`),
**ruff** (lint et format, règles et exceptions dans `pyproject.toml`), **pre-commit**
(`uv run pre-commit install`, une fois). Détail : `CONTRIBUTING.md`. Feuille de route :
`docs/plan-professionnalisation.md`.

Utilisateur final : `installer.bat` / `installer.sh` installent `requirements.txt` (mêmes
bornes que `pyproject.toml`) dans le Python du système. `VERSION` et la version de
`pyproject.toml` doivent rester égales (`outils/verifie_version.py`, en CI).
