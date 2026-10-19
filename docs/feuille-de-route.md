# Feuille de route après le plan de professionnalisation

Le plan de professionnalisation (`docs/plan-professionnalisation.md`) est fini. Les
phases 0 à 6 et 8 sont faites, la phase 7 est écartée faute de besoin. Trois axes du
premier document de propositions de Codex (18/10) sont livrés :

- candidature depuis l'app avec preuve d'envoi (2.2) ;
- dossiers contrôlés (2.3) ;
- rendement par source (2.4).

Cette feuille de route croise ce qui reste avec le second document de Codex (19/10,
« Exploration transversale des dépôts », dix pistes d'outillage). Elle classe le tout par
valeur pour la recherche d'emploi et par coût.

Règle inchangée : chaque étape livre seule, banc à 0 écart, et ne s'adopte que sur un
échec reproduit ou un gain mesuré. Pas de dépendance installée « en bloc ».

## Étape A — Faire vivre ce qui vient d'être livré (avant tout nouveau code)

| # | Quoi | Qui | Fini quand |
|---|---|---|---|
| A1 | Essai réel du panneau Candidatures sur une offre ; ajouter au détecteur de confirmation les formules réelles qu'il aurait manquées | Gabriel, puis code | une vraie candidature notée `confirmé`, ou une page non reconnue ajoutée aux motifs et testée |
| A2 | Dimanche 25/10 : premier contrôle de disponibilité hebdomadaire | lecture du bilan | les ~143 offres fermées repérées sont retirées, étape sous 110 min |
| A3 | Après une à deux semaines de journal : `jobhunter rendement` | lecture + décision | chaque source a un verdict stable ; décider (à la main) le sort d'une source refusée à chaque fois |

## Étape B — Des preuves de non-régression qui manquent (Codex 19/10, P1, effort faible)

| # | Quoi | Pourquoi ici | Fini quand |
|---|---|---|---|
| B1 ✅ (v2.4.1) | **Test d'architecture** : le moteur (`jobhunter.*` hors `app`, `accueil`) n'importe ni `tkinter` ni `customtkinter` ni `jobhunter.app` | Le plan dit « vérifié en CI par import-linter », mais rien n'est branché : un test pytest de quelques lignes suffit, sans ArchUnitPython ni import-linter | un import volontaire de Tkinter dans `scoring` fait échouer le test ; le retirer le fait passer |
| B2 ✅ (v2.4.3) | **Réponses enregistrées des connecteurs** (pytest-recording / VCR.py, dépendance de test seule) : APEC (API), LinkedIn guest, sitemap WTJ, Workday, Greenhouse/Lever | Les doublures actuelles (`faux_reseau`) sont écrites à la main : elles ne disent pas si le parseur lit encore la vraie réponse d'aujourd'hui. Une réponse réelle enregistrée, expurgée (cookies, en-têtes), rend le parseur reproductible | dix réponses rejouées sans réseau donnent les mêmes offres ; un échange manquant fait échouer ; aucun cookie ni identifiant dans les fichiers versionnés |
| B3 | **Diagnostic de lenteur** : procédure py-spy (outil externe, pas une dépendance) dans `CONTRIBUTING.md` | Utile la prochaine fois qu'une étape dépasse sa durée (collecte, disponibilité) : localiser au lieu de supposer | la procédure retrouve la fonction d'un blocage provoqué exprès, rapport sans données personnelles (`--locals` désactivé) |

## Étape C — Les deux axes métier restants (Codex 18/10)

| # | Quoi | Pourquoi | Fini quand |
|---|---|---|---|
| C1 ✅ (v2.5.0) | **Classement évalué sur les jugements réels** : constituer le jeu de référence à partir de ce qui existe déjà. Pertinentes : les offres postulées, relancées ou en entretien du suivi. Inutiles : « pas intéressé » et `exclusions.json`. Puis mesurer le classement actuel (précision des N premières). | Aucune mesure aujourd'hui de « les premières offres sont-elles les bonnes ». C'est le préalable à toute variante, sémantique ou autre. | un chiffre de référence reproductible (`jobhunter evaluation`) ; toute modification du scoring est comparée à lui, avec le banc |
| C2 ✅ (v2.6.0) | **Identité d'offre plus robuste** : d'abord une **étude**. Compter sur la vraie file les homonymes (même `entreprise\|poste`, lieu ou référence différents) et les doublons sous deux intitulés. | La clé `entreprise\|poste` est celle de `suivi.json`, la donnée la moins reconstituable. On ne migre rien sans un problème mesuré. | une ADR qui chiffre le problème et tranche : identité secondaire (référence de source) en complément, ou statu quo |

## Étape D — L'application testée comme elle tourne (Codex 19/10, P1, effort moyen)

| # | Quoi | Fini quand |
|---|---|---|
| D1 | **Sondage pywinauto, borné à une demi-journée** : inspecter l'arbre des contrôles de la fenêtre réelle. CustomTkinter dessine ses widgets sur un canvas : ils peuvent être invisibles pour UI Automation. | décision écrite. Si les contrôles sont visibles : un parcours avec un profil fictif (ouvrir, filtrer, fiche, panneau Candidatures avec le faux programme). Sinon : on garde les tests Tk internes et le smoke du panneau, et on le note. |

## Étape E — Distribution au-delà de Gabriel (quand le PC de l'ami et le Mac reviennent)

| # | Quoi | Fini quand |
|---|---|---|
| E1 | Environnement Python dédié créé par `installer.bat` (reporté depuis la phase 1) | une installation neuve sur un Windows vierge lance l'app sans toucher au Python système |
| E2 | Mises à jour **signées** : WinSparkle ou tufup (Codex P2), à choisir sur prototype. Attention : la purge de destination de tufup est incompatible avec un dossier qui contient le profil. | un paquet altéré est refusé ; le profil survit à une mise à jour interrompue |
| E3 | Accessibilité (axe-windows, Accessibility Insights) | les contrôles principaux ont un nom ; la tabulation suit l'ordre visuel |

## Écarté ou différé, avec la raison

| Piste (Codex 19/10) | Décision |
|---|---|
| File durable (litequeue, persist-queue) | Aucune perte de travail observée : chaque étape du pipeline reprend où elle s'était arrêtée (`_audit_dispo.json`, `apply_runner_done.json`, budget de durée). Codex le rappelle lui-même : aucune file ne garantit un effet réseau exécuté une seule fois. À rouvrir sur une perte constatée. |
| DocRefract (comparaison de documents) | Le banc compare déjà le texte de 99 lettres et CV à chaque changement, et `documents.controle` vérifie les fichiers finaux. Gain marginal. |
| sqlite-utils / FTS5 (recherche locale) | La recherche de l'app répond sur 12 000 offres. À rouvrir si elle devient lente. |
| ArchUnitPython | Remplacé par le test B1, plus simple, sans dépendance. |
| Modèle d'annulation de confluence-exporter | Le panneau a « Arrêter », le pipeline des budgets de durée et des reprises. |
| Huey, DurableFlow, spoolctl, outils de distribution en bêta, comparateurs PDF sous GPL/AGPL ou sans Windows | Déjà écartés par Codex, pour les raisons qu'il documente. |

## Étape F — Un produit qu'on télécharge et qu'on comprend (demandée le 2026-10-19)

Décisions de l'utilisateur :
- **application autonome**, sans Python sur la machine ;
- **français et anglais** ;
- **vitrine du dépôt en anglais**, le code gardant ses noms français ;
- **nettoyage complet**, anciennes releases comprises.

| # | Quoi | Fini quand |
|---|---|---|
| F1 ✅ (v2.7.0) | **Faire le tri**, en trois volets (voir le détail sous le tableau) | chaque fichier restant a un rôle écrit ; l'arborescence se lit d'un coup d'œil |
| F2 ✅ (v2.8.0) | **Panneaux de l'app à jour**, un par un (voir le détail sous le tableau) | chaque chiffre affiché est juste et chaque ligne a une action |
| F3 ⛔ écarté | **Source HelloWork** : pages publiques de recherche, sans contournement ; robots.txt et conditions vérifiés d'abord | offres HelloWork dans la file, réponse enregistrée et rejouée (B2), verdict dans `rendement` |
| F4 ✅ (v2.9.0) | **Installateur autonome** `JobHunterSetup.exe` (voir le détail sous le tableau) | sur un Windows sans Python : installation, ouverture, collecte et dossier |
| F5 ✅ (v2.10.0 navigation, panneaux, menus ; v2.13.0 journal et boîtes de dialogue ; la sortie des programmes lancés reste en français) | **Français et anglais** : textes de l'interface dans des catalogues, choix dans les réglages ; vitrine du dépôt en anglais (README, docs utilisateur, notes de version), version française à côté | l'app entière en anglais d'un réglage ; README anglais avec le lien français |

**F1 — faire le tri**
- Retirer des deux dépôts les programmes morts ou en double, les documents périmés,
  `Archive/` et les `.bak`.
- Supprimer les anciennes releases GitHub, sur une liste préparée. La suppression est
  irréversible : elle est lancée par l'utilisateur, en gardant au minimum la 1.15 (la
  passerelle) et les 2.x.
