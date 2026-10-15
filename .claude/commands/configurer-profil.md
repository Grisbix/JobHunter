---
description: Paramètre JobHunter pour l'utilisateur à partir de son CV (profil complet, vérifié)
argument-hint: "[chemin du CV .docx ou .pdf]"
---

Tu configures JobHunter pour la personne qui l'utilise. À la fin, `profil/profil.json`
doit être **complet** : l'application doit trouver, trier et préparer ses candidatures
aussi bien que pour le profil d'exemple, mais pour SON métier.

CV indiqué : $ARGUMENTS

## Règles

- **N'invente aucun fait.** Diplômes, employeurs, chiffres, outils et langues viennent du
  CV ou de l'utilisateur. Ce qui manque, tu le demandes ; sinon tu laisses
  `"À COMPLÉTER"` et tu le signales à la fin.
- Aucun mot de passe, aucune clé d'API : tu ne les demandes pas et ne les écris nulle
  part. Adzuna et Jooble, l'utilisateur crée lui-même ses clés (voir README).
- Aucune modification du moteur (`Scripts/*.py`) : tout se règle dans le profil. Si un
  besoin ne peut pas s'y exprimer, dis-le au lieu de coder.
- Ne lis pas `profil/exemple_finance_esg.json` en entier d'un coup s'il ne passe pas :
  lis-le par rubrique (`python -c "import json;print(json.dumps(json.load(open('profil/exemple_finance_esg.json',encoding='utf-8'))['scoring'],ensure_ascii=False,indent=1))"`).

## Étapes

1. **Le CV.** S'il n'est pas indiqué ci-dessus, demande son chemin. Préfère un `.docx` :
   c'est le modèle de tous les CV envoyés (un PDF est envoyé tel quel). Lis son texte :
   `python -c "import sys;sys.path.insert(0,'Scripts');import premier_lancement as p;print(p.lire_cv(__import__('pathlib').Path(r'CHEMIN')))"`.

2. **Les questions**, en un seul message, avec tes propositions tirées du CV :
   - métiers visés (2 à 5 intitulés, tels qu'ils apparaissent dans les annonces) ;
   - années d'expérience, stages compris ;
   - type de contrat (CDI, CDD, stage, alternance, V.I.E, freelance) ;
   - villes ou régions ; l'étranger aussi ? ;
   - accords des lettres : « diplômé » ou « diplômée » ;
   - métiers ou secteurs à **exclure** ;
   - les entreprises qu'il vise en priorité, s'il en a.

3. **Le squelette.** Lance (ajoute `--force` si un profil existe, après accord) :
   ```bash
   python Scripts/premier_lancement.py "<cv>" --metiers "<m1, m2>" --annees <n> --genre <m|f> --prioritaires "<secteurs>" --secondaires "<secteurs>" --entreprises <o|n>
   ```
   Secteurs connus : `python -c "import sys;sys.path.insert(0,'Scripts');import zones;print(list(zones.CATALOGUE))"`.
   Une ville absente du catalogue se déclare dans `zones` du profil, en objet
   `{"cle", "libelle", "lieux", "departements"}` (exemple en tête de la section
   « SECTEURS GEOGRAPHIQUES » de `Scripts/zones.py`).
   `--entreprises o` seulement si la personne vise la finance ou l'ESG.

4. **Le profil complet.** Compare `profil/profil.json` à l'exemple, rubrique par
   rubrique, et remplis chacune pour ce métier :
   - `domaines` : un par métier visé. `mots_titre` = mots et variantes d'intitulé
     (FR + EN, masculin + féminin), `parcours_fr`/`parcours_en` = 3 à 4 phrases
     factuelles tirées du CV, `accroche_*` et `preuve_*` = une phrase chacune.
   - `competences` : une entrée par compétence du CV, avec les mots que les annonces
     emploient pour la dire (synonymes, anglais, sigles). Vise 15 à 30 entrées.
   - `termes` : les sigles et outils du métier, en minuscules.
   - `scoring` : `axes` (familles de compétences), `axe_coeur` = le cœur du métier,
     `axe_complement` = ce qui le distingue ; `intitules_coeur(_forts)` = intitulés
     qui méritent 10 ; `intitules_hors_metier` = intitulés à plafonner bas.
   - `niveau` : selon les années d'expérience (`experience_max` = ce qu'il peut viser).
   - `filtre_titre` : `metier` = ce qu'un intitulé doit contenir pour être collecté,
     `exclus` = ce qui l'écarte. Trop étroit, aucune offre ; trop large, du bruit.
   - `tri.metiers_exclus` : familles hors cible.
   - `collecte.mots_cles` : 8 à 15 recherches, FR et EN si l'étranger est visé.
   - `message` et `lettre` : diplôme, langues, phrase de profil, faits par compétence.
   Une liste de mots accepte `"mot"` ou `"re:regex"`. Les regex s'écrivent avec l'outil
   d'édition, **jamais via un heredoc shell** (le `\b` y devient un backspace).

5. **Vérifie.**
   ```bash
   python Scripts/profil.py
   python Scripts/verifie_profil.py "<intitulé visé 1>" "<intitulé visé 2>" "<intitulé voisin hors cible>" "<intitulé senior du métier>"
   ```
   Attendu : les intitulés visés sont `garde`, dans le bon domaine, avec la note la plus
   haute ; les hors cible sont `ECARTE` ou notés bas ; le senior est pénalisé si la
   personne est junior. La note est calculée sur l'intitulé seul : une vraie offre,
   notée avec sa description, monte plus haut. Corrige le profil et recommence
   jusqu'à ce que ce soit juste.
   Puis un essai réel, sans rien écrire : `python Scripts/job_sources.py --linkedin --dry`.
   Regarde les intitulés gardés : s'ils débordent ou manquent, ajuste `filtre_titre` et
   `collecte.mots_cles`.

6. **Le bilan à l'utilisateur** : ce qui a été rempli, ce qui reste `À COMPLÉTER`, les
   choix faits à sa place, et la suite : `python JobHunter.pyw`, puis
   `python Scripts/pipeline_quotidien.py` pour la première collecte complète.
