<div align="center">

# JobHunter

**Ta recherche d'emploi, préparée chaque matin — et le clic final reste le tien.**

JobHunter collecte les offres de 11 sites d'emploi et de plus de 20 types de sites carrière
d'entreprises, les note de 1 à 10 selon **ton** profil, et prépare pour chacune un CV adapté,
une lettre de motivation et un court message. Il tourne sur ton ordinateur. Il n'envoie
jamais de candidature.

[![tests](https://github.com/Grisbix/JobHunter/actions/workflows/tests.yml/badge.svg)](https://github.com/Grisbix/JobHunter/actions/workflows/tests.yml)
[![version](https://img.shields.io/github/v/release/Grisbix/JobHunter)](https://github.com/Grisbix/JobHunter/releases/latest)
![python](https://img.shields.io/badge/python-3.12%20%7C%203.14-3776ab)
![plateformes](https://img.shields.io/badge/Windows%20%C2%B7%20macOS%20%C2%B7%20Linux-bureau-334155)
[![licence](https://img.shields.io/badge/licence-MIT-blue)](LICENSE)

[🇬🇧 English](README.md) · 🇫🇷 Français

<a href="https://github.com/Grisbix/JobHunter/releases/latest/download/JobHunterSetup.exe"><img alt="Télécharger l'installateur pour Windows" src="https://img.shields.io/badge/T%C3%A9l%C3%A9charger-JobHunterSetup.exe-2563eb?style=for-the-badge&logo=windows&logoColor=white"></a>
&nbsp;
<a href="#depuis-le-code-source-windows"><img alt="Code source" src="https://img.shields.io/badge/Code%20source-personnaliser-334155?style=for-the-badge&logo=github&logoColor=white"></a>

<sub>Windows 10/11 · sans Python ni droits d'administrateur · interface en français, anglais, allemand ou espagnol · tes données restent dans <code>Documents\JobHunter</code></sub>

</div>

| Les offres, triées pour ton profil | La lettre préparée pour une offre |
|---|---|
| ![Liste des offres](docs/screenshots/offers.png) | ![Lettre générée](docs/screenshots/letter.png) |

<sub>Captures faites avec un profil et des offres **fictifs** (Léa Martin, chargée de communication à Lyon) : le profil créé par le premier lancement, avant tout complément par Claude. L'application parle aussi **anglais, allemand et espagnol** : Maintenance → « Langue / Language… ».</sub>

- [Pourquoi](#pourquoi-jobhunter) · [Comment ça marche](#comment-ça-marche) · [Sources](#sources)
- [Installer (Windows)](#installer-windows) · [Depuis le code source](#depuis-le-code-source-windows) · [macOS / Linux](#macos--linux)
- [Paramétrer ton profil avec Claude](#paramétrer-ton-profil-avec-claude-code)
- [Au quotidien](#au-quotidien)
- [Le profil](#le-profil)
- [Pour aller plus loin](#pour-aller-plus-loin)
- [Règles du projet](#règles-du-projet) · [Fiabilité](#fait-pour-quon-puisse-sy-fier)
- [Dépannage](#dépannage)

## Pourquoi JobHunter

La plupart des outils de recherche d'emploi sont soit des **aspirateurs** (une pile d'offres,
sans tri, rien de préparé), soit des **robots de candidature** (des centaines de candidatures
identiques envoyées en ton nom, des comptes bloqués, des recruteurs agacés). JobHunter est
entre les deux :

| | Aspirateurs | Robots de candidature | **JobHunter** |
|---|:---:|:---:|:---:|
| Collecte sur les sites d'emploi *et* les sites carrière | parfois | parfois | ✅ |
| Classe les offres selon **ton** profil, et dit pourquoi | — | rarement | ✅ |
| CV et lettre adaptés à chaque offre, à partir de tes faits | — | génériques | ✅ |
| Remplit le formulaire, joint les documents | — | ✅ | ✅ |
| Clique « Envoyer » à ta place | — | ✅ | **jamais, par principe** |
| Contourne CAPTCHA et protections anti-robots | souvent | souvent | **jamais** |
| Ton CV et tes candidatures restent sur ta machine | variable | dans le cloud | ✅ |

## Comment ça marche

```mermaid
flowchart LR
    A[Collecter<br/>11 sites + sites carrière] --> B[Noter<br/>1–10 pour toi]
    B --> C[Préparer<br/>CV + lettre]
    C --> D{{Tu relis<br/>et cliques Envoyer}}
    D --> E[Suivre<br/>confirmée · relances]
```

1. **Collecter.** Chaque matin (ou d'un clic), les offres arrivent des sites ci-dessous et des
   pages carrière des entreprises que tu suis. Un site qui limite le débit est attendu puis
   repris ; un site qui refuse est laissé tranquille 30 jours.
2. **Noter.** Chaque offre reçoit une note de 1 à 10 calculée sur ton profil : métiers visés,
   compétences et mots qu'emploient les offres, expérience, langues, lieux. Clique une offre
   pour voir *pourquoi* elle a cette note.
3. **Préparer.** Pour les meilleures offres : un CV tiré de ton propre `.docx` avec l'intitulé
   exact du poste, une lettre construite uniquement à partir des faits que tu as donnés, et un
   court message pour les formulaires. Un contrôle signale ce qui manque avant d'envoyer.
4. **Postuler, toi-même.** JobHunter ouvre le formulaire, le remplit, joint les documents et
   surligne le bouton Envoyer. Tu relis, tu cliques. Le suivi note ensuite si le site a
   **confirmé** la candidature ou si elle est seulement **déclarée** — avec le texte vu et une
   capture.
5. **Relancer.** Brouillons de relance à 7 jours, statuts proposés à partir des courriels des
   recruteurs (lecture seule, chacun validé par toi), chiffres de la semaine.

## Sources

| Sites d'emploi | Sites carrière des entreprises |
|---|---|
| LinkedIn (pages publiques, sans connexion) · Welcome to the Jungle · APEC · Glassdoor · eFinancialCareers (9 pays) · EURES (UE) · V.I.E (Business France) · FIR · **API officielles** : France Travail, Adzuna, Jooble | Greenhouse · Lever · Ashby · Workday · SmartRecruiters · Recruitee · Teamtailor · Workable · iCIMS · SuccessFactors · Oracle · Phenom · Eightfold · Avature · Cornerstone · Talentsoft · Pinpoint · et d'autres |

Ajoute une entreprise depuis l'application (**Entreprises** → colle le lien de sa page carrière) :
JobHunter reconnaît la plateforme et la suit. Chaque source affiche son dernier résultat dans
**Accès** : offres trouvées, débit limité ou refus — une journée vide n'est jamais confondue
avec une journée calme.

---

## Installer (Windows)

1. **Télécharge [`JobHunterSetup.exe`](https://github.com/Grisbix/JobHunter/releases/latest/download/JobHunterSetup.exe)**
   et lance-le. Pas de Python à installer, pas de droits d'administrateur : JobHunter
   s'installe pour toi seul et ajoute un raccourci au menu Démarrer.
2. **Au premier lancement**, choisis ton CV (`.docx` de préférence) : JobHunter le lit et
   pose cinq questions (métiers visés, expérience, villes, accords, secteur).
3. **Clique sur « Actualiser les offres »** : la collecte, la note et les documents se font
   depuis l'application.

Tes données (profil, CV, lettres, offres, suivi) vivent dans `Documents\JobHunter` : la
mise à jour et la désinstallation n'y touchent jamais. Pour mettre à jour, l'application te
propose la nouvelle version au démarrage ; télécharge et lance le nouvel installateur.

Conseillés : [LibreOffice](https://www.libreoffice.org/download/) (CV et lettres en PDF) et
Google Chrome (candidature semi-automatique ; à défaut, la collecte utilise Edge, présent sur
tout Windows).

## Depuis le code source (Windows)

Pour personnaliser JobHunter ou le développer : le code complet, avec Python.

**Les outils**

| Outil | | À quoi il sert |
|---|---|---|
| [Python 3.12+](https://www.python.org/downloads/) | **obligatoire** | fait tourner JobHunter — `launchers\install.bat` propose de l'installer s'il manque |
| [LibreOffice](https://www.libreoffice.org/download/) | conseillé | CV et lettres en PDF (sinon `.docx`) |
| [Claude Code](https://claude.com/claude-code) | conseillé | paramètre tout ton profil depuis ton CV |
| [Git](https://git-scm.com/downloads) | facultatif | récupérer les mises à jour (`git pull`) |
| [Ollama](https://ollama.com/) | facultatif | lettres rédigées par une IA locale et gratuite |

**Les 4 étapes**

1. **Télécharge** la [dernière version](https://github.com/Grisbix/JobHunter/releases/latest) (fichier `JobHunter-….zip`) et dézippe-le.
2. **Double-clique sur `launchers\install.bat`** — bibliothèques Python et navigateur Chromium (quelques minutes, une seule fois). Les bibliothèques vont dans un dossier `.venv` à côté de JobHunter, pas dans le Python de l'ordinateur.
   Sans Python, il propose de l'installer pour toi (winget) : accepte, ferme la fenêtre, relance-le.
3. **Dépose ton CV dans `Mon_CV`** — un `.docx` de préférence (voir ci-dessous). Ce dossier n'est jamais publié.
4. **Double-clique sur `launchers\start.bat`** — la première fois, il crée ton profil en lisant ton CV et en
   posant cinq questions (métiers visés, expérience, villes, accords, secteur) ; ensuite il ouvre
   directement l'application. (Tu peux aussi ouvrir `JobHunter.pyw` : sans profil, il te propose
   de choisir ton CV.)

**Ensuite, deux outils en un double-clic :**

- **`launchers\schedule.bat`** — lance la collecte chaque matin à 8 h (`launchers\schedule.bat 07:30` pour une autre
  heure, `launchers\schedule.bat supprimer` pour l'arrêter). Journaux dans `Scripts\_logs\`.
- **`launchers\update.bat`** — récupère la dernière version (l'application te la propose aussi
  d'elle-même au démarrage, et se relance après). Elle affiche les nouveautés, installe, vérifie
  que tout se charge et **revient seule à la version d'avant** si ce n'est pas le cas. Ton
  profil, ton CV, tes lettres et ton suivi ne sont **jamais** touchés ; un fichier du programme
  que tu as modifié est gardé, la nouvelle version posée à côté en `.nouveau`. Les anciennes
  versions vont dans `_sauvegarde_maj\` ; `launchers\update.bat --annuler` y revient.
  L'application te prévient elle-même au démarrage quand une nouvelle version sort.

**Ce qu'il y a dans le dossier** : `launchers/` les outils en double-clic (`.bat` Windows,
`.sh` macOS/Linux) · `Mon_CV/` ton CV · `profil/` tes réglages · `Scripts/` les offres, le
suivi de tes candidatures et les journaux · `CV/`, `Lettres/` les documents faits pour chaque
offre · `src/` le programme · `docs/`, `tests/`, `tools/` pour les développeurs.

> **Pourquoi un `.docx` ?** Chaque CV envoyé part de ce modèle. Écris `[nom du poste]` dans ton
> accroche : l'intitulé exact de l'offre s'y insère. Un PDF est envoyé tel quel, sans adaptation.

### macOS / Linux

Mêmes étapes, avec les scripts `.sh` de `launchers/` dans un terminal ouvert dans le dossier de JobHunter (Python 3.12+ et, sous Linux, `python3-tk` à installer d'abord) :

```bash
./launchers/install.sh
./launchers/start.sh          # crée le profil depuis Mon_CV, puis ouvre l'application
./launchers/schedule.sh        # collecte chaque matin (cron)
./launchers/update.sh
```

> À chaque changement, la CI lance `launchers/install.sh` sur un Mac, puis tous les tests, dont l'ouverture de chaque panneau de l'application dans chaque langue. Personne ne l'a encore utilisée sur son propre Mac : signale tout souci.

<details>
<summary>Installation manuelle (sans les scripts)</summary>

```bash
pip install -r requirements.txt
python -m playwright install chromium
python JobHunter.pyw profile "chemin/vers/mon_CV.docx"
python JobHunter.pyw
```
</details>

## Paramétrer ton profil avec Claude Code

Le premier lancement crée un profil **qui marche**, mais sommaire. Pour un profil complet,
ouvre [Claude Code](https://claude.com/claude-code) dans le dossier JobHunter et tape :

```
/configure-profile Mon_CV\mon_CV.docx
```

Claude lit ton CV, te pose ses questions en un seul message, puis remplit tout : variantes
d'intitulés de ton métier, compétences et leurs synonymes dans les annonces, notation des
offres, filtres, recherches lancées sur les sites, paragraphes de lettre. Il vérifie que les
offres de ton métier passent et que les autres sont écartées, puis te dit ce qui reste à
compléter. **Il n'invente aucun fait** : ce qui n'est pas dans ton CV, il te le demande.

## Au quotidien

| Quoi | Comment |
|---|---|
| Ouvrir l'application | `launchers\start.bat` (ou `python JobHunter.pyw`) |
| Collecte + tri + CV/lettres des meilleures offres (1 à 3 h) | `python JobHunter.pyw pipeline` |
| Collecte LinkedIn seule / essai sans rien écrire | `python JobHunter.pyw collect --linkedin [--dry]` |
| CV + lettre des 20 meilleures offres | `python JobHunter.pyw documents --top 20` |
| Refaire CV et lettre d'une offre | `python JobHunter.pyw documents --url <morceau-du-lien>` |
| Remplissage semi-automatique d'un formulaire | dans l'application : coche des offres, « Postuler la sélection » (panneau Candidatures) ; ou `python JobHunter.pyw apply --canal linkedin` dans un terminal |

Les mêmes programmes ont une entrée unique : `python -m jobhunter` liste les commandes
(`collecte`, `documents`, `postuler`, `pipeline`, `maj`…), avec `src` dans `PYTHONPATH` ;
`python -m jobhunter documents --top 20` équivaut à la ligne du tableau.

**Chaque matin automatiquement** : `launchers\schedule.bat` (voir plus haut).
**Mettre à jour** : `launchers\update.bat` (ou le bouton « Mettre à jour JobHunter » de l'app) ;
`python JobHunter.pyw update --verifier` pour seulement voir ce qu'apporte la nouvelle version,
`--annuler` pour revenir à la précédente. Nouveautés de chaque version : [`CHANGELOG.md`](CHANGELOG.md).

## Le profil

Tout ce qui te concerne vit dans **`profil/profil.json`**. Le moteur ne connaît aucun métier :
pour changer de cible, on change le profil. Modèle complet : `profil/exemple_finance_esg.json`
(un junior en finance durable).

| Rubrique | Contenu |
|---|---|
| `identite` | nom, email, téléphone, ville, `genre` (m/f pour les accords) |
| `langues_parlees` | `["fr", "en", …]` — une annonce rédigée dans une autre langue est notée 2 au plus, une qui en exige une, 4 |
| `domaines` | un par métier visé : intitulés, CV à utiliser, **paragraphe de parcours** de la lettre |
| `competences` | tes compétences et les mots des annonces qui les désignent |
| `scoring` | comment une offre est notée : cœur du métier, plafonds, intitulés hors cible |
| `niveau` | junior, confirmé ou senior : malus d'expérience |
| `filtre_titre` | mots requis dans un intitulé pour le collecter, mots qui l'écartent |
| `tri` | familles de métiers retirées de la file |
| `zones` | secteurs prioritaires et secondaires (`idf`, `lyon`, `nantes`…) |
| `collecte.mots_cles` | recherches lancées sur LinkedIn, WTJ… |
| `message`, `lettre` | diplôme, langues, phrases de profil, faits par compétence |

Contrôler le profil, sans réseau :

```bash
python JobHunter.pyw show-profile                                              # il se lit ?
python JobHunter.pyw check-profile "Chargé de communication" "Développeur Java"
```

Le second dit, pour chaque intitulé, s'il est collecté ou écarté, son domaine et sa note.

## Pour aller plus loin

- **Ligne de CV propre à une offre** : `CV/Faits.json` (format dans `profil/exemple_Faits.json`,
  utilisée seulement si `"valide": true`).
- **Lettre écrite à la main** : `Lettres/Sur_mesure/<entreprise>__<poste>.txt` remplace le
  corps de la lettre générée.
- **Entreprises suivies directement** : `Scripts/sources_config.json` ;
  `python JobHunter.pyw probe_ats` trouve le flux carrière d'une entreprise.
- **France Travail, Adzuna, Jooble** : crée toi-même une clé d'API gratuite, puis
  panneau Accès → « Saisir la clé ». Elle va dans `Scripts/francetravail.json`,
  `adzuna.json` ou `jooble.json`, sur ton PC seulement. Sans clé, source ignorée.
- **Lettres par IA locale** : installe [Ollama](https://ollama.com/), puis `ollama pull llama3.1:8b`.

## Règles du projet

- **Aucun envoi automatique.** Le clic final est toujours le tien.
- **Aucun contournement anti-bot.** Navigateur standard, qui se déclare automatisé. Un site qui
  refuse (403, CAPTCHA) est laissé tranquille 30 jours.
- **Aucun mot de passe** lu, stocké ni tapé par les programmes ; aucune création de compte
  automatique. Les connexions aux sites carrière se font à la main.
- **Jamais ton profil Chrome personnel** : JobHunter utilise un profil dédié.
- **Tes données restent chez toi** : profil, CV, lettres, offres et suivi sont ignorés par git.

## Fait pour qu'on puisse s'y fier

Un outil qui écrit en ton nom doit être juste. Ce qui le garantit :

- **~2 300 tests sans réseau** sur un profil fictif, sous Windows (Python 3.12 et 3.14) et
  Linux, à chaque modification.
- **Un banc de non-régression** : chaque modification rejoue la note de 384 offres fictives —
  et, avant chaque version, des 12 000+ offres réelles de son auteur — et doit montrer
  **0 écart**, sauf changement voulu ([ADR 0006](docs/adr/0006-non-regression-bench.md)).
- **Des tests sur cas générés** (Hypothesis) : nettoyage des titres, détection des doublons,
  bornes de la note et fusions vérifiés sur des milliers d'entrées générées — ils ont trouvé
  deux vrais bugs dès leur premier passage.
- **Chaque panne réseau testée** : chaque lecteur de site carrière face aux refus, limites de
  débit, erreurs serveur, délais et réponses illisibles — toujours signalée, jamais un « rien
  de nouveau » silencieux.
- **Chaque panneau ouvert sans console**, puis avec des fichiers de données abîmés.
- **Des données protégées** : un seul chemin d'écriture par fichier, sous verrou, atomique ;
  sauvegarde quotidienne, et tout nettoyage s'annule. Tes candidatures ne sont jamais
  supprimées par une purge automatique.
- **Signature des mises à jour** vérifiée avant installation (intégrée,
  [ADR 0012](docs/adr/0012-signed-updates.md) ; active dès que la clé publique de l'auteur est
  livrée), analyse CodeQL, actions de CI figées par empreinte, et
  [décisions d'architecture](docs/adr/) écrites avec leur raison.

## Dépannage

| Symptôme | Cause probable |
|---|---|
| « Python est introuvable » | Python non installé, ou « Add Python to PATH » non coché : réinstaller |
| « Profil introuvable » | lancer `launchers\start.bat`, ou `/configure-profile` dans Claude Code |
| Aucune offre ne passe | `filtre_titre.metier` trop étroit, ou `collecte.mots_cles` trop rares |
| Trop d'offres hors sujet | compléter `filtre_titre.exclus`, resserrer `filtre_titre.metier` |
| Lettre sans paragraphe de parcours | `domaines[].parcours_fr` vide |
| CV non adapté à l'offre | CV fourni en PDF : fournir un `.docx` |
| L'application ne s'ouvre pas | lancer `python JobHunter.pyw` dans un terminal pour lire l'erreur |
| « 429 » pendant la collecte | limite de débit d'un site : la collecte attend et reprend seule |
| « 403 » ou « challenge » | refus du site : il est ignoré, c'est voulu |

---

**Licence** : [MIT](LICENSE).

**Contribuer** : idées et bugs bienvenus dans les [issues](https://github.com/Grisbix/JobHunter/issues). Pour le code :
[`CONTRIBUTING.md`](.github/CONTRIBUTING.md), puis [`AGENTS.md`](AGENTS.md) (architecture,
conventions) et [`docs/`](docs/README.md) (programmes, pièges appris à la dure, feuille de
route) ; `python -m pytest -q` lance toute la suite sans réseau. Commentaires et docs sont en
anglais ; les noms de fonctions et les clés du profil restent en français, pour que les
profils existants continuent de marcher.
