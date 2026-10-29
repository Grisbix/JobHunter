#!/usr/bin/env python3
"""daily_pipeline — The morning scan, in a single entry point.

WHAT IT REPLACES, and why. Three mechanisms were supposed to feed the queue. Measured
on 21/09/2026: none of the three brought a single offer.

  Windows task `JobSearch_Daily_Scrape`
      -File ...\\Recherche_emploi_ESG_Finance_ORGANISE\\Scripts\\run_pipeline.ps1
      That file no longer exists. Result 0xFFFD0000 every morning at 8:00.

  hermes/scripts/run_full_job_pipeline.sh
      Scraped Indeed through curl_cffi impersonate='chrome124'. The request GOES
      THROUGH (HTTP 200, 794 KB) but the page no longer contains a single card:
      `td.resultContent` = 0, `data-jk=` = 0, neither captcha nor block. The parser
      targets a markup Indeed no longer uses. The script prints "Scraped 0 jobs",
      merges zero offers, and ends on "✅ Pipeline termine". A failure that declares
      itself successful.

  hermes/scripts/run_job_search_pipeline.sh
      Orchestrated three third-party wrappers. Last run: three `returncode=0`, three
      "wrapper executed", one of them a "placeholder summary". Nothing enters
      apply_queue.json.

NONE OF THE THREE TOUCHED THE V.I.E. The 274 in the queue came from manual runs.

THIS PIPELINE calls the project's code, the tested one:

    1. job_sources.py, in five      a) ATS, Workday, V.I.E, FIR    b) LinkedIn
       passes, each merged          c) eFC x9 sites, EURES
                                    d) France Travail, Adzuna, Jooble
                                    e) WTJ (last: it often makes us wait)
    2. ajoute_vie.py --completer   the V.I.E DETAIL route: allowance, contact,
                                   description — which the LIST does not have
    3. linkedin_desc.py            the text of today's LinkedIn offers, which arrive
                                   with their title only
       scrape_desc.py (3b, 3c)     same for Workday (API) and the career sites read
                                   without a description (public pages)
    4. tri_file.py --supprime      seniority, required experience, profession — the
                                   applications of suivi.json are spared
    5. generate_docs.py --top N    CV and letter for the top of the queue

Each run writes its log into _logs/pipeline_<date>_<time>.log. The engine's modules
add pipeline_<date>_<time>_moteur.log to it (timestamped).

THE STEPS ARE SEQUENTIAL, and it is not a matter of style: `job_sources.main()` takes
the queue lock when it starts and keeps it for the whole scan. Two steps in parallel,
and the second exits with code 3.

A ZERO IS NOT GOOD NEWS. "Nothing to take" and "refused entry" give the same figure,
and that is how an entirely throttled scan passes for a quiet day — after which it is
run again, which is exactly what must not be done against a quota. This program
therefore reads each step's counters and says so when a step returned nothing.

Run:
  python JobHunter.pyw pipeline
  python JobHunter.pyw pipeline --docs 50
  python JobHunter.pyw pipeline --sans-docs
"""

import argparse
import os
import re
import subprocess
import sys
import threading
import time

from jobhunter import frozen as _gele
from jobhunter import profiles as _profils
from jobhunter import root as _racine

# The root by MARKER (jobhunter.root), never a hard-coded path: the folders
# moved four times on 20-21/09/2026 and everything that hard-coded a root died
# silence. JOBHUNTER_RACINE surcharge.
ROOT = _racine.racine()
SCRIPTS = _racine.scripts()
sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)  # type: ignore[union-attr]  # console : TextIOWrapper

# Career site readers that only bring back the title: their offer page
# is public, scrape_desc reads it. Closed list — an anti-bot source does not get in.
DESC_SOURCES_PUBLIQUES = (
    "sitemap,talentbrew,avature,oracle,adb,icims,peoplesoft,"
    "service_public,eightfold,workable,gogenerali,sfrss,phenom,csod"
)