- Ranger l'arborescence.

**F2 — panneaux de l'app à jour, un par un**
- « Mes CV » : variantes du profil, banque de faits, état des dossiers (2.3), CV par
  offre retrouvés depuis l'offre plutôt qu'une liste de 1 983.
- « Entreprises » : les flux réellement collectés (ATS, Workday, autres flux), avec
  rendement et verdict (2.4) ; comptes d'offres justes.
- « Accès » : sources actives seulement, état réel (refus, limite, clé manquante),
  Adzuna et Jooble compris.

**F4 — installateur autonome**
- Application compilée (PyInstaller) et installateur Windows.
- Construits par la CI et attachés à chaque release.
- Deux badges dans le README, comme Ibaraki : « Télécharger l'installeur » et « Code
  source ».
- Chrome et LibreOffice détectés, avec un lien s'ils manquent.
- Mise à jour de l'app installée par la release suivante.

Ordre : **F1 → F2 → F3 → F4 → F5**. On trie d'abord, pour ne pas compiler ni traduire du
code mort. L'installateur se construit sur une base propre. On traduit en dernier, une
fois les textes stabilisés.

## Étape G — Idées de la veille GitHub (19/10)

| # | Quoi | Fini quand |
|---|---|---|
| G1 ✅ (v2.13.0) | **Annuaires d'entreprises** Lever, Ashby, Greenhouse (jobsync, MIT) dans le panneau Entreprises | taper un nom, choisir, suivre ; `outils/annuaires.py --verifier` en reproduit les fichiers |
| G2 ✅ (v2.14.0) | **Relecteur des lettres** : une seconde passe, sans le contexte de la rédaction, qui confronte la lettre au guide de style et aux faits ; l'annonce est une entrée non fiable (injection) | chaque défaut signalé est reproduit par un test ; aucune lettre réécrite sans accord |
| G3 ◐ (v2.15.0 : chaque fit expliqué dans la fiche ; reste à mieux classer, quand il y aura assez de jugements) | **Note d'adéquation justifiée** (C1 bis) : chaque point du fit cite le passage de l'annonce qui le donne | `jobhunter evaluation` fait mieux que l'AUC de 0,46 de la 2.5.0, sur les mêmes jugements |
| G4 | **Statuts depuis Gmail**, lecture seule, propositions validées une à une — seulement si Gabriel le demande | — |

