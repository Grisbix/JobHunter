"""`python -m jobhunter.app`: launches the application (like JobHunter.pyw)."""

from jobhunter.profiles import appliquer

appliquer()  # the active profile, before any module builds its paths

from jobhunter.welcome import assurer_profil  # noqa: E402

assurer_profil()

from jobhunter.app.window import main  # noqa: E402  (the app reads the profile when loaded)

main()
