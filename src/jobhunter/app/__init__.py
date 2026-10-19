"""The desktop application (former JobHunter.pyw, phase 3.7 of the plan).

commun     paths, statuses, table columns, steps and maintenance
theme      colours, fonts, basic widgets
fenetre    App, assembly of the mixins; main()
tableau, donnees, fiche, actions, panneaux, detail, execution: one mixin per domain

FACADE (jobhunter._facade): the package sees the names of its submodules (`app.App`,
`app.COLS`); replacing `app.SUIVI` reaches the module that defines it. Loading the
package reads the profile: the launcher calls `jobhunter.accueil.assurer_profil()` first.
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
