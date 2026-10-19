# Les programmes — que fait quoi

Ancien `Scripts/README.md`. Depuis la 2.0, les programmes vivent dans
`src/jobhunter/programmes/` (et le moteur dans les autres paquets de `src/jobhunter`) ;
`Scripts/` ne garde que les données. Les noms ci-dessous sont les noms historiques des
fichiers : `job_sources.py` est `jobhunter.sources`, `queue_io.py` est
`jobhunter.stockage.file`, `web_nav.py` est `jobhunter.navigation`, etc.
(`docs/architecture.md`).

**Point d'entrée quotidien : l'app (`JobHunter.pyw`).** Presque tout ici est appelé par
elle. La ligne de commande sert quand un programme a besoin du clavier, ou pour les
opérations en lot : `python JobHunter.pyw <commande>` (ou `python -m jobhunter
<commande>` une fois installé), et tout programme par son nom
(`python JobHunter.pyw probe_ats`).

**Le fichier qui compte : `apply_queue.json`.** Toutes les offres y sont — sauf leurs
descriptions, qui vivent à part dans `descriptions.json` (elles pesaient 64 % du fichier,
que 13 programmes réécrivaient en entier pour modifier une seule offre). La séparation est
invisible : `queue_io.charger()` les réinjecte.

**Pour lire ou écrire la file, passer par `queue_io`.** Pas `json.loads` : la lecture
directe ne voit plus les descriptions, et l'écriture directe perd le verrou.

**Pour `suivi.json`, passer par `suivi_io`.** Même raison, enjeu plus grand : une offre
perdue, le scan la retrouve demain ; une candidature perdue ne revient jamais.

---

## Le socle — lu par presque tout

| Programme | Rôle |
|---|---|
| `web_nav.py` | Navigation web (Playwright) : cookies, détection d'ATS, recherche d'offre, repli page carrière. 3400 lignes, le plus gros morceau. |
| `site_strategies.py` | Stratégies par site pour les 62 sites sans compte. |
| `jutil.py` | Écriture JSON **atomique** (tmp + `os.replace`), verrou inter-processus (casse celui d'un processus mort), et les helpers partagés : `chemin_de`, `url_de`, `existe`, `sans_accent`, `cle`. |
| `queue_io.py` | **Le seul chemin d'accès à `apply_queue.json`.** `charger()` en lecture, `transaction()` pour écrire (verrou + relecture fraîche + écriture atomique). Sépare les descriptions dans `descriptions.json`. |
| `suivi_io.py` | **Le seul chemin d'accès à `suivi.json`** — les candidatures, la donnée la moins reconstituable du projet. Même contrat que `queue_io` : `charger()`, `transaction()`, `modifier()`, `poser()`. |
| `ats_match.py` | **Le scoring.** Six axes pondérés (ESG ×3, finance ×2, IA ×1,5), plafond par densité ESG, malus séniorité et expérience. |

## Collecte d'offres

| Programme | Rôle |
|---|---|
| `scrape_jobs.py` | Scrape les 65 sites carrière d'entreprises (`unique_domains.txt`). Écrit `offres_fraiches.json` **et fusionne dans la file** (`--no-merge` pour s'en abstenir). Respecte `robots.txt`. |
| `job_sources.py` | Scan large — APIs ATS, LinkedIn public, V.I.E, FIR, Talent, France Travail, WTJ — **et fusion** dans la file. Écrit `offres_scan.json`. |
| `add_offer.py` | Colle un lien d'offre → analyse la page → file + CV/lettre. |
| `probe_ats.py` | Teste des slugs candidats sur les 5 API ATS publiques. |
| `probe_carrieres.py` | **Trouve la vraie page carrière** de chaque site et **l'ATS derrière**. Lit la page d'accueil (le site dit lui-même où il recrute), puis le sitemap, puis devine — dans cet ordre. Écrit `carrieres_detectees.json`. |
| `probe_workday.py` | Trouve les flux Workday publics des grands groupes. |
| `probe_keywords.py` | Mesure le **rendement réel** d'un mot-clé de recherche. |
| `setup_francetravail.py` | Installe et vérifie les identifiants de l'API France Travail. |

## Qualité de la file

| Programme | Rôle |
|---|---|
| `scrape_desc.py` | Récupère la description depuis la page de l'offre. Échoue sur les sites anti-bot. |
| `linkedin_desc.py` | Descriptions LinkedIn via l'**API invite publique**, là où `scrape_desc` bute sur le mur de connexion. Re-score dans la foulée. |
| `linkedin_closed.py` | Retire les offres LinkedIn qui n'acceptent plus de candidature. Ne supprime que sur signal positif. |
| `resolve_offer_links.py` | Remplace un lien « page carrière » par le lien de l'offre. |
| `enrich_homepages.py` | Trouve la page d'accueil des entreprises sans URL d'offre. |
| `link_check.py` | Vérifie les URLs (live / dead / soft-404). Module. |
| `verify_links.py` | Détecte les liens qui n'aboutissent plus chez la bonne société. |
| `recheck_dead.py` | Soft-404 rendus en JavaScript (HTTP 200 mais corps vide). |
| `audit_dispo.py` | Contrôle de toute la file sans navigateur et retrait des offres fermées ; attend et reprend sur 429 ; `--duree` l'arrête de lui-même avant de retirer. Étape 4b du pipeline, le dimanche. |
| `fix_wtj_urls.py` | Répare les liens Welcome to the Jungle. |
| `queue_tools.py` | Maintenance de la file. |
| `rescore_ats.py` | Recalcule `ats_pct` et `skills_match` sur toute la file. |
| `export_queue_csv.py` | Sauvegarde lisible en CSV. |

