"""Audit de disponibilite (audit_dispo), sans reseau.

Une limite de debit s'attend et reprend, un refus d'entree s'arrete ; APEC et WTJ
retrouvent l'offre par leur propre source ; une offre suivie n'est jamais retiree ;
choix et ordre des cibles ; la sauvegarde du jour n'est jamais ecrasee.
Converti depuis Scripts/test_audit_dispo.py, qui remplacait httpx.Client et
time.sleep pour tout le processus.
"""

import datetime

import httpx
import pytest

from jobhunter import sources as job_sources
from jobhunter.programmes import audit_dispo as a
from jobhunter.programmes import linkedin_desc as ld
from jobhunter.programmes import pipeline_quotidien as pq

JOUR = "2026-10-02"


class R:
    def __init__(self, code, txt=""):
        self.status_code, self.text, self.headers = code, txt, {}


OUVERTE = R(200, "x" * 500)
FERMEE = R(200, "closed-job" + "x" * 500)


def offre(i, url=None, poste="P", **k):
    o = {
        "entreprise": f"E{i}",
        "poste": poste,
        "url": url or f"https://www.linkedin.com/jobs/view/12345{i}0",
    }
    o.update(k)
    return o


@pytest.fixture
def pauses(monkeypatch):
    p = []
    monkeypatch.setattr(a.time, "sleep", p.append)
    monkeypatch.setattr(a, "sauver_etat", lambda e: None)
    return p


@pytest.fixture
def scenario(monkeypatch):
    """Le client httpx d'audit_dispo rend les reponses donnees, dans l'ordre."""

    def jouer(reponses):
        it = iter(reponses)

        class Client:
            def __init__(self, **k):
                pass

            def get(self, url):
                return next(it)

        monkeypatch.setattr(httpx, "Client", Client)

    return jouer


# ── limite de debit : attendre, reprendre ; refus : s'arreter ──────────────────
@pytest.fixture
def trois_429(pauses, scenario):
    etat = {}
    scenario([OUVERTE, R(429), R(429), R(429), OUVERTE, FERMEE])
    fini = a.verifier([offre(i) for i in range(3)], etat, 4, JOUR)
    return fini, etat, pauses


def test_429_reprend_et_finit(trois_429):
    assert trois_429[0]


def test_429_pause_longue_de_15_min(trois_429):
    assert 900 in trois_429[2]


def test_429_aucune_offre_perdue(trois_429):
    assert [v[0] for v in trois_429[1].values()] == ["OK", "OK", "FERMEE"]


@pytest.fixture
def sans_fin(pauses, scenario):
    scenario([OUVERTE] + [R(429)] * 50)
    return a.verifier([offre(i) for i in range(3)], {}, 2, JOUR), pauses


def test_429_sans_fin_rend_la_main(sans_fin):
    assert not sans_fin[0]


def test_429_sans_fin_pauses_15_puis_30_min(sans_fin):
    assert [s for s in sans_fin[1] if s > 30] == [900, 1800]


@pytest.fixture
def refus(pauses, scenario):
    scenario([R(403)] * 5)
    return a.verifier([offre(i) for i in range(3)], {}, 4, JOUR), pauses


def test_403_arret_immediat(refus):
    assert not refus[0]


def test_403_aucune_pause(refus):
    assert not [s for s in refus[1] if s > 1]


# ── APEC : retrouver l'offre par la recherche qui l'a trouvee ──────────────────
def apec(num, poste="Analyste ESG"):
    url = f"https://www.apec.fr/candidat/recherche-emploi.html/emploi/detail-offre/{num}"
    return offre(num, url=url, poste=poste)


def file_et_etat(offres):
    return offres, {a.queue_io.oid(o): [None, "HTTP 403", o["url"], JOUR] for o in offres}


