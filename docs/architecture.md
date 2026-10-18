# Architecture de JobHunter

Ce document décrit l'état au 18 octobre 2026 (version 1.12). Les choix structurants ont
chacun leur ADR dans [`docs/adr/`](adr/) ; le plan qui a mené ici est
[`plan-professionnalisation.md`](plan-professionnalisation.md).

## Vue d'ensemble

```
                 profil/profil.json  (identité, métiers, mots-clés, scoring, textes)
                          │  lu par jobhunter.profil
                          ▼
  ┌────────────── collecte ──────────────┐     ┌──────── tri et note ────────┐
  │ jobhunter.sources                    │     │ jobhunter.scoring           │
  │  ats · workday · linkedin · wtj · efc│     │  fit (note 1-10, fit_fin)   │
  │  eures · indeed · apec · glassdoor   │ ──▶ │  langue · zones · domaines  │
  │  vie · fir · talent · francetravail  │     │  tri (sort ce qui ne colle  │
  │  agregateurs                         │     │  pas au profil)             │
  │  fusion ── dédoublonne, note, écrit ─┼──┐  └─────────────────────────────┘
  └──────────────────────────────────────┘  │
                                            ▼
                         Scripts/apply_queue.json  ◀── jobhunter.stockage.file
                         Scripts/descriptions.json      (verrou, écriture atomique,
                         Scripts/suivi.json        ◀──   descriptions à part)
                                            │          jobhunter.stockage.suivi
             ┌──────────────────────────────┼───────────────────────────┐
             ▼                              ▼                           ▼
  ┌── documents ──────────┐   ┌── application ─────────┐   ┌── navigation ──────────┐
  │ jobhunter.documents   │   │ jobhunter.app          │   │ jobhunter.navigation   │
  │  cv · lettre · message│   │  fenetre.App = mixins  │   │  page · carrieres      │
  │  cv_auto · llm · rendu│   │  tableau · fiche ·     │   │  formulaires · segment │
  │  (.docx puis .pdf)    │   │  actions · panneaux…   │   │  compte · linkedin…    │
  └───────────────────────┘   └────────────────────────┘   └────────────────────────┘
                                                              remplit, SURLIGNE l'envoi :
                                                              le clic final est humain
```

## Les paquets

| Paquet | Rôle | Dépend de |
|---|---|---|
| `jobhunter.racine` | racine de l'installation (marqueur `Scripts/` + `profil/`, ou `JOBHUNTER_RACINE`) | — |
| `jobhunter.profil` | lecture du profil, motifs compilés depuis ses listes ; `utiliser()` injecte un profil | racine, paresseux |
| `jobhunter.paresseux` | valeurs de module calculées à la première lecture ([ADR 0007](adr/0007-valeurs-du-profil-paresseuses.md)) | — |
| `jobhunter.journal` | `logging` du moteur : console à l'identique, fichier horodaté par exécution | — |
| `jobhunter.reseau` | requêtes HTTP bornées en durée totale, client partagé, compteur des refus `INCIDENTS` | — |
| `jobhunter.texte`, `liens` | normalisation de texte, chemins ↔ `file:///` | — |
| `jobhunter.stockage` | file, descriptions, suivi : verrou, atomicité | racine |
| `jobhunter.scoring` | note, langue, zones, domaine, tri | profil, texte, chemins |
| `jobhunter.sources` | collecte par source, fusion dans la file | reseau, scoring, stockage |
| `jobhunter.documents` | CV, lettre, message court, PDF | profil, scoring.lexique, chemins |
| `jobhunter.navigation` | Playwright : du site de la société au formulaire rempli | racine |
| `jobhunter.app` | l'application bureau (customtkinter) | tout ce qui précède |
| `jobhunter.cli` | `python -m jobhunter <commande>` | racine |

