"""`python -m jobhunter.app`: launches the application (like JobHunter.pyw)."""

from jobhunter.welcome import assurer_profil

assurer_profil()

from jobhunter.app.window import main  # noqa: E402  (the app reads the profile when loaded)

main()