@pytest.fixture
def apec_statuts(monkeypatch):
    reponses = {
        "Poste vivant": ([{"numeroOffre": "999W"}, {"numeroOffre": "111W"}], 2),
        "Poste ferme": ([{"numeroOffre": "999W"}], 1),
        "Analyste": ([{"numeroOffre": f"{i}X"} for i in range(50)], 400),
    }
    monkeypatch.setattr(job_sources, "_apec_page", lambda mot, debut: reponses[mot])
    monkeypatch.setattr(job_sources, "APEC_PAUSE", 0)
    q, etat = file_et_etat(
        [apec("111W", "Poste vivant"), apec("222W", "Poste ferme"), apec("333W", "Analyste")]
    )
    a.par_la_source(q, etat, JOUR, "2026-09-25")
    return {o["poste"]: etat[a.queue_io.oid(o)][0] for o in q}


def test_apec_revue_dans_la_recherche(apec_statuts):
    assert apec_statuts["Poste vivant"] == "OK"


def test_apec_absente_d_une_recherche_complete(apec_statuts):
    assert apec_statuts["Poste ferme"] == "FERMEE_SOURCE"


def test_apec_absente_d_une_recherche_tronquee_indecis(apec_statuts):
    assert apec_statuts["Analyste"] is None


@pytest.fixture
def apec_refus(monkeypatch):
    appels = []

    def refus(mot, debut):
        appels.append(mot)
        return None, 0

    monkeypatch.setattr(job_sources, "_apec_page", refus)
    monkeypatch.setattr(job_sources, "APEC_PAUSE", 0)
    q, etat = file_et_etat([apec(f"{i}0W", f"T{i}") for i in range(6)])
    a.par_la_source(q, etat, JOUR, "2026-09-25")
    return appels, etat


def test_apec_403_arret_au_3e_refus(apec_refus):
    assert len(apec_refus[0]) == job_sources.APEC_ABANDON


def test_apec_403_rien_tranche(apec_refus):
    assert all(v[0] is None for v in apec_refus[1].values())


# ── WTJ : le sitemap liste ce qui est en ligne ─────────────────────────────────
U = "https://www.welcometothejungle.com/fr/companies/x/jobs/"


@pytest.fixture
def wtj(monkeypatch):
    sitemap = {(U + "en-ligne").lower()} | {f"u{i}" for i in range(20000)}
    monkeypatch.setattr(a, "_wtj_urls", lambda: sitemap)
    q, etat = file_et_etat([offre(1, url=U + "en-ligne"), offre(2, url=U + "retiree")])
    a.par_la_source(q, etat, JOUR, "2026-09-25")
    return [etat[a.queue_io.oid(o)][0] for o in q]


def test_wtj_au_sitemap_ok(wtj):
    assert wtj[0] == "OK"


def test_wtj_absente_du_sitemap_retiree(wtj):
    assert wtj[1] == "FERMEE_SOURCE"


def test_wtj_sitemap_illisible_rien_tranche(monkeypatch):
    monkeypatch.setattr(a, "_wtj_urls", lambda: None)
    q, etat = file_et_etat([offre(1, url=U + "x")])
    a.par_la_source(q, etat, JOUR, "2026-09-25")
    assert etat[a.queue_io.oid(q[0])][0] is None


# ── plus servie par sa source (Glassdoor, Indeed) ──────────────────────────────
GD = "https://www.glassdoor.fr/job-listing/x"
VIEILLE = offre(1, url=GD, vu_le="2026-08-20", source="glassdoor 2026-08-20")
REVUE = offre(2, url=GD + "2", vu_le="2026-10-01", source="glassdoor 2026-08-20")
CANAL_MORT = offre(3, url="https://fr.indeed.com/viewjob?jk=1", source="Indeed 2026-08-01")
ABSENTE = ("2026-09-02", {"glassdoor.fr": True})


@pytest.fixture
def etat_source():
    return {
        a.queue_io.oid(o): [None, "HTTP 403", o["url"], JOUR] for o in (VIEILLE, REVUE, CANAL_MORT)
    }


def test_plus_vue_depuis_30_j_retiree(etat_source):
    assert a.motif(VIEILLE, etat_source, {}, "", ABSENTE) == "plus servie par sa source"


