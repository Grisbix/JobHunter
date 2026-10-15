---
paths:
  - Scripts/ats_match.py
  - Scripts/tri_file.py
---
# Scoring — `ats_match.fit_score`

`fit_score(text, title)` rend un entier 1–10. Six axes pondérés : ESG ×3, finance ×2,
IA ×1,5, data/risk/conseil ×1.

Trois mécanismes qu'on ne devine pas en lisant la formule :

- **Un plafond proportionnel à la densité ESG.** Sans lui, finance + risk + conseil
  suffisent à saturer le score sans le moindre signal ESG. Le plafond suit la densité
  de marqueurs, pas leur simple présence : une description d'entreprise de 8000
  caractères qui dit une fois « sustainability » n'est pas une offre ESG. Un intitulé
  explicitement ESG lève le plafond à 10.
- **La langue plafonne en dernier** (`plafond_langue`) : `langues_parlees` du profil. Annonce
  **rédigée** dans une autre langue → 2 (mots-outils ; l'en-tête compte à part, car EURES traduit
  des annonces) ; annonce qui **exige** une langue non parlée → 4. « Dutch is a plus »,
  « preferably Dutch », « Dutch and/or French », « Chinese markets » n'exigent rien.
- **L'analyste financier classique monte à 8** (`_TITRE_FINANCE`, 2026-10-07) : sans ESG ni
  IA, le plafond général est 6, mais un intitulé finance (financial/investment/credit analyst,
  M&A, FP&A, contrôleur de gestion…) plafonne à 8 + 2 × axe ESG. L'ESG reste devant.
- **Des vetos de métier sur l'intitulé**, qui l'emportent sur tout vocabulaire vert
  sauf un marqueur ESG-finance fort (`_ESG_TITRE_FORT`) : HSE → 6 ; métier technique
  ou hors finance (`_titre_hors_cible` : recherche académique, achats, supply chain,
  bâtiment, administratif, sciences) → 6, ou 8 si le poste parle d'IA. Un mot
  générique — sustainab, durable, green, climat — levait sinon le plafond de n'importe
  quel métier. Un intitulé technique qui nomme un métier financier (audit, analyste,
  crédit) reste dans la cible.
- **Les malus s'appliquent au seul INTITULÉ**, jamais à la description. Cherchés dans
  le texte entier, « Lead Generation » déclenchait le malus SENIOR et « présence
  commerciale » le malus NEG, soit −4 sur une offre ni senior ni commerciale.

**`fit_fin` départage les ex aequo** (`fit_detail`, 2026-10-09) : décimal, toujours à ±0,45 du
`fit` entier — son arrondi rend `fit`, aucun seuil ne bouge. Dans le niveau, `_departage`
pèse intitulé ESG, densité ESG, compétences ESG/finance citées (non plafonnées), place du
brut, expérience exigée. Tout code qui écrit `fit` écrit aussi `fit_fin` ; l'app, les
dossiers, top et alertes trient dessus.

**Le `fit` mesure la densité de vocabulaire, pas l'accessibilité du poste.** Un
« 2027 Corporate & Investment Bank » sort à 6, un « AI Tech Lead » à 7. Pour trier ce
qui colle vraiment au profil, c'est `tri_file.py` qui tranche — sur l'intitulé et
l'expérience exigée.