Les dépendances vont dans un seul sens (de haut en bas du tableau). Quelques imports
différés vers `Scripts/` restent, marqués `TRANSITION` dans le code : `doublons`,
`rejets_tri`, `exclusions`, `wtj_desc`, `enrich_homepages`, `relances`, `mise_a_jour`.

## Les données

Trois fichiers JSON dans `Scripts/`, trois contrats d'accès
([ADR 0002](adr/0002-trois-fichiers-trois-contrats.md)) :

- **`apply_queue.json`** — les offres. Identité : `oid = "entreprise|poste"`, jamais
  l'URL. Écriture uniquement par `stockage.file.transaction()`.
- **`descriptions.json`** — le texte des annonces, à part : il pesait 64 % de la file.
  Réinjecté à la lecture, ressorti à l'écriture, de façon transparente.
- **`suivi.json`** — les candidatures. La donnée la moins reconstituable : seul fichier
  versionné, écrit entrée par entrée (`stockage.suivi.poser`) sur l'état relu sous verrou.

Un programme qui trouve la file verrouillée sort en **code 3** sans rien modifier
([ADR 0003](adr/0003-verrou-fichier-code-3.md)).

## Le pipeline quotidien

`Scripts/pipeline_quotidien.py` (ou `python -m jobhunter pipeline`), lancé chaque matin
par la tâche que pose `planifier.bat` :

1. **collecte**, en cinq passes fusionnées chacune (ATS/Workday/V.I.E ; LinkedIn ;
   eFC/EURES ; APEC/France Travail/Adzuna/Jooble ; Glassdoor/WTJ) — une passe qui dépasse
   son temps ne perd que la sienne ;
2. **fiches détaillées** des V.I.E, **descriptions** LinkedIn et sites carrière ;
3. **tri** : séniorité, expérience exigée, métier — les candidatures sont épargnées ;
4. **disponibilité** : offres fermées retirées (API publique, 404/410) ;
5. **documents** : CV et lettre pour le haut de la file.

Une sauvegarde de la file, des descriptions et des scans est faite avant toute étape
(`Scripts/_sauvegardes/<date>/`, sept jours glissants).

Journaux : `Scripts/_logs/pipeline_<date>_<heure>.log` garde la console de chaque étape ;
`…_moteur.log` à côté garde les messages du moteur avec heure, niveau et module
(`jobhunter.journal`, variable `JOBHUNTER_JOURNAL`). Dans le moteur, `print` est réservé
à la sortie des commandes (`main()`) ; le reste passe par `logging`.

## Réseau : ce qui est permis

Pages et API **publiques** seulement. Une limite de débit (429) s'attend et la passe
reprend où elle s'était arrêtée ; un refus (403, 999, CAPTCHA) arrête la source, sans
nouvelle tentative avant 30 jours ([ADR 0004](adr/0004-429-attendre-403-arreter.md)).
Aucun contournement anti-bot, aucun moteur furtif, aucun mot de passe manipulé, aucune
soumission automatique ([ADR 0005](adr/0005-aucune-soumission-automatique.md)).

## Code hérité : les façades

Chaque ancien `Scripts/x.py` déplacé dans le paquet est un **alias** du module
(`sys.modules`), pas une copie ; un paquet découpé (`sources`, `documents`,
`navigation`, `app`) voit les noms de tous ses sous-modules, et une affectation va au
module qui possède le nom ([ADR 0001](adr/0001-facades-alias.md)). Les façades
disparaîtront avec l'installation par `pip` (phase 6 du plan).

## Vérifier qu'un changement ne change rien

- `outils/banc.py comparer outils/banc_reference.json` : 384 offres fictives, chaque
  décision (titre gardé, note, domaine, tri, zone, pays, contrat, langue, message, lettre
  et CV) comparée à la référence. 0 écart attendu ([ADR 0006](adr/0006-banc-de-non-regression.md)).
- `pytest` : ~1 450 tests sans réseau ; `mypy` : strict sur le socle.
