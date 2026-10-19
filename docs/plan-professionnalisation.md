# Plan : amener JobHunter au niveau professionnel

Rédigé le 2026-10-17. Le fond est solide (bugs mesurés et documentés, tests hors réseau,
verrous, écritures atomiques, règles de sécurité tenues). Ce plan traite la **forme** :
structure, outillage, testabilité, typage, distribution.

## État mesuré au départ (v1.3.2)

| Mesure | Valeur |
|---|---|
| Programmes / tests | 70 / 29 fichiers — 28 400 / 4 800 lignes |
| Fichiers > 800 lignes | `job_sources` 3 921 (90 fonctions), `web_nav` 3 380, `JobHunter.pyw` 3 281 (une classe `App` de 191 méthodes), `tailor_application` 1 294, `scrape_jobs` 1 026, `site_strategies` 810 |
| Modules les plus importés | `queue_io` ← 29, `job_sources` ← 21 (sert aussi de boîte à outils : `title_ok`, `_norm`…), `profil` ← 13, `jutil` ← 12 |
| Cycles d'import directs | `ats_match`↔`tailor_application`, `job_sources`↔`scrape_jobs`, `jutil`↔`queue_io`, `message_offre`↔`tailor_application` |
| Effets de bord à l'import | 91 appels au niveau module (profil lu, motifs compilés depuis le profil…) |
| `sys.path.insert` | 57 fichiers |
| Outillage | aucun linter, formateur, typage ; tests maison (✅/❌), pas de pytest ; Python système |

## Principes

1. **Comportement inchangé à chaque étape.** Un banc de non-régression (phase 0) le prouve ;
   aucune phase ne se fusionne sans lui.
2. **Un module à la fois**, une branche et une PR par étape, CI verte. Pas de grande
   réécriture : les pièges documentés reviendraient.
3. **Compatibilité pendant la transition** : les anciens points d'entrée (`Scripts/*.py`,
   `.bat`, tâche planifiée, `synchro_moteur`) restent des façades minces jusqu'à la fin.
4. **Rien n'est ajouté « au cas où »** : chaque abstraction répond à un problème mesuré.

---

## Phase 0 — Filet de sécurité (½ journée)

But : pouvoir prouver qu'une refonte ne change rien.

- `outils/banc.py` : sur une file donnée, calcule et enregistre `fit`, `fit_fin`, décision du
  tri, domaine, zone, pays, et l'empreinte du texte des lettres, CV et messages d'un
  échantillon d'offres. Mode `--comparer` : rapporte tout écart. (Reprend le banc de la
  migration du 15/10 : 11 341 offres, 99 dossiers.)
- Deux jeux : le **profil d'exemple + une file fictive** (versionnés, tournent en CI) et
  les **données réelles** de Recherche_emploi (local seulement, jamais publiées).

Fini quand : `banc --comparer` rend 0 écart sur la version actuelle contre elle-même, en CI.

## Phase 1 — Outillage (1 journée) → v1.4.0

- `pyproject.toml` : métadonnées, dépendances bornées (reprises de `requirements.txt`),
  configuration des outils. `requirements.txt` reste, généré, pour les `.bat`.
