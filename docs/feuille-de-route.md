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
| B1 | **Test d'architecture** : le moteur (`jobhunter.*` hors `app`, `accueil`) n'importe ni `tkinter` ni `customtkinter` ni `jobhunter.app` | Le plan dit « vérifié en CI par import-linter », mais rien n'est branché : un test pytest de quelques lignes suffit, sans ArchUnitPython ni import-linter | un import volontaire de Tkinter dans `scoring` fait échouer le test ; le retirer le fait passer |
| B2 | **Réponses enregistrées des connecteurs** (pytest-recording / VCR.py, dépendance de test seule) : APEC (API), LinkedIn guest, sitemap WTJ, Workday, Greenhouse/Lever | Les doublures actuelles (`faux_reseau`) sont écrites à la main : elles ne disent pas si le parseur lit encore la vraie réponse d'aujourd'hui. Une réponse réelle enregistrée, expurgée (cookies, en-têtes), rend le parseur reproductible | dix réponses rejouées sans réseau donnent les mêmes offres ; un échange manquant fait échouer ; aucun cookie ni identifiant dans les fichiers versionnés |
| B3 | **Diagnostic de lenteur** : procédure py-spy (outil externe, pas une dépendance) dans `CONTRIBUTING.md` | Utile la prochaine fois qu'une étape dépasse sa durée (collecte, disponibilité) : localiser au lieu de supposer | la procédure retrouve la fonction d'un blocage provoqué exprès, rapport sans données personnelles (`--locals` désactivé) |

## Étape C — Les deux axes métier restants (Codex 18/10)

| # | Quoi | Pourquoi | Fini quand |
|---|---|---|---|
| C1 | **Classement évalué sur les jugements réels** : constituer le jeu de référence à partir de ce qui existe déjà. Pertinentes : les offres postulées, relancées ou en entretien du suivi. Inutiles : « pas intéressé » et `exclusions.json`. Puis mesurer le classement actuel (précision des N premières). | Aucune mesure aujourd'hui de « les premières offres sont-elles les bonnes ». C'est le préalable à toute variante, sémantique ou autre. | un chiffre de référence reproductible (`jobhunter evaluation`) ; toute modification du scoring est comparée à lui, avec le banc |
| C2 | **Identité d'offre plus robuste** : d'abord une **étude**. Compter sur la vraie file les homonymes (même `entreprise\|poste`, lieu ou référence différents) et les doublons sous deux intitulés. | La clé `entreprise\|poste` est celle de `suivi.json`, la donnée la moins reconstituable. On ne migre rien sans un problème mesuré. | une ADR qui chiffre le problème et tranche : identité secondaire (référence de source) en complément, ou statu quo |

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

## Ordre proposé

**A** (en continu, surtout de l'observation) → **B1** (une heure) → **B2** → **C1** →
**C2 (étude)** → **D1 (sondage)** → **B3** quand une lenteur se présente → **E** quand
la distribution revient.

Ce qui reste hors d'atteinte, quoi qu'il arrive :
- aucune soumission automatique ;
- aucun contournement anti-bot ;
- aucun mot de passe manipulé.
