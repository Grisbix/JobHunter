"""`python -m jobhunter.app`: launches the application (like JobHunter.pyw)."""

from jobhunter.accueil import assurer_profil

assurer_profil()

from jobhunter.app.fenetre import main  # noqa: E402  (the app reads the profile when loaded)

main()