- **uv** + fichier de verrouillage ; venv `.venv` pour le développement. L'utilisateur final
  garde `installer.bat` (qui crée le venv au lieu d'installer dans le Python système).
- **ruff** (lint + format). Règles d'abord `E,F,I,UP,B` ; format de tout le code dans **un
  commit dédié**, déclaré dans `.git-blame-ignore-revs`.
- **pre-commit** : ruff, fin de ligne, fichiers > 1 Mo, détection de secrets.
- CI : `ruff check`, `ruff format --check`, banc, suites.

Fini quand : ruff propre, CI verte, banc 0 écart, `installer.bat` testé sur un dossier neuf.

## Phase 2 — Tests sous pytest (1 à 2 jours) → v1.4.x

- Étape immédiate : `tests/test_suites_historiques.py` lance chaque suite actuelle comme un
  test pytest (paramétré) — tout passe sous `pytest` dès le premier jour.
- `conftest.py` : fixtures `profil_exemple`, `file_temporaire`, `suivi_temporaire`,
  `faux_reseau` (remplace les doublures de `_get_borne`), horloge et `sleep` simulés.
- Conversion suite par suite, des plus petites aux plus grosses : chaque `check()` devient
  une fonction ou un cas `parametrize` ; les affectations de globales (`J.KEYWORDS = …`)
  deviennent `monkeypatch`, remis en place après chaque test.
- `pytest-cov` : couverture mesurée, seuil = valeur de départ, qui ne doit plus baisser.

Fini quand : toutes les suites converties, `pytest -q` en < 2 min, couverture publiée en CI.

**Fait le 2026-10-18.** Les 27 suites converties cas pour cas : 1 142 tests (dont 1 qui lit
des données réelles, marqué `donnees_reelles`), un garde-fou contre toute nouvelle suite
dans `Scripts/`. Couverture 31 % du moteur (fichiers de test exclus), seuil 30 en CI.
Trouvé en convertissant : des vérifications qui ne vérifiaient rien (idempotence de
`titre_poste` dans test_titres, un cas `True` en dur dans test_web_nav) et une dizaine de
suites qui modifiaient des globales du moteur (`time.sleep`, `urlopen`, `httpx.Client`,
chemins, clés) pour tout le processus sans les remettre en place, et un test « réseau
mocké » qui interrogeait réellement le web (80 s) et pouvait écrire dans le cache
`homepages.json`. Durée : ~80 s, ~2 min 30 avec la couverture.

## Phase 3 — Paquet et découpage (1 à 2 semaines, par PR) → v2.0.0

Structure cible :

```
src/jobhunter/
  stockage/     verrou.py, atomique.py, file.py (queue_io), suivi.py, descriptions.py
  profil.py     objet Profil (chargé une fois, passé en paramètre)
  reseau.py     client HTTP : bornes de durée, pauses, 429 attendu, 403 = arrêt, incidents
  scoring/      fit.py (ats_match), langue.py, zones.py, tri.py, domaines.py
  sources/      commun.py (title_ok, normalisation, fusion), linkedin.py, ats/<lecteur>.py,
                workday.py, efc.py, eures.py, apec.py, agregateurs.py, sites_carriere.py
  documents/    lettre.py, cv.py, message.py, cv_auto.py, chemins.py, rendu.py (docx/pdf)
  navigation/   web_nav découpé : navigateur.py, formulaires.py, ats_detect.py, strategies/
  candidature/  apply_runner.py, relances.py, suivi.py
  app/          JobHunter découpé en vues : table.py, fiche.py, journal.py, maintenance.py,
                mise_a_jour.py, theme.py
  pipeline.py   pipeline_quotidien
  cli.py        `jobhunter <commande>` : collecte, tri, documents, postuler, pipeline, maj…
```

Ordre (des feuilles vers les dépendants, une PR chacun) :

1. `stockage/` — casse le cycle `jutil`↔`queue_io`.
2. `profil.py` + `reseau.py`.
3. `scoring/` — sort `titre_poste()` et le vocabulaire commun de `tailor_application` pour
   casser `ats_match`↔`tailor_application`.
4. `sources/` — découpe `job_sources` (3 921 lignes) par source ; ses utilitaires partagés
   vont dans `sources/commun.py`, ce qui casse `job_sources`↔`scrape_jobs`.
5. `documents/` — découpe `tailor_application`, casse `message_offre`↔`tailor_application`.
6. `navigation/` — découpe `web_nav` (3 380 lignes) et `site_strategies`.
7. `app/` — la classe `App` (191 méthodes) devient un assemblage de vues.
8. `cli.py` ; les `.bat`/`.sh` appellent `jobhunter …`.
9. Retrait des façades `Scripts/*.py` (dernière PR, après un cycle complet de pipeline réel).
   **Passerelle 1.15.0** : le moteur, les tests et l'application n'importent plus les
   façades ; surtout, `mise_a_jour` contrôle la version installée avec SON propre code
   (`python -m jobhunter maj --controler`). Sans elle, toute installation 1.x refuserait
   la 2.0 : son contrôle importait `queue_io`, `job_sources`… par leur ancien nom. La 1.15
   doit donc précéder la 2.0 ; une installation antérieure qui sauterait directement en
   2.0 serait ramenée à sa version (rien n'est perdu) — passer par la 1.15.

**Avancement** : 1 à 8 faits le 2026-10-18 (v1.5.0 à v1.12.0), banc 0 écart à chaque étape.
`sources/` a gardé les sources en modules plats (`ats.py` réunit les lecteurs d'ATS et les
« autres API », qui s'appelaient l'un l'autre) ; `sites_carriere` reste dans `scrape_jobs`. `documents/` : `commun`, `cv`, `lettre`, `llm`,
`rendu`, `message`, `cv_auto` ; `chemins` est resté `jobhunter.chemins` (partagé avec le scoring). `navigation/` : une section
de `web_nav` par module, sans cycle (vérifié par un test qui charge chacun seul). `app/` : la classe `App` assemble un
mixin par domaine (méthodes copiées telles quelles) ; le premier lancement est `jobhunter.accueil`. `cli` : `python -m jobhunter <commande>` aiguille
vers les programmes ; les `.bat`/`.sh` y passeront avec l'installation (phase 6).

Fini quand : `pip install -e .` puis `jobhunter pipeline` fonctionne ; aucun
`sys.path.insert` ; aucun cycle (vérifié en CI par `import-linter`) ; banc 0 écart à chaque PR.

**Fait (2026-10-18, v1.15.0 puis v2.0.0)** : 3.9 en deux temps. La passerelle 1.15.0
(ci-dessus) a été publiée et testée seule (mise à jour ZIP 1.14 → 1.15). La 2.0.0 déplace
les 57 programmes de `Scripts/` dans `jobhunter.programmes` (`git mv`, historique gardé),
retire les 14 façades ; `Scripts/` ne garde que les données ([ADR 0008](adr/0008-programmes-dans-le-paquet.md)).
`JobHunter.pyw` est le seul `sys.path.insert` (pour lancer sans installation). Fusionnée
après un cycle complet du pipeline réel sur le code précédent.

## Phase 4 — Effets de bord, configuration, journaux (2 à 3 jours, avec la phase 3)

- **Aucune lecture de fichier ni de réseau à l'import** (91 appels aujourd'hui). Les motifs
  dépendant du profil sont compilés par le `Profil`, pas au chargement du module.
- `Profil`, `ClientHttp` et chemins **injectés** en paramètre : les tests construisent ce
  dont ils ont besoin, sans patcher de globales.
- **`logging`** dans tout le moteur (niveaux, format commun, fichier par exécution du
  pipeline) ; `print` réservé à la sortie de la CLI. `INCIDENTS` devient un compteur porté
  par `ClientHttp`.

Fini quand : `python -c "import jobhunter.sources.linkedin"` ne lit aucun fichier.

**Avancement (2026-10-18, v1.13.0)** : l'import n'écrit plus rien (trois dossiers étaient
créés au chargement) et n'ouvre aucune connexion — vérifié par
`tests/test_effets_import.py`, un cliquet.

**Fait (2026-10-18, v1.14.0)** : l'import ne lit plus aucun fichier. Les ~110 valeurs
tirées du profil et de `chemins.json` se calculent à la première lecture
(`jobhunter.paresseux`, [ADR 0007](adr/0007-valeurs-du-profil-paresseuses.md)) ;
`profil.utiliser()` injecte un profil en mémoire, `profil.recharger()` revient au
fichier. `logging` (`jobhunter.journal`) remplace les 80 `print` des fonctions du moteur,
avec la même sortie console et un fichier horodaté par exécution du pipeline.
`INCIDENTS` vit dans `jobhunter.reseau`, à côté du client HTTP. Non fait, à dessein :
passer `ClientHttp` et les chemins en paramètre de chaque fonction — les tests les
remplacent déjà sans globales cachées (`_get_borne`, `CHEMIN`), et le changement
toucherait toutes les signatures pour rien de mesurable.

## Phase 5 — Typage (continu, à partir de la phase 3)

- Annotations sur toutes les fonctions publiques. `Offre` et `Candidature` en `TypedDict`
  (le JSON ne change pas), puis `dataclass` là où c'est utile.
- **mypy** en CI : strict sur `stockage/`, `profil.py`, `reseau.py`, `scoring/` ; non strict
  ailleurs, durci module par module.

Fini quand : mypy strict sur le cœur, aucun `# type: ignore` sans commentaire.

**Avancement (2026-10-18, v1.13.0)** : mypy en CI sur tout le paquet ; strict sur le socle
(`stockage`, `profil`, `reseau`, `racine`, `texte`, `liens`, `types`) et sur tout le
`scoring` (+ `chemins`, `_facade`) : le critère de fin est atteint. Restent, en continu,
les `TypedDict` d'`Offre` et `Candidature`, et le durcissement des autres paquets.

**Avancement (2026-10-19)** : `Offre` et `Candidature` sont des `TypedDict` non totaux
(toutes les clés facultatives : une offre se construit par étapes), inventoriés sur une vraie
file de 12 137 offres et sur les clés que le code lit ou écrit. `cli`, `accueil` et
`mise_a_jour` rejoignent la liste stricte. Mesuré pour la suite, en erreurs du mode strict :
`documents` 187, `navigation` 175, `sources` 395, `app` 1 024, les programmes ~85.
Puis `documents.rendu`, `llm`, `commun`, `cv_auto` et `cv` passent stricts (banc 0 écart) ;
puis `lettre` et `message` : **tout `documents` est strict**, puis **tout `navigation`**
(objets Playwright typés `Any` : `page.evaluate` rend Any de toute façon), puis **tout
`sources`**. Restent `app` (1 024) et les programmes. Leçon : un renommage de variable
que mypy jugeait correct cassait `contrat_de_la_description` (32 écarts au banc, aucun
test) — le banc reste obligatoire même pour du typage.

## Phase 6 — Distribution (1 journée) → v2.x

- JobHunter installable : `pip install git+https://github.com/Grisbix/JobHunter@v2.0.0`.
- Recherche_emploi **dépend** d'une version étiquetée au lieu de recopier le moteur :
  `synchro_moteur.py` est retiré ; le dépôt ne garde que profil, données et scripts perso.
- Une seule source de version (`pyproject.toml`, lue par `mise_a_jour`).
- **Test de passage 1.3.x → 2.0** sur une vraie install ZIP et un vrai clone : la
  restructuration déplace des dizaines de fichiers (la mise à jour retire les anciens
  intacts, garde les modifiés — à vérifier en réel, comme pour la 1.3.0).

**Avancement (2026-10-18, v1.13.0)** : `src/jobhunter` se construit en wheel (vérifié en CI)
et s'installe ; la commande `jobhunter` marche depuis un venv neuf, les programmes encore
dans `Scripts/` via `JOBHUNTER_RACINE`. Restent, et ils dépendent du retrait des façades
(3.9) : Recherche_emploi dépendant d'une version étiquetée au lieu de `synchro_moteur`, et
le test 1.x → 2.0. `VERSION` reste lu par la mise à jour tant que des installations 1.x
existent (la CI vérifie qu'il égale `pyproject.toml`).

**Fait (2026-10-19, v2.0.0 et v2.1.0)** : passage réel 1.15 → 2.0 vérifié sur une
installation ZIP et sur un clone git (`Scripts/` vidé de ses `.py`, VERSION 2.0.0, commandes
et contrôle OK). Recherche_emploi dépend du paquet installé à une version étiquetée
(`pip install "jobhunter @ git+…@v2.1.0"`) ; `synchro_moteur` et les copies du moteur y sont
retirés. Banc sur ses données : 0 écart sur 12 137 offres et 99 lettres/CV (1.14 contre
2.1, même file). Restent, reportés : le test sur un Windows neuf et sur un Mac.

## Phase 7 — Données (optionnel, plus tard)

- SQLite derrière l'interface de `stockage/` (inchangée) : transactions, index, plus de
  verrou fichier ni de réécriture complète. Script de migration JSON → SQLite, export JSON
  conservé. À lancer seulement si le volume ou les accès concurrents le justifient.

## Phase 8 — Documentation (continu)

- Les commentaires-récits deviennent des **ADR** courts (`docs/adr/NNNN-titre.md` :
  contexte, décision, conséquence) ; le code garde une ou deux lignes et le lien.
- `docs/architecture.md` (schéma des paquets et du pipeline), `CONTRIBUTING.md`
  (installer, tester, publier), docstrings au format Google sur l'API publique.

**Avancement (2026-10-18, v1.13.0)** : `docs/architecture.md` et six ADR (façades, données,
verrou, 429/403, aucune soumission, banc). Restent les docstrings Google et le
remplacement progressif des commentaires-récits par des renvois aux ADR.

**Avancement (2026-10-19)** : docstrings au format Google (Args, Returns, Yields, Raises)
sur toute l'API publique du socle — `stockage` (file, suivi, verrou, atomique), `profil`,
`racine`, `reseau`. Ruff les exige désormais sur ces fichiers (règle `D`, convention
google) ; un module rejoint la liste quand il est documenté, comme pour mypy strict.

---

## Calendrier indicatif

| Semaine | Phases | Version |
|---|---|---|
| 1 | 0, 1, 2 (étape immédiate) | 1.4.0 |
| 2 | 2 (conversion), 3.1–3.3, 4 en parallèle | 1.4.x |
| 3–4 | 3.4–3.9, 5 sur le cœur | 2.0.0 |
| 5 | 6, test de passage réel, 8 | 2.0.x |
| plus tard | 7 si besoin | — |

## Risques et parades

| Risque | Parade |
|---|---|
| Régression silencieuse du scoring ou des documents | Banc phase 0, obligatoire à chaque PR |
| Tâche planifiée, `.bat`, app cassés par les déplacements | Façades jusqu'à la fin de la phase 3 ; un pipeline réel complet avant de les retirer |
| Mise à jour 1.3 → 2.0 qui casse l'install d'un utilisateur | Test réel ZIP + git avant publication ; retour arrière automatique déjà en place |
| Recherche_emploi désynchronisé pendant la refonte | Il reste sur la 1.3.x jusqu'à la 2.0 ; correctifs urgents rétroportés |
| Refonte qui s'éternise | Chaque PR livre seule et laisse tout vert ; on peut s'arrêter après n'importe laquelle |