# What we read in each step's output to know whether it produced
# something. A pattern that does not match is not an error: it returns None,
# and the step is reported "sans compteur" rather than "zéro".
_COMPTEURS = {
    "scan": re.compile(r"\+(\d+)\s+nouvelles"),
    "vie": re.compile(r"(\d+)\s+offres\s+enrichies"),
    "desc": re.compile(r"(\d+)\s+description\(s\)\s+recuperee"),
    "desc_ats": re.compile(r"===\s*(\d+)/\d+\s+descriptions\s+enregistr"),
    "tri": re.compile(r"supprimees\s*:\s*(\d+)"),
    "dispo": re.compile(r"(\d+)\s+retirees"),
    "reposts": re.compile(r"(\d+)\s+republi"),
    "postings": re.compile(r"(\d+)\s+annonce\(s\)\s+gard"),
    "site": re.compile(r"(\d+)\s+offre\(s\)\s+retrouvee"),
    "docs": re.compile(r"(\d+)\s*/\s*\d+\s+offres\s+[ée]quip"),
    "controle": re.compile(r"(\d+)\s+[àa]\s+revoir"),
}


class _Journal:
    """Writes both to the console and to today's log.

    WHY. Run by the scheduled task, the pipeline has no visible console: on
    2026-09-22, a scan ran for an hour without anyone being able to say whether it
    was progressing, throttled or stuck. The last log dated from 08/09. The log is
    written BY the pipeline, not by a redirection of the launcher: so it also exists
    for a manual run."""

    def __init__(self, console, chemin):
        self.console = console
        self.fichier = open(chemin, "a", encoding="utf-8", buffering=1)

    def write(self, s):
        self.console.write(s)
        self.fichier.write(s)
        return len(s)

    def flush(self):
        self.console.flush()
        self.fichier.flush()


_A_SAUVER = (
    "apply_queue.json",
    "descriptions.json",
    _racine.nom("suivi.json"),
    "companies_seen.json",
)


def sauvegarder(garder=7):
    """Dated copy of the data, BEFORE any step touches it.

    WHY HERE. Until 2026-09-23, git versioned the queue: it was the de facto backup.
    The generated data left git that day (it mixed with the code commits), and this
    snapshot takes over. It is taken before the collection: if a step damages the
    queue, the state from before exists. Seven rolling days, gzip-compressed since
    3.61 (60 MB a day became 16; storage.backups). Returns the folder, or None."""
    import shutil

    from jobhunter.storage import backups

    base = _racine.dans(SCRIPTS, "_sauvegardes")
    cible = base / time.strftime("%Y-%m-%d")
    try:
        # THE FIRST OF THE DAY WINS. A second run the same day (a --rapide
        # trial, a manual rerun) copied the queue already modified over
        # the morning's: on 2026-10-02, the 18:55 trial replaced the state
        # from before the audit that had just removed 1486 offers.
        # A copy cut short (a crash, a full disk) has the queue but not the rest: the
        # missing files are completed, the ones there are never replaced (audit
        # 2026-10-29: the day's tracker was missing and never copied again).
        cible.mkdir(parents=True, exist_ok=True)
        for nom in _A_SAUVER:
            src = SCRIPTS / nom
            if src.exists() and not backups.fichier(cible, nom):
                backups.ecrire(src, cible)
        # The name is an ISO date: alphabetical order is chronological. Only the daily
        # folders count: the copies `<date>_avant_audit` / `_avant_restauration` live
        # here too, and counted among the seven they pushed out the daily ones.
        jours = sorted(
            p for p in base.iterdir() if p.is_dir() and re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.name)
        )
        for vieux in jours[:-garder]:
            shutil.rmtree(vieux, ignore_errors=True)
        # The audit and restore copies follow the day they were taken.
        if len(jours) > garder:
            doyen = jours[-garder].name
            for p in base.iterdir():
                if p.is_dir() and p.name[:10] < doyen and p.name[10:11] == "_":
                    shutil.rmtree(p, ignore_errors=True)
        # The backups made before 3.61, plain: compressed once, as they are met.
        for d in base.iterdir():
            if d.is_dir():
                backups.compresser(d)
        return cible
    except OSError as e:
        print(f"! sauvegarde impossible : {type(e).__name__}: {e}")
        return None


