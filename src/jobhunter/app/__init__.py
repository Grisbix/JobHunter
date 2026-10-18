"""L'application bureau (ancien JobHunter.pyw, phase 3.7 du plan).

commun     chemins, statuts, colonnes du tableau, etapes et maintenance
theme      couleurs, polices, widgets de base
fenetre    App, assemblage des mixins ; main()
tableau, donnees, fiche, actions, panneaux, detail, execution : un mixin par domaine

FACADE (jobhunter._facade) : le paquet voit les noms de ses sous-modules (`app.App`,
`app.COLS`) ; remplacer `app.SUIVI` atteint le module qui le definit. Charger le paquet
lit le profil : le lanceur appelle `jobhunter.accueil.assurer_profil()` d'abord.
"""

from jobhunter import _facade

_MODULES = _facade.installer(
    __name__,
    (
        "commun",
        "theme",
        "tableau",
        "donnees",
        "fiche",
        "actions",
        "panneaux",
        "detail",
        "execution",
        "fenetre",
    ),
)
