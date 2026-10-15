#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pipeline_quotidien.py — Le scan du matin, en un seul point d'entree.

CE QU'IL REMPLACE, et pourquoi. Trois mecanismes etaient censes alimenter la
file. Mesure du 21/09/2026 : aucun des trois n'apportait une offre.

  Tache Windows `JobSearch_Daily_Scrape`
      -File ...\\Recherche_emploi_ESG_Finance_ORGANISE\\Scripts\\run_pipeline.ps1
      Ce fichier n'existe plus. Resultat 0xFFFD0000 chaque matin a 8h00.

  hermes/scripts/run_full_job_pipeline.sh
      Scrape Indeed via curl_cffi impersonate='chrome124'. La requete PASSE
      (HTTP 200, 794 Ko) mais la page ne contient plus une seule carte :
      `td.resultContent` = 0, `data-jk=` = 0, ni captcha ni blocage. Le
      parseur vise un balisage qu'Indeed n'utilise plus. Le script affiche
      « Scraped 0 jobs », fusionne zero offre, et se termine sur
      « ✅ Pipeline termine ». Un echec qui se declare reussi.

  hermes/scripts/run_job_search_pipeline.sh
      Orchestre trois wrappers tiers. Dernier run : trois `returncode=0`,
      trois « wrapper executed », dont un « placeholder summary ». Rien
      n'entre dans apply_queue.json.

AUCUN DES TROIS NE TOUCHAIT LES V.I.E. Les 274 de la file venaient de
lancements manuels.

CE PIPELINE-CI appelle le code du projet, celui qui est teste :

    1. job_sources.py, en trois     a) ATS, Workday, LinkedIn, V.I.E, FIR
       passes fusionnees chacune    b) eFC x9 sites, EURES
                                    c) Talent, Indeed, Glassdoor, APEC, WTJ, FT
    2. ajoute_vie.py --completer   la route DETAIL des V.I.E : indemnite,
                                   contact, description — que la LISTE n'a pas
    3. linkedin_desc.py            le texte des offres LinkedIn du jour, qui
                                   arrivent avec leur seul intitule
       scrape_desc.py (3b, 3c)     idem pour Workday (API) et les sites carriere
                                   lus sans description (pages publiques)
    4. tri_file.py --supprime      seniorite, experience exigee, metier — les
                                   candidatures de suivi.json sont epargnees
    5. generate_docs.py --top N    CV et lettre pour le haut de la file

Chaque lancement ecrit son journal dans _logs/pipeline_<date>_<heure>.log.

LES ETAPES SONT SEQUENTIELLES, et ce n'est pas un choix de style :
`job_sources.main()` prend le verrou de la file a son demarrage et le garde
pour tout le scan. Deux etapes en parallele, et la seconde sort en code 3.

UN ZERO N'EST PAS UNE BONNE NOUVELLE. « Rien a prendre » et « refus d'entree »
rendent le meme chiffre, et c'est ainsi qu'un scan entierement bride passe
pour une journee calme — apres quoi on le relance, ce qu'il ne faut surtout
pas faire face a un quota. Ce programme releve donc les compteurs de chaque
etape et le dit quand une etape n'a rien rendu.

Run :
  python pipeline_quotidien.py
  python pipeline_quotidien.py --docs 50
  python pipeline_quotidien.py --sans-docs