def etape(nom, args, cle, timeout=5400):
    """Runs a step. Returns (code, counter or None, full output).

    THE OUTPUT GOES THROUGH LIVE. The old version captured everything and only
    displayed the last twelve lines AT THE END of the step: during a one-hour
    collection, nothing. Now each line is copied as the step writes it, so the log
    says where we are.

    EXCEEDING THE DURATION KILLS THE STEP, NOT THE PIPELINE. `subprocess.run(
    timeout=...)` raised TimeoutExpired, which nothing caught: the pipeline died
    without a summary. Here a timer kills the step, which returns a non-zero code,
    and the following steps decide for themselves."""
    debut = time.time()
    print(f"\n{'─' * 62}\n▶ {nom}\n  {' '.join(args)}")
    env = dict(os.environ, PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8")
    p = subprocess.Popen(
        [_gele.interpreteur(), *args],
        cwd=str(SCRIPTS),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        # A scheduled run has no console: without this, Popen
        # dies on "[WinError 6] Descripteur non valide".
        stdin=subprocess.DEVNULL,
    )
    tue = threading.Event()

    def _stop():
        tue.set()
        # THE TREE, NOT ONLY THE PROCESS. On 2026-09-28, the step "stopped
        # after 90 min" lasted 136: p.kill() killed Python, but its children
        # (browser) kept the output open and the read below
        # waited for their end. taskkill /T takes the descendants with it.
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(p.pid), "/T", "/F"],
                capture_output=True,
                stdin=subprocess.DEVNULL,
            )
        p.kill()

    minuterie = threading.Timer(timeout, _stop)
    minuterie.start()
    lignes = []
    try:
        for ligne in p.stdout:
            ligne = ligne.rstrip("\n")
            lignes.append(ligne)
            # Minutes elapsed at the start of the line: without them, a 78-min log
            # did not say WHICH source was taking the time.
            print(f"  {(time.time() - debut) / 60:5.1f}' {ligne}")
        p.wait()
    finally:
        minuterie.cancel()
    sortie = "\n".join(lignes)
    m = _COMPTEURS[cle].search(sortie)
    n = int(m.group(1)) if m else None
    mins = (time.time() - debut) / 60
    if tue.is_set():
        print(f"  ! arretee apres {timeout // 60} min (duree maximale depassee)")
    print(
        f"  ⏱ {mins:.1f} min · code {p.returncode} · "
        f"{'compteur ' + str(n) if n is not None else 'sans compteur'}"
    )
    return p.returncode, n, sortie


def dispo_aujourd_hui(a, jour):
    """Does the availability check run today (day: 0 = Monday)?"""
    if a.sans_dispo:
        return False
    return a.dispo or a.rapide or jour == a.dispo_jour


def tous_les_profils(profils):
    """The pipeline of each profile, one after the other, each in its own process.

    Each profile has its own root (queue, lock, logs): the process of a profile runs
    with `JOBHUNTER_RACINE` pointing to it, exactly as when that profile is active.
    Returns the highest exit code (0 if every profile went through).
    """
    principale = _profils.principale()
    codes = []
    for p in profils:
        print(f"\n=== Profil « {p.nom} » ({p.racine}) ===", flush=True)
        env = {
            **os.environ,
            "JOBHUNTER_RACINE": str(p.racine),
            _profils.ENV_PRINCIPALE: str(principale),
        }
        r = subprocess.run(
            [
                _gele.interpreteur(),
                "-m",
                "jobhunter.programs.daily_pipeline",
                *sys.argv[1:],
                "--un-profil",
            ],
            env=env,
            stdin=subprocess.DEVNULL,
        )
        codes.append(r.returncode)
        print(f"=== « {p.nom} » : code {r.returncode} ===", flush=True)
    return max(codes, default=0)


def main():
    _racine.exporter_paquet()  # the steps run `python -m jobhunter...`
    # One run identifier for every step: the offers, scores and yield lines of this
    # morning say they come from it (run_id).
    from jobhunter import run_id as _execution

    print(f"Exécution {_execution.courant()}")
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs", type=int, default=30, help="nombre de dossiers a generer (0 = aucun)")
    ap.add_argument("--sans-docs", action="store_true")
    ap.add_argument("--sans-vie", action="store_true")
    ap.add_argument("--sans-desc", action="store_true")
    ap.add_argument("--sans-tri", action="store_true")
    ap.add_argument("--sans-dispo", action="store_true")
    ap.add_argument(
        "--dispo-jour",
        type=int,
        default=6,
        help="jour du controle de disponibilite, 0 = lundi ... 6 = dimanche (defaut)",
    )
    ap.add_argument("--dispo", action="store_true", help="controle de disponibilite aujourd'hui")
    ap.add_argument("--sans-site", action="store_true")
    # A PIPELINE THAT CANNOT BE TRIED IS NOT VERIFIABLE. `--all` takes
    # more than an hour: impossible to answer "does it work?" without
    # blocking a machine for the afternoon. This mode goes through the THREE steps
    # on a sample — a single source, ten V.I.E, three folders — and
    # gives the same report. It serves to validate the wiring, not to fill the queue.
    ap.add_argument(
        "--rapide", action="store_true", help="essai de bout en bout sur un echantillon (~5 min)"
    )
    ap.add_argument(
        "--un-profil",
        action="store_true",
        help="seulement le profil actif (par defaut : chaque profil, l'un apres l'autre)",
    )
    a = ap.parse_args()

    if not a.un_profil and len(profils := _profils.liste()) > 1:
        return tous_les_profils(profils)

    journaux = SCRIPTS / "_logs"
    journaux.mkdir(exist_ok=True)
    journal = journaux / f"pipeline_{time.strftime('%Y-%m-%d_%H%M')}.log"
    sys.stdout = _Journal(sys.stdout, journal)
    # The engine's timestamped log (jobhunter.log: time, level, module), one
    # per run, next to the console log; the steps inherit it.
    os.environ["JOBHUNTER_JOURNAL"] = str(journal.with_name(journal.stem + "_moteur.log"))

    # The state of this run, for the application (collect_state): a collection that
    # did not finish, or did not even start, must show where the user looks.
    from jobhunter import collect_state as _etat

    if a.rapide:  # a wiring test on a sample is not the morning collection
        return _executer(a, journal)[0]
    _etat.debut(_execution.courant(), str(journal))
    try:
        rc, erreurs = _executer(a, journal)
    except BaseException as e:  # noqa: BLE001 — recorded, then raised again
        _etat.plantage(type(e).__name__)
        raise
    if rc == 3:
        _etat.plantage(erreurs[0])
    else:
        _etat.fin(rc, erreurs)
    return rc