## Documents — CV et lettres

| Programme | Rôle |
|---|---|
| `tailor_application.py` | **Génère** le CV et la lettre adaptés à une offre. Contient `titre_poste()`, le nettoyage de l'intitulé. |
| `generate_docs.py` | Lots depuis la file. Sélecteurs : `--top`, `--all`, `--sans-source`, `--objet`, `--collisions`, `--cv-generique`. |
| `rename_docs.py` | Noms au format `Camille_Exemple_CV/Lettre_<Poste>_<Entreprise>`. |
| `sync_docs.py` | Gendarme de cohérence : le `.docx` est la source, le PDF en découle. |
| `refresh_letters.py` | Rafraîchit toutes les lettres — date, ordre, objet. Idempotent. |
| `fix_letters.py` | Réhabilite les lettres existantes. |

## Candidature et suivi

| Programme | Rôle |
|---|---|
| `controle_dossiers.py` | Contrôle des dossiers avant envoi (lecture seule) : PDF lisible, une page, coordonnées, gabarit rempli ; préfère le PDF à jour à son .docx. Étape 5b du pipeline. `python JobHunter.pyw controle`. |
| `apply_runner.py` | Remplit les formulaires, **semi-automatique** : le clic final d'envoi reste le tien. Piloté par le panneau Candidatures de l'app (`--pilote`) ou au clavier ; après « envoyé », observe la page et écrit le suivi avec la preuve (`envoi` confirmé / incertain, capture dans `Scripts/_preuves/`). |
| `relances.py` | Mails de relance J+7 / J+10 par offre. `--brouillons` prépare ceux de toutes les relances dues, sans rien ouvrir ni envoyer : tâche Windows `Relances`, le lundi à 9h30, bilan dans le vault (`Routines/Relances/`). |
| `metriques_hebdo.py` | Bilan de la semaine, en lecture seule : candidatures envoyées, à relancer, réponses, fusions du pipeline et jours sans run. Lancé le dimanche à 21h par la tâche Windows `Metriques_Emploi` ; sortie dans le vault, `Routines/Metriques_Emploi/`. |
| `notify_matches.py` | Alerte Windows quand une offre à fort fit arrive. |
| `acces.py` | Gère les accès aux sites **sans jamais stocker de mot de passe**. |
| `test_acces_sites.py` | Mesure quels sites de la file sont ouvrables. |

## Tests

| Programme | Couverture |
|---|---|
| `test_patterns.py` | 68 cas — reconnaissance de formulaires, recherche d'offres, remplissage. |
| `test_titres.py` | 38 cas — nettoyage de l'intitulé, élision, idempotence. |
| `test_contrats.py` | 26 cas — déduction du type de contrat, et ses faux positifs. |
| `test_sources.py` | 24 cas — arbitrage des doublons entre sources. |
| `test_queue_io.py` | 25 cas — exclusion entre processus, non-écriture sur exception, séparation des descriptions. |
| `test_suivi.py` | 9 cas — une candidature enregistrée ne disparaît jamais, même si son annonce ferme. |
| `test_relances.py` | 11 cas — modèle J+7 puis J+10, brouillon retouché jamais écrasé, rien n'est envoyé. |
| `test_metriques_hebdo.py` | 26 cas — dates `AAAA-MM-JJ` et `jj/mm`, entrées sans date, seuil de relance, journaux du pipeline. |
| `test_web_nav_mock.py` | 20 cas — réseau et Ollama mockés. |
| `test_web_nav.py` | Tests synthétiques de `web_nav`, sans réseau. |
| `test_live_nav.py` | Test réel en lecture seule sur de vrais sites carrière. |

Les cinq premiers tournent sans réseau : `python test_patterns.py`, etc.

## Hors périmètre

Aucune création de compte et aucune lecture de boîte mail par programme : ce sont des
actions que l'utilisateur fait lui-même.

---

## Pièges du code, appris à la dure

**`\b` dans une regex écrite via un heredoc shell.** Il devient soit le caractère
backspace `\x08`, soit un antislash littéral. Dans les deux cas le motif compile, ne lève
rien, et **ne matche plus jamais**. Trois occurrences. `job_sources.py` et
`tailor_application.py` refusent maintenant de démarrer si un de leurs motifs est corrompu.

**Un sélecteur doit comparer le contenu du fichier, pas la donnée source.** Un test du
genre `titre_poste(brut) != brut` est vrai en permanence : il ne converge jamais et
repropose éternellement les mêmes offres.

