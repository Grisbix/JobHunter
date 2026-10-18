"""Arbitrage des doublons entre sources, lexiques et filtre d'entree (job_sources, scrape_jobs).

Une meme annonce parait souvent sur LinkedIn ET sur un vrai site d'emploi ;
LinkedIn est le pire des deux, et la premiere source vue gagnait au hasard de
l'ordre des scans. Converti depuis Scripts/test_sources.py.
"""

import json
import re

import pytest

from jobhunter import sources as J
from jobhunter.programmes.scrape_jobs import matches_esg_finance, offre_retenue
from jobhunter.sources import en_france, rang_source

LI = "https://fr.linkedin.com/jobs/view/x-4"
WTJ = "https://www.welcometothejungle.com/fr/companies/o/jobs/x"
IND = "https://fr.indeed.com/viewjob?jk=x"
ATS = "https://boards.greenhouse.io/o/jobs/1"


# ── classement des sources ─────────────────────────────────────────────────────
@pytest.mark.parametrize(
    ("url", "attendu"),
    [
        ("https://fr.linkedin.com/jobs/view/consultant-esg-at-oderis-4", 0),
        ("https://www.linkedin.com/jobs/view/123", 0),
        ("https://fr.indeed.com/viewjob?jk=abc", 1),
        ("https://fr.talent.com/view?id=x", 1),
        ("https://www.welcometothejungle.com/fr/companies/oderis/jobs/x", 2),
        ("https://www.apec.fr/candidat/emploi/1234", 2),
        ("https://mon-vie-via.businessfrance.fr/offres/123", 2),
        ("https://boards.greenhouse.io/sweep/jobs/123", 3),
        ("https://jobs.lever.co/greenly/abc", 3),
        ("https://careers.axa.com/careers-home/jobs/2446", 3),
        ("", -1),
        (None, -1),
    ],
    ids=[
        "LinkedIn",
        "LinkedIn www",
        "Indeed",
        "Talent",
        "WTJ",
        "APEC",
        "Business France",
        "Greenhouse",
        "Lever",
        "site entreprise",
        "vide",
        "None",
    ],
)
def test_rang_source(url, attendu):
    assert rang_source(url) == attendu


@pytest.mark.parametrize(
    ("meilleure", "pire"),
    [(WTJ, LI), (IND, LI), (WTJ, IND), (ATS, WTJ)],
    ids=["WTJ > LinkedIn", "Indeed > LinkedIn", "WTJ > Indeed", "ATS > WTJ"],
)
def test_ordre_des_sources(meilleure, pire):
    assert rang_source(meilleure) > rang_source(pire)


# ── promotion reelle dans merge_into_queue ─────────────────────────────────────
@pytest.fixture
def file_vide(tmp_path, monkeypatch):
    """File jetable ; les fusions ne lisent pas les rejets reels du tri."""
    q = tmp_path / "q.json"
    q.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(J, "QUEUE", q)
    monkeypatch.setattr(J, "REJETS_TRI", tmp_path / "rejets.json")
    return q


def lire(q):
    return json.loads(q.read_text(encoding="utf-8"))


def fusion(lot):
    return J.merge_into_queue(lot, dry=False)


def oderis(url, **k):
    return J._mk("Consultant(e) Junior ESG", url, "Oderis Consulting", **k)


