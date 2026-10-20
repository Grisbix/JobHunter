# 0014 — The eight open questions of the technical plan, settled

**Status**: accepted on 2026-10-21 (JobHunter 3.10.1).

## Context

The technical plan of 20 October (profiles, API connections, search settings, updates)
ended on eight questions to settle "before development". Most of the work has shipped
since (3.2 to 3.10), and each release answered one of them in code. This record states
the answers in one place, as they are implemented, so that the next change starts from a
decision and not from a question.

## Decision

1. **What is a profile for?** First, several searches of one person (another job,
   another city); several people on one computer are supported too, since a profile is a
   complete workspace (ADR 0013). What profiles share is the machine's: the API keys and
   their daily quota (`sources.quota`, counted for all profiles together) and the
   dedicated Chrome profile. Two people who need separate quotas use two installations.
2. **Which installation channel is maintained?** Two: the Windows installer
   (`JobHunterSetup.exe`, with its embedded Python) for users, and the source ZIP of a
   tagged release (launchers `install`/`update`) — which is also what a developer
   installs with `pip install git+…@vX.Y.Z`. MSIX and Velopack were studied (notes of
   20 October) and not adopted: they would add a second update path to secure.
3. **Which accesses are shared, between which profiles?** The keyed APIs (Adzuna, Jooble,
   France Travail) and the Chrome profile, between the profiles of one installation, read
   from the main workspace and never copied (ADR 0013). No program handles a password
   (ADR 0005 and the web-navigation rules).
4. **Is the system keyring reachable from scheduled routines?** Not reliably: a Windows
   task that runs while the user is logged off has no access to the user's credential
   store. The keys stay in local files ignored by git (`adzuna.json`, `jooble.json`,
   `francetravail.json`), entered through the application (masked input, never through
   the command line or a chat), never printed — the connection test shows only the type of
   an error.
5. **How long are histories, diagnostics and backups kept?** Bounded by count where they
   grow with every collection: `vus_sur` 12 sources, `changements` 10, `historique_fit` 10
   entries; daily backups of the queue 7 days rolling. Everything the user may want back
   is kept until the user deletes it: update backups (`_sauvegarde_maj/`), the
   migration ZIP, the versions set aside by « Documents à comparer »
   (`_a_comparer/_anciennes/`). The yield and per-company logs are small and kept.
   No program deletes user data on its own, apart from the bounded lists above.
6. **Does switching profile need a restart?** Yes. Every data path is fixed when its
   module is imported; the application restarts on the chosen profile (3.2). A hot switch
   was rejected in ADR 0013.
7. **What proves that an update worked?** Not the end of the download: the updater
   writes the expected version (`.maj_attendue.json`), the new version confirms it at
   start-up after reading the data (`confirmer_demarrage`), and a second update must say
   "Déjà à jour". The CI replays real transitions from the two previous releases on
   Windows and Linux (`update-transition.yml`, 3.4).
8. **What about program files the user modified on purpose?** They are kept; the new
   version is written beside them as `.nouveau` and the summary says so. "Modified" is
   measured against the installed version's manifest, not guessed. A file the user created
   is never touched. Every replaced file is backed up first, and `--annuler` restores it.

## Consequences

- The plan's "decisions to make" section is closed; a change to one of these answers is a
  new ADR, not an edit of this one.
- Two answers depend on the signing key (question 7 is complete only once releases are
  signed, ADR 0012): until the author publishes the public key, updates are verified
  against the tagged release only.