**Windows ignore la casse des noms de fichiers.** Deux noms qui ne diffèrent que par la
casse sont **un seul fichier**. Toute déduplication de noms doit grouper en minuscules.

**`sys.stdout.reconfigure(encoding="utf-8")` est obligatoire** dans tout programme qui
affiche un emoji. Sans lui, la sortie redirigée (tuyau, log, tâche planifiée) retombe sur
cp1252 et lève `UnicodeEncodeError` à la première ligne.

**Une annonce ferme APRÈS qu'on y a postulé.** Toute suppression automatique doit donc
épargner les offres présentes dans `suivi.json` — sinon elle efface en priorité celles
auxquelles l'utilisateur a candidaté, et la trace devient orpheline.

**Vérifier un import en chargeant le module, pas en analysant la syntaxe.** `ast.parse`
passe sur un `import` manquant ; l'erreur ne sort qu'à l'exécution.

**Un index doit pointer sur l'objet qu'on garde, pas sur celui qu'on a lu.**
`merge_into_queue` rangeait dans son index le dict venu du *scan*, alors que la file
recevait un dict *différent*. Toute promotion d'URL ou description arrivant plus tard dans
le même lot s'écrivait donc sur un orphelin : les compteurs annonçaient « 1 lien promu »
et la file gardait le lien LinkedIn et sa description vide. C'est le cas **normal**, pas un
cas limite — un `--all` enchaîne ATS, LinkedIn, WTJ, eFC et Indeed sur la même annonce.

**Un garde-fou qui choisit ses cibles par le nom finit par en rater.** Le contrôle des `\b`
ne regardait que les globales préfixées `_RX_` : il ignorait `_DOMAIN_RX`, `_HARD_NEG_RX`
et `_AI_RX`, c'est-à-dire exactement les motifs de `title_ok`, le filtre qui décide ce qui
entre dans la file. Il balaie maintenant **toute** `re.Pattern` du module.

**Deux listes de mots-clés qui doivent s'accorder divergent en silence.** `title_ok` exige
un mot du lexique large (`scrape_jobs`) **et** un mot métier (`_DOMAIN_RX`) : un terme
présent dans l'un et absent de l'autre fait jeter l'offre sans un mot. « CSRD » était un
mot-clé de *recherche* du scan et vivait dans `_DOMAIN_RX`, mais pas dans le lexique — on
demandait ces offres à LinkedIn pour les jeter à l'arrivée. `test_sources.py` teste
l'invariant.

**Une collecte vide a deux causes opposées.** Rien à prendre, ou refus d'entrée. Les deux
rendaient `[]` sans un mot, si bien qu'un scan entièrement bridé ressemblait à une journée
calme — et on le relançait, ce qui est exactement ce qu'il ne faut pas faire face à un
quota. `job_sources.INCIDENTS` compte les refus et `main()` les affiche ; un 404 d'ATS
reste silencieux, lui, car un slug mort est le cas normal.

**Ne rends que le verrou que tu as pris.** `prendre_verrou` est réentrant, `rendre_verrou`
ne l'est pas. Une fonction qui prend puis rend, alors que son appelant le gardait pour tout
le programme (`jutil.garder`), le lui retire — et la suite du travail se fait à découvert.
`jutil.tenu(chemin)` répond avant de prendre.

**Écrire un instantané mémoire écrase le travail des autres.** L'app gardait `suivi.json`
en mémoire et le réécrivait ENTIER à chaque clic. Un « postulé » sur une offre effaçait
donc les relances que `relances.py` venait de noter sur d'autres — sans un mot. On écrit
une entrée, sous verrou, sur l'état relu à l'intérieur du verrou : c'est ce que fait
`suivi_io.poser`. Testé par `test_suivi.py`.

**Une boucle `after` qui ne rattrape qu'une exception précise meurt à la première autre.**
`_drain` (l'app) ne voyait que `queue.Empty` ; toute autre panne sortait AVANT la ligne qui
reprogramme la boucle. Mesuré : 1 tour au lieu de 20, et plus aucun rechargement de table
après un scan. La reprogrammation va dans un `finally`. Dans un `.pyw` il n'y a pas de
console, donc la trace part dans le vide : `root.report_callback_exception` la range
maintenant dans `_logs/app_erreurs.log`.

**Une promesse d'annulation doit désigner un fichier qui existe.** La boîte de suppression
disait « récupérable via git » ; le jour de la vérification, 424 offres du disque
n'étaient dans aucun commit. La suppression écrit maintenant une copie horodatée dans
`_corbeille/` avant de retirer quoi que ce soit.

**Deux chemins vers le même fichier ne sont pas égaux.** `queue_io` ne réinjectait les
descriptions que si le chemin reçu valait `CHEMIN` *tel quel* : `Path("apply_queue.json")`,
lancé depuis `Scripts/`, rendait les 11 710 offres sans description (le banc réel a vu
25 461 écarts, tous faux), et `sauver` les aurait réécrites dans la file. Les chemins se
comparent maintenant résolus (`_est_la_file`).
