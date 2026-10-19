# Contribuer à JobHunter

> **In English.** The code, comments and commit messages are in French; issues and pull
> requests in English are welcome. Set up with `uv sync`, then before each commit run
> `uv run pytest -q` (about 1,850 offline tests), `uv run mypy` and
> `uv run python outils/banc.py comparer outils/banc_reference.json` (0 difference expected).
> Architecture and conventions: [`AGENTS.md`](AGENTS.md) and [`docs/adr/`](docs/adr/). The
> Windows installer is built by `outils/installateur/construire.py` (see ADR 0011). Rules
> that are not up for debate: nothing is ever sent automatically, no anti-bot circumvention,
> no password handled by the programs.

## Installer l'environnement de développement

```bash
uv sync                                           # .venv + dépendances verrouillées (uv.lock)
uv run python -m playwright install chromium      # navigateur des tests de navigation
uv run pre-commit install                         # contrôles avant chaque commit
```

Python 3.12 ou plus récent. Sans uv : `python -m venv .venv`, puis
`pip install -r requirements.txt ruff pytest pre-commit`.

## Avant chaque commit

```bash
uv run pytest -q                                                   # ~1 850 tests, sans réseau
uv run python outils/banc.py comparer outils/banc_reference.json   # 0 écart attendu
uv run mypy                                                        # types ; strict hors programmes
```

pre-commit lance ruff (lint et format), vérifie YAML/TOML, les gros fichiers, les clés
privées et la cohérence `VERSION` / `pyproject.toml`. La CI GitHub refait tout, sous Windows
et Linux.

**Types et docstrings.** mypy est strict sur tout le paquet sauf les programmes
(`jobhunter.programmes`), vérifiés en mode normal. Toute fonction publique hors programmes
et fenêtre (`jobhunter.app`) a une docstring au format Google : ruff (`D`) l'exige.

**Une source change sa réponse ?** `tests/test_rejeu_sources.py` rejoue de vraies réponses
enregistrées (`tests/reponses/`). Si un site a changé et que le parseur est adapté,
réenregistrer la source (réseau, à lancer exprès) :
`uv run python outils/rejeu.py enregistrer lever`. APEC, WTJ et les sources à clé n'y sont
pas : refus d'entrée, défi anti-bot ou identifiants.

## Installer le paquet

`uv sync` installe `src/jobhunter` en mode éditable ; `pip install -e .` aussi. La commande
`jobhunter <commande>` existe alors (`jobhunter` seul liste les commandes). Hors du dépôt,
`JOBHUNTER_RACINE` désigne le dossier qui contient `Scripts/` et `profil/` (sinon le paquet
le cherche en remontant depuis le dossier courant). Sans installation : `python JobHunter.pyw
<commande>`.

## Comprendre le code

[`docs/architecture.md`](docs/architecture.md) : paquets, données, pipeline.
[`docs/adr/`](docs/adr/) : les décisions qui ne se rediscutent pas au détour d'une tâche.

## Écrire un test

Dans `tests/`, en pytest, avec les fixtures de `tests/conftest.py` (faux réseau, horloge,
file et suivi jetables, navigateur). Jamais d'affectation directe d'une globale du moteur :
`monkeypatch`. Données fictives et profil d'exemple uniquement. Un test qui a besoin d'un
autre profil le construit et le passe à `profil.utiliser(donnees)`, puis
`profil.recharger()` en fin de test.

## Diagnostiquer une lenteur (py-spy)

Quand une étape dépasse sa durée (collecte, disponibilité, documents), on localise avant
de supposer. [py-spy](https://github.com/benfred/py-spy) lit la pile d'un programme
Python en cours sans l'arrêter ni le modifier. C'est un outil externe, pas une
dépendance du projet :

```powershell
# 1. trouver le PID du programme lent
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*jobhunter*' } | Select ProcessId, CommandLine

# 2. la pile de chaque fil, maintenant
uvx --from py-spy py-spy dump --pid <PID>

# 3. où passe le temps, sur 60 s (fichier SVG à ouvrir dans un navigateur)
uvx --from py-spy py-spy record --pid <PID> --duration 60 -o lenteur.svg
```

**Jamais `--locals`** : il imprime les variables de chaque cadre, donc des offres, des
lettres, des chemins personnels. Sans lui, le rapport ne contient que des noms de
fonctions et de fichiers du paquet ; on peut le joindre à une issue.

Vérifié le 19/10/2026 sur Python 3.14 : un `time.sleep` provoqué dans une fonction
`etape_bloquee` sort en tête du `dump`, avec son fichier et sa ligne.

## Règles

- **Comportement inchangé, sauf intention explicite.** Le banc le prouve. Un changement
  voulu régénère la référence dans le même commit, et le message dit pourquoi.
- **Un sujet par commit**, message clair qui explique le pourquoi.
- **Le moteur ne connaît personne** : tout ce qui est propre à une personne vit dans
  `profil/profil.json` (voir `AGENTS.md`).
- **Rien à l'import** : ni lecture, ni écriture, ni réseau (`tests/test_effets_import.py`).
  Une valeur tirée du profil s'écrit `_PARESSEUX["NOM"] = lambda: ...` et se lit
  `_ici.NOM` dans son module ([ADR 0007](docs/adr/0007-valeurs-du-profil-paresseuses.md)).
- **`print` pour la sortie d'une commande (`main()`), `logging` pour le reste** :
  `_log = journal.journal(__name__)`.
- **Limites non négociables** : aucune soumission automatique de candidature, aucun
  contournement anti-bot ni résolution de CAPTCHA, aucun mot de passe manipulé par les
  programmes. Détail : `AGENTS.md`.
- Les tests tournent sur le **profil d'exemple** et des **offres fictives**, jamais sur des
  données réelles.

## Publier une version

1. Monter `VERSION` **et** `version` dans `pyproject.toml` (identiques).
2. Ajouter la section `## X.Y.Z — date` en tête de `CHANGELOG.md`.
3. CI verte sur `main`, puis `gh release create vX.Y.Z` avec la section du CHANGELOG :
   l'étiquette sert de référence à la mise à jour des installations par ZIP.