def test_revue_recemment_gardee(etat_source):
    assert a.motif(REVUE, etat_source, {}, "", ABSENTE) is None


def test_canal_en_panne_rien_conclu(etat_source):
    assert a.motif(CANAL_MORT, etat_source, {}, "", ABSENTE) is None


def test_offre_suivie_jamais_retiree(etat_source):
    assert a.motif(VIEILLE, etat_source, {a.queue_io.oid(VIEILLE): {}}, "", ABSENTE) is None


def test_fermee_source_motif_dedie(etat_source):
    etat_source[a.queue_io.oid(VIEILLE)][0] = "FERMEE_SOURCE"
    assert a.motif(VIEILLE, etat_source, {}, "", None).startswith("retiree par sa source")


# ── choix des cibles : revue = ouverte, rythme selon l'age, ordre ──────────────
L = "https://www.linkedin.com/jobs/view/"


@pytest.fixture
def cibles():
    j = datetime.date(2026, 10, 2)
    revue = offre(1, url=L + "1000001", vu_le="2026-10-01", fit=10)
    jeune = offre(2, url=L + "1000002", source="linkedin 2026-09-28", fit=9)
    vieille = offre(3, url=L + "1000003", source="linkedin 2026-08-20", fit=9)
    basse = offre(4, url=L + "1000004", source="linkedin 2026-08-01", fit=3)
    haute = offre(5, url=L + "1000005", source="linkedin 2026-09-30", fit=10)
    q = [revue, jeune, vieille, basse, haute]
    etat = {  # vues il y a 6 jours
        a.queue_io.oid(jeune): ["OK", "ouverte", jeune["url"], "2026-09-26"],
        a.queue_io.oid(vieille): ["OK", "ouverte", vieille["url"], "2026-09-26"],
    }
    choisies = [o["entreprise"] for o in a.choisir_cibles(q, etat, {}, j)]
    frais = [o["entreprise"] for o in a.choisir_cibles(q, dict(etat), {}, j, frais=3)]
    return choisies, etat, revue, frais


def test_revue_par_la_collecte_pas_de_requete(cibles):
    assert "E1" not in cibles[0]


def test_revue_par_la_collecte_marquee_ok(cibles):
    assert cibles[1][a.queue_io.oid(cibles[2])][0] == "OK"


def test_offre_jeune_pas_encore(cibles):
    assert "E2" not in cibles[0]  # vue il y a 6 j, rythme 10 j


def test_offre_vieille_a_refaire(cibles):
    assert "E3" in cibles[0]  # vue il y a 6 j, rythme 5 j


def test_meilleur_fit_d_abord(cibles):
    assert cibles[0][0] == "E5"


def test_fit_faible_en_dernier(cibles):
    assert cibles[0][-1] == "E4"


def test_frais_fixe_l_emporte_sur_l_age(cibles):
    assert "E2" in cibles[3]


# ── linkedin_desc signale une fiche fermee au passage ──────────────────────────
@pytest.fixture
def fiche_fermee():
    class Rep:
        status_code, text = 200, "<div>No longer accepting applications</div>" + "x" * 500

    class Client:
        def get(self, *x, **k):
            return Rep()

    ld.FERMEES.clear()
    yield ld.description("42", Client())
    ld.FERMEES.clear()


def test_fiche_fermee_pas_de_description(fiche_fermee):
    assert fiche_fermee == ""


def test_fiche_fermee_reperee(fiche_fermee):
    assert "42" in ld.FERMEES


# ── la sauvegarde du jour n'est jamais ecrasee ─────────────────────────────────
def test_premiere_sauvegarde_du_jour_gagne(tmp_path, monkeypatch):
    monkeypatch.setattr(pq, "SCRIPTS", tmp_path)
    (tmp_path / "apply_queue.json").write_text("matin", encoding="utf-8")
    copie = pq.sauvegarder()
    (tmp_path / "apply_queue.json").write_text("soir", encoding="utf-8")
    pq.sauvegarder()
    assert (copie / "apply_queue.json").read_text(encoding="utf-8") == "matin"
