---
paths:
  - JobHunter.pyw
---
# Application bureau

**Le tableau est indexé par position.** Retirer une colonne oblige à retirer *aussi*
la valeur correspondante dans `_row_vals`, sinon tout se décale d'un cran.

`_racine()` cherche `Scripts/apply_queue.json` en remontant : l'app fonctionne où
qu'on la place. Ne jamais y coder une racine en dur — les chemins du projet ont bougé
quatre fois en deux jours.

`_auto_scrape()` (2026-09-21) lance `scrape_jobs.py --headless` au démarrage
puis au retour de focus. Trois garde-fous, tous nécessaires :

| Garde-fou | Valeur | Pourquoi |
|---|---|---|
| verrou `_bg_busy` | partagé avec `_auto_sync` | `job_sources.main()` garde le verrou de file pendant tout le scan |
| `_SCRAPE_COOLDOWN_S` | 1800 s | sans lui, chaque clic sur la fenêtre relançait un scan |
| plafond session | 4 | borne le coût d'une journée d'allers-retours |

Sans eux, un simple retour de focus pouvait geler l'app le temps d'un scan complet.

## Un `.pyw` ne dit jamais pourquoi il ne s'ouvre pas

L'extension `.pyw` supprime la console : une exception au démarrage ferme la fenêtre sans
un mot. Pour diagnostiquer, relancer avec l'interpréteur **console** et lire la trace :

```bash
PYTHONIOENCODING=utf-8 python JobHunter.pyw
```

Mesuré le 2026-09-22 : l'app ne s'ouvrait plus depuis le 20/09 17:27, et le commit
`85e5d58c` — celui-là même qui ajoutait `_auto_scrape` — avait perdu sa ligne
`def _auto_scrape(self):`. Le corps de la méthode, indenté de huit espaces, avait été
absorbé par `_on_focus_scrape` juste au-dessus. **Le fichier compilait sans erreur** :
`py_compile` passe, l'attribut ne manque qu'à l'exécution.

Corollaire : après toute édition de ce fichier, vérifier que chaque `self._methode`
appelée existe bien comme `def` de la classe `App`, puis **lancer l'app** — la compilation
ne prouve rien ici.

## « ↶ Retour » de disposition (Alt+Gauche)

`_dispo_pile` mémorise la disposition **avant** chaque geste : séparateur tableau | fiche,
largeur des colonnes (`_dispo_suivre` sur presser/relâcher), « Agrandir » la fiche, barre
Outils. `_dispo_retour` remonte d'un geste. Tout nouveau geste d'agrandissement appelle
`_dispo_memo()` avant d'agir. Le contenu (statuts) relève de Ctrl+Z, pas de cette pile.

## Statuts qui masquent, statuts qui grisent

La colonne Lieu affiche `zones.ville_affichee` (IDF = « Paris »), la colonne Pays `zones.pays_lieu` ; `_sortkey` trie sur ces mêmes valeurs.

`pas intéressé` et `expiré` **masquent** la ligne (`MASQUANTS`, interrupteur « Voir les
masquées » pour la revoir), `mauvaise` la **grise**. `expiré` = annonce fermée, un fait,
pas un jugement : ne pas le confondre avec `mauvaise` ni `refus`. Les deux vivent dans `suivi.json` ; aucun ne retire l'offre de
la file — c'est le rôle d'« Écarter », qui passe par `exclusions.py`. Tout nouveau
statut va dans `STATUTS`, `ST_EMOJI` et, s'il colore la ligne, `ST_COULEUR`.
Le suivi s'écrit par `suivi_io` (clé du statut : **`s`**, pas `statut` — le panneau
Stats comptait 0 postulé pour 10 candidatures, le 2026-09-23, sur cette confusion).

Un dialogue se parente à **`self.root`**, jamais à `self` : `App` n'est pas un widget.
`Toplevel(self)` compile, et lève au clic — « Écarter » ne s'ouvrait pas, constaté et
corrigé le 2026-09-23.

## Vérifier visuellement sans lancer de scan

`JOBHUNTER_SANS_FOND=1` coupe scan, descriptions et sync ; `JOBHUNTER_ACTION` (avec la
précédente) exécute du Python dans l'app 1,5 s après l'ouverture, `app` désignant
l'instance — pour se placer sur un panneau avant une capture.