"""
import argparse
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path


def _racine():
    """La racine du projet, par MARQUEUR. Jamais un chemin en dur : les
    dossiers ont bouge quatre fois les 20-21/09/2026 et tout ce qui codait
    une racine est mort en silence. JOB_SEARCH_ROOT surcharge."""
    for cand in (os.environ.get("JOB_SEARCH_ROOT", ""),
                 *[str(p) for p in Path(__file__).resolve().parents]):
        if cand and (Path(cand) / "Scripts" / "apply_queue.json").exists():
            return Path(cand)
    return Path(__file__).resolve().parent.parent


ROOT = _racine()
SCRIPTS = ROOT / "Scripts"
sys.path.insert(0, str(SCRIPTS))
sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

# Lecteurs de sites carriere qui ne rapportent que le titre : leur page d'offre
# est publique, scrape_desc la lit. Liste fermee — une source anti-bot n'y entre pas.
DESC_SOURCES_PUBLIQUES = ("sitemap,talentbrew,avature,oracle,adb,icims,peoplesoft,"
                          "service_public,eightfold,workable,gogenerali,sfrss,phenom,csod")

# Ce qu'on releve dans la sortie de chaque etape pour savoir si elle a produit
# quelque chose. Un motif qui ne matche pas n'est pas une erreur : il rend None,
# et l'etape est signalee « sans compteur » plutot que « zero ».
_COMPTEURS = {
    "scan": re.compile(r"\+(\d+)\s+nouvelles"),
    "vie": re.compile(r"(\d+)\s+offres\s+enrichies"),
    "desc": re.compile(r"(\d+)\s+description\(s\)\s+recuperee"),
    "desc_ats": re.compile(r"===\s*(\d+)/\d+\s+descriptions\s+enregistr"),
    "tri": re.compile(r"supprimees\s*:\s*(\d+)"),
    "dispo": re.compile(r"(\d+)\s+retirees"),
    "site": re.compile(r"(\d+)\s+offre\(s\)\s+retrouvee"),
    "docs": re.compile(r"(\d+)\s*/\s*\d+\s+offres\s+[ée]quip"),
}


class _Journal:
    """Ecrit a la fois sur la console et dans le journal du jour.

    POURQUOI. Lance par la tache planifiee, le pipeline n'a pas de console
    visible : le 2026-09-22, un scan a tourne une heure sans que personne
    puisse dire s'il avancait, s'il etait bride ou s'il etait bloque. Le dernier
    journal datait du 08/09. Le journal est ecrit PAR le pipeline, pas par une
    redirection du lanceur : il existe donc aussi pour un lancement a la main."""

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


_A_SAUVER = ("apply_queue.json", "descriptions.json", "suivi.json")


def sauvegarder(garder=7):
    """Copie datee des donnees, AVANT que la moindre etape y touche.

    POURQUOI ICI. Jusqu'au 2026-09-23, git versionnait la file : c'etait la
    sauvegarde de fait. Les donnees generees sont sorties de git ce jour-la
    (elles se melaient aux commits de code), et cet instantane prend le relais.
    Il est pris avant la collecte : si une etape abime la file, l'etat d'avant
    existe. Sept jours glissants, ~35 Mo chacun. Rend le dossier, ou None."""
    import shutil
    base = SCRIPTS / "_sauvegardes"
    cible = base / time.strftime("%Y-%m-%d")
    try:
        # LA PREMIERE DU JOUR GAGNE. Un second lancement le meme jour (essai
        # --rapide, relance a la main) recopiait la file deja modifiee par-dessus
        # celle du matin : le 2026-10-02, l'essai de 18h55 a remplace l'etat
        # d'avant l'audit qui venait de retirer 1486 offres.
        if (cible / "apply_queue.json").exists():
            return cible
        cible.mkdir(parents=True, exist_ok=True)
        for nom in _A_SAUVER:
            src = SCRIPTS / nom
            if src.exists():
                shutil.copy2(src, cible / nom)
        # Le nom est une date ISO : l'ordre alphabetique est chronologique.
        for vieux in sorted(p for p in base.iterdir() if p.is_dir())[:-garder]:
            shutil.rmtree(vieux, ignore_errors=True)
        return cible
    except OSError as e:
        print(f"! sauvegarde impossible : {type(e).__name__}: {e}")
        return None


def etape(nom, args, cle, timeout=5400):
    """Lance une etape. Rend (code, compteur ou None, sortie complete).

    LA SORTIE PASSE EN DIRECT. L'ancienne version capturait tout et n'affichait
    que les douze dernieres lignes A LA FIN de l'etape : pendant une collecte
    d'une heure, rien. Maintenant chaque ligne est recopiee au moment ou
    l'etape l'ecrit, donc le journal dit ou l'on en est.

    LE DEPASSEMENT DE DUREE TUE L'ETAPE, PAS LE PIPELINE. `subprocess.run(
    timeout=...)` levait TimeoutExpired, que rien n'attrapait : le pipeline
    mourait sans bilan. Ici une minuterie tue l'etape, qui rend un code non nul,
    et les etapes suivantes decident d'elles-memes."""
    debut = time.time()
    print(f"\n{'─' * 62}\n▶ {nom}\n  {' '.join(args)}")
    env = dict(os.environ, PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8")
    p = subprocess.Popen([sys.executable, *args], cwd=str(SCRIPTS),
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, encoding="utf-8", errors="replace", env=env,
                         # Un run planifie n'a pas de console : sans ceci, Popen
                         # meurt sur « [WinError 6] Descripteur non valide ».
                         stdin=subprocess.DEVNULL)
    tue = threading.Event()

    def _stop():
        tue.set()
        # L'ARBRE, PAS SEULEMENT LE PROCESSUS. Le 2026-09-28, l'etape « arretee
        # apres 90 min » en a dure 136 : p.kill() tuait Python, mais ses enfants
        # (navigateur) gardaient la sortie ouverte et la lecture ci-dessous
        # attendait leur fin. taskkill /T emporte les descendants.
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(p.pid), "/T", "/F"],
                           capture_output=True, stdin=subprocess.DEVNULL)
        p.kill()

    minuterie = threading.Timer(timeout, _stop)
    minuterie.start()
    lignes = []
    try:
        for ligne in p.stdout:
            ligne = ligne.rstrip("\n")
            lignes.append(ligne)
            # Minutes ecoulees en tete de ligne : sans elles, un journal de 78 min
            # ne disait pas QUELLE source prenait le temps.
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
    print(f"  ⏱ {mins:.1f} min · code {p.returncode} · "
          f"{'compteur ' + str(n) if n is not None else 'sans compteur'}")
    return p.returncode, n, sortie


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs", type=int, default=30,
                    help="nombre de dossiers a generer (0 = aucun)")
    ap.add_argument("--sans-docs", action="store_true")
    ap.add_argument("--sans-vie", action="store_true")
    ap.add_argument("--sans-desc", action="store_true")
    ap.add_argument("--sans-tri", action="store_true")
    ap.add_argument("--sans-dispo", action="store_true")
    ap.add_argument("--sans-site", action="store_true")
    # UN PIPELINE QU'ON NE PEUT PAS ESSAYER N'EST PAS VERIFIABLE. `--all` prend
    # plus d'une heure : impossible de repondre « est-ce que ca marche ? » sans
    # bloquer une machine pour l'apres-midi. Ce mode traverse les TROIS etapes
    # sur un echantillon — une seule source, dix V.I.E, trois dossiers — et
    # rend le meme rapport. Il sert a valider le cablage, pas a remplir la file.
    ap.add_argument("--rapide", action="store_true",
                    help="essai de bout en bout sur un echantillon (~5 min)")
    a = ap.parse_args()

    journaux = SCRIPTS / "_logs"
    journaux.mkdir(exist_ok=True)
    journal = journaux / f"pipeline_{time.strftime('%Y-%m-%d_%H%M')}.log"
    sys.stdout = _Journal(sys.stdout, journal)

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

    # L'APEC en mode rapide : API publique, robots.txt sans un seul Disallow,
    # et elle rend quelques centaines d'offres en trois minutes. C'est la
    # source qui remplace Indeed depuis qu'il est ferme.
    # LA COLLECTE EN TROIS ETAPES, chacune avec sa duree maximale et SA fusion.
    # En une seule, `--all` ne fusionnait qu'a la toute fin : du 24 au 28/09,
    # quatre matins sur cinq, la collecte a depasse 90 min et tout ce qu'elle
    # avait ramasse — dont ~3300 offres LinkedIn — a ete perdu avec elle. La
    # reussie du 27 avait pris 78 min. Aucune source ne bloquait : c'etait la
    # SOMME (LinkedIn long, pauses de 45 s sur les 403 d'Indeed et de
    # Glassdoor, 200 s sur le 202 de WTJ, eFC a 10 s la fiche). Decoupee, une
    # etape trop lente ne perd plus que ses propres offres.
    #   a) gros volume, APIs rapides ; b) sources bornees par leur crawl-delay ;
    #   c) sites lents, qui refusent souvent — en dernier, pour que leurs pauses
    #   ne retardent rien d'autre.
    if a.rapide:
        collectes = [("1/5  Collecte — APEC seule (essai)", ["--apec"], 5400)]
    else:
        # CINQ PASSES depuis le 2026-10-02. En trois, la passe a (ATS + Workday
        # + LinkedIn) et la passe c (Talent + Indeed + Glassdoor + APEC + WTJ)
        # ont toutes deux depasse 60 min le 30/09 : ATS 13 min et Workday 19
        # n'atteignaient LinkedIn qu'a 33 min ; Talent prenait 30 min a lui seul.
        # LinkedIn a desormais sa passe ; les sources sures (APEC, France
        # Travail) passent avant celles qui refusent (Indeed, Glassdoor, WTJ).
        collectes = [
            ("1a/5 Collecte — ATS, Workday, V.I.E, FIR",
             ["--ats", "--workday", "--vie", "--fir"], 1800),
            ("1b/5 Collecte — LinkedIn",
             ["--linkedin"], 3600),
            ("1c/5 Collecte — eFinancialCareers x9, EURES",
             ["--efc", "--efc-sites", "monde", "--efc-limite", "30", "--eures"], 1800),
            # Talent et Indeed retires le 2026-10-03 (0 offre, 403 depuis le
            # 24/09) ; Adzuna et Jooble, API officielles, couvrent leur vivier.
            ("1d/5 Collecte — APEC, France Travail, Adzuna, Jooble",
             ["--apec", "--ft", "--adzuna", "--jooble"], 2700),
            ("1e/5 Collecte — Glassdoor, WTJ",
             ["--glassdoor", "--wtj"], 2400),
        ]
    ajoutees = 0
    for nom, drapeaux, duree in collectes:
        code, n, _ = etape(nom, ["job_sources.py", *drapeaux], "scan", timeout=duree)
        bilan.append(("collecte " + nom[1] if not a.rapide else "collecte", code, n))
        if code == 3:
            # Verrou pris ailleurs : les etapes suivantes echoueraient pareil.
            print("\n! La file est occupee par un autre programme. Arret propre.")
            return 3
        ajoutees += n or 0
    if ajoutees == 0:
        alertes.append("la collecte n'a ajoute AUCUNE offre")

    if not a.sans_vie:
        vie = ["ajoute_vie.py", "--completer", "--pause", "0.4"]
        if a.rapide:
            vie += ["--limite", "10"]
        code, n, _ = etape("2/5  V.I.E — fiches detaillees", vie, "vie")
        bilan.append(("v.i.e", code, n))
        if code == 4:
            alertes.append("l'API V.I.E n'a rendu aucune fiche — cle ou reseau")

    # 3 ET 4 AVANT 5, ET CE N'EST PAS UN DETAIL. Les dossiers se generent pour le
    # haut de la file. Sans description, une offre LinkedIn est notee sur huit
    # mots de titre, et `tri_file` ne voit pas les annees d'experience exigees —
    # le 2026-09-22, ce seul critere a ecarte 1540 offres, invisibles sans texte.
    # L'ancien ordre produisait donc des CV pour des postes Senior que le tri
    # aurait supprimes le lendemain.
    if not a.sans_desc:
        desc = ["linkedin_desc.py"] + (["--limit", "20"] if a.rapide else [])
        code, n, _ = etape("3/5  Descriptions LinkedIn", desc, "desc")
        bilan.append(("descriptions", code, n))
        # 3b. Les sites carriere (2026-10-08) : Workday par son API, puis les
        # lecteurs qui ne rapportent que le titre, par leur page publique. Liste
        # FERMEE de sources : jamais Glassdoor ni Indeed, qui refusent les robots.
        lim = ["--limit", "10"] if a.rapide else []
        code, n, _ = etape("3b/5 Descriptions Workday (API)",
                           ["scrape_desc.py", "--all", "--api-seul"] + (lim or ["--limit", "800"]),
                           "desc_ats", timeout=1800)
        bilan.append(("desc. workday", code, n))
        code, n, _ = etape("3c/5 Descriptions sites carriere",
                           ["scrape_desc.py", "--all", "--source", DESC_SOURCES_PUBLIQUES]
                           + (lim or ["--limit", "200"]), "desc_ats", timeout=2400)
        bilan.append(("desc. sites carriere", code, n))

    if not a.sans_tri:
        # En essai, le tri INSPECTE sans ecrire : --rapide valide le cablage,
        # il ne doit pas purger la vraie file.
        tri = ["tri_file.py"] + ([] if a.rapide else ["--supprime"])
        code, n, _ = etape("4/5  Tri — seniorite, experience, metier", tri, "tri")
        bilan.append(("tri", code, n))

    # 4b, AVANT LES DOSSIERS : on ne genere pas un CV pour une offre fermee.
    # Le 2026-10-02, un audit complet a trouve une offre verifiee sur trois
    # deja fermee. Chaque jour ne recontrole que ce qui n'a pas ete vu depuis
    # sept jours. Sur une limite de debit (429), audit_dispo attend et reprend
    # — une seule pause ici, pour ne pas retarder les dossiers ; il rend alors
    # le code 4 (« incomplet »), et la relance du lendemain reprend la ou il
    # s'est arrete. Ce n'est pas une panne.
    if not a.sans_dispo:
        dispo = ["audit_dispo.py", "--pauses", "1"]
        # 900 controles au plus (~40 min a 2,6 s), les meilleures offres d'abord :
        # le reste passe le lendemain, plutot que d'etre coupe par la minuterie.
        dispo += ["--limite", "20"] if a.rapide else ["--supprime", "--sans-copie",
                                                       "--limite", "900"]
        code, n, _ = etape("4b/5 Disponibilite — offres fermees", dispo, "dispo",
                           timeout=45 * 60)
        if code == 4:
            alertes.append("audit de disponibilite incomplet (limite de debit) — reprise demain")
            code = 0
        bilan.append(("disponibilite", code, n))

    # 4c, AVANT LES DOSSIERS : une offre LinkedIn retrouvee sur le site de
    # l'employeur (ATS publics, Workday) y prend son lien direct, pour postuler
    # sans passer par LinkedIn. L'etat `_site_final.json` evite de resonder :
    # un flux trouve est garde, une absence n'est resondee qu'apres 30 jours.
    # Le premier passage apres l'ajout de Workday (2026-10-07) sonde tout ;
    # coupe par la minuterie, il reprend le lendemain ou il en etait.
    if not a.sans_site:
        site = ["site_final.py", "--fit", "8"] + (["--limite", "10", "--dry"] if a.rapide else [])
        code, n, _ = etape("4c/5 Site employeur — ATS publics, Workday", site, "site",
                           timeout=40 * 60)
        bilan.append(("site final", code, n))

    if not a.sans_docs and a.docs:
        n_docs = 3 if a.rapide else a.docs
        code, n, _ = etape("5/5  Dossiers — CV et lettres",
                           ["generate_docs.py", "--top", str(n_docs)], "docs")
        bilan.append(("dossiers", code, n))

    print(f"\n{'═' * 62}\nBILAN")
    for nom, code, n in bilan:
        etat = "ok" if code == 0 else f"code {code}"
        print(f"  {nom:12} {etat:10} {n if n is not None else '—'}")

    try:
        import queue_io
        q = queue_io.charger(descriptions=False)
        fit9 = sum(1 for o in q if (o.get("fit") or 0) >= 9)
        print(f"\n  file : {len(q)} offres · {fit9} a fit >= 9")
    except Exception as e:
        print(f"\n  ! lecture de la file impossible : {type(e).__name__}")

    if alertes:
        print("\n⚠ A REGARDER")
        for x in alertes:
            print(f"  · {x}")
    return 1 if any(c not in (0,) for _, c, _ in bilan) else 0


if __name__ == "__main__":
    sys.exit(main())