## Ordre proposé

**A** (en continu, surtout de l'observation) → **B1** (une heure) → **B2** → **C1** →
**C2 (étude)** → **D1 (sondage)** → **B3** quand une lenteur se présente → **E** quand
la distribution revient.

Ce qui reste hors d'atteinte, quoi qu'il arrive :
- aucune soumission automatique ;
- aucun contournement anti-bot ;
- aucun mot de passe manipulé.

## Fait

- **B1** (v2.4.1) : `tests/test_architecture.py`.
- **B2** (v2.4.3) : `outils/rejeu.py` enregistre une vraie réponse publique de sept sources
  (Greenhouse, Lever, Ashby, Workday, LinkedIn, EURES, FIR), nettoyée ;
  `tests/test_rejeu_sources.py` la rejoue sans réseau et exige les mêmes offres.
  - Pas de VCR.py : toutes les requêtes des sources passent déjà par `_get_borne` et
    `_post_borne`, c'est là qu'on enregistre et qu'on rejoue.
  - Un échange manquant fait échouer, même quand la source avale l'exception (le cas de
    LinkedIn).
  - Trouvé en route : 10 des 16 comptes Greenhouse de la configuration répondaient 404
    (entreprises parties de Greenhouse), retirés de la configuration d'exemple.
- **C1** (v2.5.0) : `jobhunter evaluation` mesure le classement (`fit_fin`) face aux
  jugements du suivi. Pertinentes : postulé, relancé, entretien, refus, à postuler.
  Inutiles : mauvaise, pas intéressé ; une « mauvaise » dont la note dit un fait (pourvu,
  page sans offre) ne compte pas. La commande donne l'AUC avec un intervalle à 90 %,
  la précision des premières, et les pires erreurs.
  `--enregistrer` garde une référence pour juger toute variante.
  - **Premier constat**, sur les 37 jugements d'un utilisateur : **AUC 0,46**
    (intervalle 0,31 – 0,62), c'est-à-dire pas mieux que le hasard **sur les offres
    jugées**.
  - Beaucoup d'offres écartées sont notées au maximum, souvent sans note qui dise
    pourquoi : le moteur ne peut pas apprendre ce qu'il ne voit pas.
  - **Suite logique (C1 bis)** : un motif en un clic quand on écarte une offre (stage,
    langue, séniorité, métier, lieu…), pour savoir ce que le scoring rate avant de le
    modifier.
- **C2** (v2.6.0, [ADR 0010](adr/0010-identite-entreprise-poste.md)) : étude chiffrée.
  - Constats : 12 offres sur 86 perdues comme même poste dans plusieurs villes ; 9 URL
    portent 2 ou 3 clés dans une file de 12 169 offres.
  - Décision : la clé `entreprise|poste` reste, il n'y a pas de migration du suivi.
  - Le dédoublonnage du scan garde la ville de la meilleure zone et note les autres
    (`autres_lieux`).
  - `doublons` réunit les offres de même URL d'annonce, en gardant l'offre suivie puis
    l'intitulé actuel.
- **F3** écarté le 2026-10-19 : les conditions d'utilisation de HelloWork (art. 8.2)
  interdisent toute extraction automatisée, même non commerciale, sans licence écrite ;
  robots.txt interdit aussi les pages de recherche. Pistes conformes : Adzuna et Jooble
  (API officielles, qui reprennent une partie de ces offres), l'ajout d'une offre par son
  lien, ou une licence demandée à HelloWork.