def _executer(a, journal):
    """The run itself. Returns (exit code, names of the steps in error)."""
    titre = f"Pipeline quotidien — {time.strftime('%Y-%m-%d %H:%M')}"
    print(f"╔{'═' * 60}╗")
    print(f"║ {titre:<58} ║")
    print(f"╚{'═' * 60}╝")
    print(f"racine : {ROOT}")
    print(f"journal : {journal}")
    sauv = sauvegarder()
    print(f"sauvegarde : {sauv if sauv else 'ECHEC — voir ci-dessus'}")
    if not sauv:
        alertes_depart = ["la sauvegarde du jour n'a pas pu etre faite"]
    else:
        alertes_depart = []

    bilan, alertes = [], list(alertes_depart)

    # APEC in quick mode: public API, robots.txt without a single Disallow,
    # and it returns a few hundred offers in three minutes. It is the
    # source that replaces Indeed since it closed.
    # THE COLLECTION IN SEVERAL STEPS, each with its maximum duration and ITS merge.
    # In a single one, `--all` only merged at the very end: from 24 to 28/09,
    # four mornings out of five, the collection exceeded 90 min and everything it
    # had gathered — including ~3300 LinkedIn offers — was lost with it. The
    # successful one of the 27th had taken 78 min. No source was blocking: it was the
    # SUM (long LinkedIn, 45 s pauses on the 403s of Indeed and
    # Glassdoor, 200 s on WTJ's 202, eFC at 10 s per posting). Split, a
    # step that is too slow only loses its own offers.
    #   a) large volume, fast APIs; b) sources bounded by their crawl-delay;
    #   c) slow sites, which often refuse — last, so that their pauses
    #   delay nothing else.
    if a.rapide:
        # A sample from sources that answer: APEC, the old sample, refuses every
        # request since 07/10, so a trial collected nothing and every later step ran
        # on an empty queue (measured 2026-10-24 on four new profiles).
        collectes = [
            (
                "1/5  Collecte — LinkedIn 1 page + makesense (essai)",
                ["--linkedin", "--pages", "1", "--makesense"],
                5400,
            )
        ]
    else:
        # FIVE PASSES since 2026-10-02. With three, pass a (ATS + Workday
        # + LinkedIn) and pass c (Talent + Indeed + Glassdoor + APEC + WTJ)
        # both exceeded 60 min on 30/09: ATS 13 min and Workday 19
        # only reached LinkedIn at 33 min; Talent alone took 30 min.
        # LinkedIn now has its own pass; the safe sources (APEC, France
        # Travail) go before those that refuse (Indeed, Glassdoor, WTJ).
        collectes = [
            (
                "1a/5 Collecte — ATS, Workday, V.I.E, FIR",
                ["--ats", "--workday", "--vie", "--fir"],
                1800,
            ),
            ("1b/5 Collecte — LinkedIn", ["--linkedin"], 3600),
            (
                "1c/5 Collecte — eFinancialCareers x9, EURES, Arbeitsagentur, makesense",
                [
                    "--efc",
                    "--efc-sites",
                    "monde",
                    "--efc-limite",
                    "30",
                    "--eures",
                    "--arbeitsagentur",
                    "--makesense",
                ],
                1800,
            ),
            # Talent and Indeed removed on 2026-10-03 (0 offers, 403 since
            # 24/09); APEC and Glassdoor on 2026-10-21 (DataDome, Cloudflare: refused at
            # every collection). Adzuna and Jooble, official APIs, cover their pool.
            (
                "1d/5 Collecte — France Travail, Adzuna, Jooble, USAJOBS, freehire",
                ["--ft", "--adzuna", "--jooble", "--freehire"]
                + (["--usajobs"] if _pays_usajobs() else []),
                2700,
            ),
            ("1e/5 Collecte — WTJ", ["--wtj"], 2400),
            ("1f/5 Collecte — sites carrières des entreprises vues", ["--entreprises-vues"], 2400),
        ]
    ajoutees = 0
    for nom, drapeaux, duree in collectes:
        code, n, _ = etape(nom, ["-m", "jobhunter.sources", *drapeaux], "scan", timeout=duree)
        bilan.append(("collecte " + nom[1] if not a.rapide else "collecte", code, n))
        if code == 3:
            # Lock taken elsewhere: the following steps would fail the same way.
            print("\n! La file est occupee par un autre programme. Arret propre.")
            return 3, ["file occupée par un autre programme"]
        ajoutees += n or 0
    if ajoutees == 0:
        alertes.append("la collecte n'a ajoute AUCUNE offre")

    if not a.sans_vie:
        vie = ["-m", "jobhunter.programs.add_vie", "--completer", "--pause", "0.4"]
        if a.rapide:
            vie += ["--limite", "10"]
        code, n, _ = etape("2/5  V.I.E — fiches detaillees", vie, "vie")
        bilan.append(("v.i.e", code, n))
        if code == 4:
            alertes.append("l'API V.I.E n'a rendu aucune fiche — cle ou reseau")

    # 3 AND 4 BEFORE 5, AND IT IS NOT A DETAIL. The folders are generated for the
    # top of the queue. Without a description, a LinkedIn offer is scored on eight
    # title words, and `tri_file` does not see the years of experience required —
    # on 2026-09-22, this criterion alone set aside 1540 offers, invisible without text.
    # The old order therefore produced CVs for Senior jobs that the sorting
    # would have deleted the next day.
    if not a.sans_desc:
        desc = ["-m", "jobhunter.programs.linkedin_desc"] + (["--limit", "20"] if a.rapide else [])
        code, n, _ = etape("3/5  Descriptions LinkedIn", desc, "desc")
        bilan.append(("descriptions", code, n))
        # 3b. The career sites (2026-10-08): Workday through its API, then the
        # readers that only bring back the title, through their public page. CLOSED
        # list of sources: never Glassdoor nor Indeed, which refuse robots.
        lim = ["--limit", "10"] if a.rapide else []
        code, n, _ = etape(
            "3b/5 Descriptions Workday (API)",
            ["-m", "jobhunter.programs.scrape_desc", "--all", "--api-seul"]
            + (lim or ["--limit", "800"]),
            "desc_ats",
            timeout=1800,
        )
        bilan.append(("desc. workday", code, n))
        code, n, _ = etape(
            "3c/5 Descriptions sites carriere",
            ["-m", "jobhunter.programs.scrape_desc", "--all", "--source", DESC_SOURCES_PUBLIQUES]
            + (lim or ["--limit", "200"]),
            "desc_ats",
            timeout=2400,
        )
        bilan.append(("desc. sites carriere", code, n))

    if not a.sans_tri:
        # In a trial, the sorting INSPECTS without writing: --rapide validates the wiring,
        # it must not purge the real queue.
        tri = ["-m", "jobhunter.scoring.sorting"] + ([] if a.rapide else ["--supprime"])
        code, n, _ = etape("4/5  Tri — seniorite, experience, metier", tri, "tri")
        bilan.append(("tri", code, n))

    # 4a: reposted offers, and the same text under another company (an agency, a
    # job board). Observations for the « Signal » column; nothing is removed. Its
    # history (_offres_vues.json) needs one run a day to date the addresses.
    if not a.sans_tri:
        rep = ["-m", "jobhunter.programs.reposts"] + (["--dry"] if a.rapide else [])
        code, n, _ = etape("4a/5 Republications", rep, "reposts", timeout=15 * 60)
        bilan.append(("republications", code, n))

    # 4a': the posting of each application, kept before the availability check can
    # see it close (jobhunter.postings). The app keeps it at the "postulé" click;
    # this catches the statuses set elsewhere (apply runner, emails).
    pa = ["-m", "jobhunter.programs.archive_postings"] + (["--dry"] if a.rapide else [])
    code, n, _ = etape("4a/5 Annonces des candidatures", pa, "postings", timeout=10 * 60)
    bilan.append(("annonces", code, n))

    # 4b, BEFORE THE FOLDERS: we do not generate a CV for a closed offer.
    # On 2026-10-02, a full audit found one verified offer out of three
    # already closed. Each day only rechecks what has not been seen for
    # seven days. On a rate limit (429), audit_dispo waits and resumes
    # — a single pause here, so as not to delay the folders; it then returns
    # code 4 ("incomplet"), and the next day's run resumes where it
    # stopped. It is not a failure.
    # ONCE A WEEK (on Sunday, --dispo-jour). Every day, the step
    # cost 45 min for nothing: cut by the timer before removing anything
    # at all (08-18/10/2026). It now stops by itself
    # (--duree, 100 min, the best offers first) then removes the closed ones;
    # the timer is now only a safety net.
    if dispo_aujourd_hui(a, time.localtime().tm_wday):
        dispo = ["-m", "jobhunter.programs.availability_audit", "--pauses", "1"]
        dispo += (
            ["--limite", "20"] if a.rapide else ["--supprime", "--sans-copie", "--duree", "100"]
        )
        code, n, _ = etape("4b/5 Disponibilite — offres fermees", dispo, "dispo", timeout=110 * 60)
        if code == 4:
            alertes.append("controle de disponibilite incomplet — reprise la semaine prochaine")
            code = 0
        bilan.append(("disponibilite", code, n))

    # 4c, BEFORE THE FOLDERS: a LinkedIn offer found again on the
    # employer's site (public ATS, Workday) takes its direct link there, to apply
    # without going through LinkedIn. The `_site_final.json` state avoids probing again:
    # a found feed is kept, an absence is only probed again after 30 days.
    # The first pass after Workday was added (2026-10-07) probes everything;
    # cut by the timer, it resumes the next day where it was.
    if not a.sans_site:
        site = ["-m", "jobhunter.programs.final_site", "--fit", "8"] + (
            ["--limite", "10", "--dry"] if a.rapide else []
        )
        code, n, _ = etape(
            "4c/5 Site employeur — ATS publics, Workday", site, "site", timeout=40 * 60
        )
        bilan.append(("site final", code, n))

    if not a.sans_docs and a.docs:
        n_docs = 3 if a.rapide else a.docs
        code, n, _ = etape(
            "5/5  Dossiers — CV et lettres",
            ["-m", "jobhunter.programs.generate_docs", "--top", str(n_docs)],
            "docs",
        )
        bilan.append(("dossiers", code, n))
        # 5b: what will really be sent (readable PDF, one page, contact details, filled
        # template). Read-only; a folder to review must not be sent as is.
        code, n, _ = etape(
            "5b/5 Controle des dossiers",
            ["-m", "jobhunter.programs.check_folders", "--fit", "8"],
            "controle",
            timeout=10 * 60,
        )
        if n:
            alertes.append(f"{n} dossier(s) a revoir avant envoi — python JobHunter.pyw check")
        bilan.append(("controle dossiers", code, n))

    print(f"\n{'═' * 62}\nBILAN")
    for nom, code, n in bilan:
        etat = "ok" if code == 0 else f"code {code}"
        print(f"  {nom:12} {etat:10} {n if n is not None else '—'}")

    try:
        from jobhunter.storage import queue as queue_io

        q = queue_io.charger(descriptions=False)
        fit9 = sum(1 for o in q if (o.get("fit") or 0) >= 9)
        print(f"\n  file : {len(q)} offres · {fit9} a fit >= 9")
    except Exception as e:
        print(f"\n  ! lecture de la file impossible : {type(e).__name__}")

    if alertes:
        print("\n⚠ A REGARDER")
        for x in alertes:
            print(f"  · {x}")
    erreurs = [nom for nom, c, _ in bilan if c not in (0,)]
    return (1 if erreurs else 0), erreurs


def _pays_usajobs() -> bool:
    """USAJOBS in the morning collection: for a profile in the United States."""
    from jobhunter.sources import countries as _pays

    return _pays.source_du_pays("usajobs")


if __name__ == "__main__":
    sys.exit(main())
