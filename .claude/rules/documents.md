---
paths:
  - Scripts/tailor_application.py
  - Scripts/generate_docs.py
  - Scripts/regenere_docs.py
  - Scripts/sync_docs.py
  - Scripts/chemins.py
---
# Documents générés

`tailor_application.py` génère CV et lettre pour une offre ; `generate_docs.py` en
fait des lots depuis la file. **Le `.docx` est la source, le PDF en découle** —
`sync_docs.py` est le gendarme de cette règle.

`chemins.py` est **le seul endroit qui décide où vivent les documents générés**. Onze
programmes construisaient `ROOT / "CV" / "Par_offre"` chacun de leur côté ; les sortir
du dépôt demandait onze modifications cohérentes. La résolution ne peut pas échouer :
`Scripts/chemins.json` s'il existe, sinon la racine du projet.

La distinction qui compte :

| Dossier | Nature |
|---|---|
| `Par_offre/` | **sortie**, reconstruite entièrement par `regenere_docs.py` |
| `CV/Modèles/`, `CV/Sur_mesure/`, `Lettres/Relances/`, `Lettres/Messages/`, `Lettres/Sur_mesure/` | **entrées** écrites à la main, que rien ne régénère |

`Lettres/Sur_mesure/<entreprise>__<poste>.txt` **remplace le corps** de la lettre pour
cette offre-là, paragraphes séparés par une ligne vide. Le gabarit sert 5374 annonces et
ne peut donc rien dire de précis sur aucune ; quand une offre mérite une heure de travail,
le corps se rédige ici.

Tout ce qui entoure reste **généré** — en-tête, date, objet, formule d'appel (qui sait
nommer deux destinataires) et reprise de clôture accordée. On ne réécrit pas à la main ce
que le code fait mieux.

`CV/Sur_mesure/<entreprise>__<poste>.json` retouche le CV de cette offre : `remplace`
(texte du modèle → texte pour l'offre), `ajoute_apres`, `supprime` (pour tenir sur une
page). Une ancre introuvable est signalée, jamais ignorée. `generate_docs.py --url <extrait>`
refait CV et lettre d'une offre après retouche.

**Sans sur-mesure, le CV passe par `cv_auto`**, sans LLM : `CV/Faits.json` liste des faits
validés par l'utilisateur (`"valide": true`), avec leurs déclencheurs. Un fait non validé n'est
jamais utilisé : rien ne s'invente. `cv_une_page()` régénère en retirant les `allegements`
un par un tant que le PDF dépasse une page, puis repart du modèle nu en dernier recours.
Tout appelant qui produit un CV passe par `cv_une_page`, pas par `tailor_cv` seul.
**Un fait donné pour une seule offre va dans son `CV/Sur_mesure`, jamais dans la banque**
sans accord explicite : Iberdrola et « espagnol avancé » (Helexia) y avaient été mis par erreur.

La recherche du fichier est tolérante à la casse et à la ponctuation, et la clé passe par
`_slug` **en entier**. Assembler deux slugs autour d'un `__` littéral donnait
`mirova__analyste…` face à un fichier réduit à `mirova_analyste…` : la lettre sur mesure
n'était jamais trouvée, **sans un message**, et la générique partait à sa place.

## Style d'écriture

Le registre se règle dans le profil (`lettre`, `message`) et, pour une offre qui mérite
une heure, dans `Lettres/Sur_mesure/`. Une seule règle est assez forte pour vivre ici.

## Ce qu'une lettre ne dit jamais

**Aucune phrase ne dévalorise le candidat.** Règle posée par l'utilisateur le 2026-09-22, après
sept réécritures du même paragraphe. Ni « mon parcours est court mais spécialisé », ni
« je suis junior et je l'assume », ni « mon expérience professionnelle est encore courte ».

Le fait reste vrai et l'annonce le sait déjà : elle demande une *première* expérience.
L'écrire n'apporte aucune information et retire au lecteur l'envie d'aller plus loin. On
énonce ce qu'on apporte, jamais ce qui manque.

Le mouvement inverse — se vanter — est traité par les règles de style ci-dessus : pas de
superlatif, pas de « spécialisation rare », pas de jugement sur le marché du recrutement
(« ces deux compétences se rencontrent rarement dans une même annonce » explique son
métier au recruteur).

`verifie_redites.py` **n'attrape rien de tout cela**. Il compte les répétitions, les
conjonctions et les points-virgules ; le ton lui échappe entièrement, et il était au vert
sur les sept versions. C'est la raison d'être de `Lettres/Sur_mesure/`.

La conversion `.docx` → PDF passe par LibreOffice (`soffice.exe`), en **lots** : une
conversion à la fois coûte 1,2 s dont l'essentiel est le démarrage du programme.