@pytest.fixture
def promue_par_wtj(file_vide):
    file_vide.write_text(
        json.dumps(
            [
                {
                    "entreprise": "Oderis Consulting",
                    "poste": "Consultant(e) Junior ESG",
                    "domaine": "ESG_Finance_Durable",
                    "statut": "Scan 2026-09-03",
                    "url": LI,
                    "canal": "manuel",
                    "site_kind": "board",
                    "fit": 8,
                    "description": "",
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    r = fusion([oderis(WTJ, source="welcometothejungle.com")])
    return file_vide, r, lire(file_vide)


def test_aucun_doublon_ajoute(promue_par_wtj):
    assert len(promue_par_wtj[2]) == 1


def test_un_lien_promu(promue_par_wtj):
    assert promue_par_wtj[1]["promus"] == 1


def test_l_url_est_celle_de_wtj(promue_par_wtj):
    assert promue_par_wtj[2][0]["url"] == WTJ


def test_canal_manuel_pour_un_board(promue_par_wtj):
    assert promue_par_wtj[2][0]["canal"] == "manuel"


@pytest.fixture
def linkedin_ensuite(promue_par_wtj):
    """LinkedIn ne doit JAMAIS ecraser une meilleure source."""
    r = fusion([oderis(LI)])
    return r, lire(promue_par_wtj[0])


def test_linkedin_ne_retrograde_pas_le_lien(linkedin_ensuite):
    assert linkedin_ensuite[1][0]["url"] == WTJ


def test_aucune_promotion_a_contresens(linkedin_ensuite):
    assert linkedin_ensuite[0]["promus"] == 0


@pytest.fixture
def ats_ensuite(linkedin_ensuite, promue_par_wtj):
    fusion([oderis(ATS)])
    return lire(promue_par_wtj[0])


def test_l_ats_promeut_par_dessus_wtj(ats_ensuite):
    assert ats_ensuite[0]["url"] == ATS


def test_canal_auto_pour_une_entreprise(ats_ensuite):
    assert ats_ensuite[0]["canal"] == "auto"


# ── enrichissement DANS LE MEME lot ────────────────────────────────────────────
# `--all` enchaine les sources : la meme annonce arrive plusieurs fois dans UN
# appel. La promotion et la description s'ecrivaient sur un dict orphelin.
LOT = [
    J._mk("Analyste ESG", LI, "Amundi", "Paris, France", source="linkedin-search"),
    J._mk(
        "Analyste ESG",
        ATS,
        "Amundi",
        "Paris, France",
        source="greenhouse:amundi",
        description="Analyse extra-financière, SFDR, taxonomie. Bac+5 finance durable.",
    ),
]


@pytest.fixture
def meme_lot(file_vide):
    r = fusion([dict(o) for o in LOT])
    return r, lire(file_vide)


def test_une_seule_ligne_creee(meme_lot):
    assert len(meme_lot[1]) == 1


def test_lien_ats_remplace_linkedin(meme_lot):
    assert meme_lot[1][0]["url"] == ATS


def test_description_dans_la_file(meme_lot):
    assert meme_lot[1][0].get("description", "").strip()


def test_promotion_comptee_une_fois(meme_lot):
    assert meme_lot[0]["promus"] == 1


@pytest.fixture
def ordre_inverse(file_vide):
    r = fusion([dict(o) for o in reversed(LOT)])
    return r, lire(file_vide)


def test_ordre_inverse_le_lien_ats_tient(ordre_inverse):
    assert ordre_inverse[1][0]["url"] == ATS


def test_ordre_inverse_aucune_retrogradation(ordre_inverse):
    assert ordre_inverse[0]["promus"] == 0


# ── les deux listes de mots-cles ne divergent pas ──────────────────────────────
# title_ok = lexique LARGE et mot METIER : un mot present dans l'un et absent de
# l'autre fait jeter l'offre en silence (« CSRD » etait demande a LinkedIn puis jete).
@pytest.mark.parametrize(
    "mot",
    [
        "esg",
        "csr",
        "csrd",
        "sfdr",
        "taxonomie",
        "hse",
        "qhse",
        "e&s",
        "extra-financier",
        "rse",
        "biodiversit",
        "impact",
        "transition",
        "environnement",
        "environmental",
        "durabilit",
        "decarbonation",
        "climat",
        "carbon",
        "green",
        "quant",
        "risk",
        "risque",
        "credit",
        "invest",
        "audit",
        "actuari",
        "treasury",
        "tresorerie",
        "m&a",
        "portfolio",
        "asset",
        "analyste",
        "analytic",
        "consultant",
        "conseil",
        "economiste",
        "comptab",
        "controlling",
    ],
)
def test_mot_passe_le_lexique_large(mot):
    assert matches_esg_finance(mot)


# ── le filtre d'entree de scrape_jobs ──────────────────────────────────────────
# « h/f » est dans le lexique large : seul, il acceptait boucher, plombier, serveur.
@pytest.mark.parametrize(
    ("titre", "attendu"),
    [
        ("Plombier chauffagiste H/F", False),
        ("Serveur en restauration H/F", False),
        ("Chef de rayon boucherie H/F", False),
        ("Assistant RH (H/F)", False),
        ("Commercial sédentaire H/F", False),
        ("Backend Developer H/F", False),
        ("Talent Acquisition Manager", False),
        ("Designer UX Senior", False),
        ("Analyste ESG junior H/F", True),
        ("Sustainable Finance Analyst", True),
        ("CSRD Reporting Manager", True),
        ("Graduate Programme Finance", True),
        ("Contrôleur de gestion H/F", True),
        ("Chargé de mission environnement", True),
        ("VIE Transition Énergétique Corporate", True),
        ("AI Software Engineer", True),
    ],
)
def test_offre_retenue(titre, attendu):
    assert offre_retenue(titre) is attendu


# ── le garde-fou \b couvre TOUS les motifs ─────────────────────────────────────
def test_au_moins_25_motifs_compiles():
    # les motifs vivent dans les sous-modules de jobhunter.sources (phase 3.4)
    assert len(J._motifs()) >= 25


@pytest.mark.parametrize(
    "nom", ["_DOMAIN_RX", "_HARD_NEG_RX", "_AI_RX", "_NEG_TITLE_RX", "_RX_ALT"]
)
@pytest.mark.parametrize(
    "corrompu",
    [re.compile("(\x08ia\x08)"), re.compile("(" + chr(92) * 2 + "bia)")],
    ids=["backspace", "antislash"],
)
def test_motif_corrompu_detecte(monkeypatch, nom, corrompu):
    monkeypatch.setattr(J, nom, corrompu)
    with pytest.raises(AssertionError):
        J._verifier_motifs()


# ── par defaut, le monde entier entre ──────────────────────────────────────────
def test_monde_actif_par_defaut():
    assert J.MONDE is True


@pytest.mark.parametrize(
    "lieu",
    [
        "Singapore, Singapore",
        "Dublin, Leinster, Ireland",
        "London",
        "Luxembourg",
        "Bruxelles",
        "Zurich",
    ],
)
def test_le_monde_entre(lieu):
    assert en_france(lieu)


# ── avec --france, le filtre trie toujours juste ───────────────────────────────
# Un flux ATS porte le nom de la societe, pas son pays : seul le LIEU tranche.
@pytest.mark.parametrize(
    ("lieu", "attendu"),
    [
        ("Paris", True),
        ("Bordeaux", True),
        ("", True),
        ("Remote", True),
        ("All France (remote)", True),
        ("fr", True),
        ("PARIS 08, Île-de-France, France", True),
        ("Strasbourg", True),
        ("33", True),
        ("Sud-Ouest", True),
        ("Berlin", False),
        ("Dublin, Leinster, Ireland", False),
        ("Hanoi", False),
        ("Tokyo, JP", False),
        ("London", False),
        ("Frankfurt am Main, Hessen, Deutschland", False),
        ("de", False),
        ("Casablanca", False),
        # passaient a tort : aucun code d'Etat americain, et l'inconnu etait accepte
        ("Reston, VA", False),
        ("Aurora, CO", False),
        ("Crane, IN", False),
        ("Mexico City", False),
    ],
)
def test_filtre_france(monkeypatch, lieu, attendu):
    monkeypatch.setattr(J, "MONDE", False)
    assert en_france(lieu) is attendu


def test_mode_mondial_retabli_apres_le_test():
    assert J.MONDE is True
