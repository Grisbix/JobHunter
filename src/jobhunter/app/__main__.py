"""`python -m jobhunter.app` : lance l'application (comme JobHunter.pyw)."""

from jobhunter.accueil import assurer_profil

assurer_profil()

from jobhunter.app.fenetre import main  # noqa: E402  (l'app lit le profil au chargement)

main()
