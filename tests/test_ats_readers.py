"""Readers of career pages and public ATS (job_sources.fetch_ats / fetch_autre).

Without network: the responses are frozen, copied from the real structure of the sites on
2026-10-08. Converted from Scripts/test_ats_readers.py, which replaced
_get_borne, _post_borne, WORKDAY_MOTS and WORKDAY_PAUSE for the whole process.
The LinkedIn part is in test_linkedin_429.py.
"""

import datetime
import json

import pytest
from conftest import Reponse

from jobhunter import sources as J


class JS(dict):
    """JSON body of a response — to be told apart from a routing table."""


@pytest.fixture
def lire(monkeypatch):
    """lire(kind, cle, pages, statut=200, ats=False) -> (offers, URLs requested, incidents).
    `pages`: a single body (any URL), or {URL pattern: body} (first pattern contained)."""
    monkeypatch.setattr(J, "WORKDAY_MOTS", ["esg"])  # one request per keyword reader
    monkeypatch.setattr("jobhunter.sources.keywords.du_profil", lambda n: [])  # not the profile's
    monkeypatch.setattr(J, "WORKDAY_PAUSE", 0)

    def faire(kind, cle, pages, statut=200, ats=False, appel=None):
        appels = []

        def envoi(_httpx, url, **kw):
            appels.append(url)
            if not isinstance(pages, dict) or isinstance(pages, JS):
                return Reponse(pages, statut)
            for motif, corps in pages.items():
                if motif in url:
                    return Reponse(corps, statut)
            return Reponse("", 404)

        monkeypatch.setattr(J, "_get_borne", envoi)
        monkeypatch.setattr(J, "_post_borne", envoi)
        J.INCIDENTS.clear()
        if appel:
            r = appel()
        else:
            r = J.fetch_ats(kind, cle) if ats else J.fetch_autre(kind, cle, "Societe")
        return r, appels, {k: dict(v) for k, v in J.INCIDENTS.items()}

    yield faire
    J.INCIDENTS.clear()


def titres(r):
    return [o["titre"] for o in r]


# Safeguard: the test titles do pass the profession filter.
def test_title_ok_accepte_l_intitule_de_test():
    assert J.title_ok("Sustainable Finance Analyst") is True


def test_title_ok_refuse_l_intitule_hors_metier():
    assert J.title_ok("Software Engineer") is False


# ── Avature: two templates, with and without class="link" ─────────────────────────
AVATURE = """
<article class="article article--result"><div class="article__header"><div class="article__header__text">
 <h3 class="article__header__text__title article__header__text__title--7">
  <a class="link" href="https://jobs.example.com/careers/JobDetail/A/1">
   Sustainable Finance Analyst
  </a></h3>
 <span class="list-item-jobCountry">France</span>
 <span class="list-item-jobCreationDate">05-10-2026</span>
</div></div></article>
<article class="article article--result"><div class="article__header"><div class="article__header__text">
 <h3 class="article__header__text__title article__header__text__title--7">
  <a href="https://talent.ecb.europa.eu/careers/JobDetail/B/2">
   ESG Risk Analyst &amp; Reporting
  </a></h3>
</div></div></article>
"""


@pytest.fixture
def avature(lire):
    return lire("avature", "talent.ecb.europa.eu/careers", AVATURE)


def test_avature_deux_gabarits(avature):
    assert titres(avature[0]) == ["Sustainable Finance Analyst", "ESG Risk Analyst & Reporting"]


def test_avature_date_iso(avature):
    assert avature[0][0]["date"] == "2026-10-05"


def test_avature_pays(avature):
    assert avature[0][0]["location"] == "France"


def test_avature_mot_cle_dans_l_url(avature):
    assert "search=esg" in avature[1][0]


def test_avature_source(avature):
    assert avature[0][1]["source"] == "avature:talent.ecb.europa.eu/careers"


# ── TalentBrew (Moody's, ING) ──────────────────────────────────────────────────
TALENTBREW = """
<li class="search-results-list__item"><div class="search-results-list__content">
 <h2 class="search-results-list__job-title"><a class="search-results-list__job-link"
 href="/en/job/stockholm/analyst-sustainable-finance/49841/101" data-job-id="101" id="job-101">Analyst - Sustainable Finance</a></h2>
 <ul><li class="search-results-list__job-info job-location"> Stockholm, Sweden </li></ul></div></li>
<li class="search-results-list__item"><div class="search-results-list__content">
 <h2><a class="search-results-list__job-link" href="/en/job/x/software-engineer/49841/102" data-job-id="102">Software Engineer</a></h2></div></li>
"""


@pytest.fixture
def moodys(lire):
    return lire("talentbrew", "careers.moodys.com/en|49841", TALENTBREW)


def test_talentbrew_url_de_recherche(moodys):
    assert moodys[1][0] == "https://careers.moodys.com/en/search-jobs/esg/49841/1"


def test_talentbrew_hors_metier_ecarte(moodys):
    assert titres(moodys[0]) == ["Analyst - Sustainable Finance"]


def test_talentbrew_lien_absolu(moodys):
    attendu = "https://careers.moodys.com/en/job/stockholm/analyst-sustainable-finance/49841/101"
    assert moodys[0][0]["url"] == attendu


def test_talentbrew_lieu(moodys):
    assert moodys[0][0]["location"] == "Stockholm, Sweden"


ING = """
<li class="search-results-item vacancy-item"><div class="vacancy-item__content">
 <a href="/en/job/makati-city/esg-expert/3121/415" data-job-id="415">
  <h2 class="search-results-item__title vacancy-item__title">ESG Expert</h2> </a>
 <ul class="vacancy-item__metas"><li><span class="job-location">Makati City, Philippines</span></li></ul></div></li>
<button class="js-save-job-btn" data-job-id="415">Save</button>
"""


@pytest.fixture
def ing(lire):
    return lire("talentbrew", "careers.ing.com/en|3121", ING)


def test_talentbrew_ing_titre_dans_le_h2(ing):
    assert titres(ing[0]) == ["ESG Expert"]


def test_talentbrew_ing_lieu_apres_le_lien(ing):
    assert ing[0][0]["location"] == "Makati City, Philippines"


# ── ADB : tableau HTML, « Intitule / reference » ───────────────────────────────
ADB = """<tbody><tr class=" table-striped"><td headers="view-title-table-column"><span class="meta"></span>
<a href="https://www.adb.org/careers/260893">Climate Finance Specialist / 260893</a> </td>
<td class="views-field views-field-field-location">Asian Development Bank Headquarters </td>
<td class="views-field views-field-field-date-content"><time datetime="2026-09-21T12:00:00Z">21 Sep 2026</time></td></tr>
<tr><td><a href="https://www.adb.org/careers/260900">Director / 260900</a></td></tr></tbody>"""


@pytest.fixture
def adb(lire):
    return lire("adb", "www.adb.org/work-with-us/careers/current-opportunities", ADB)


def test_adb_reference_retiree_hors_metier_ecarte(adb):
    assert titres(adb[0]) == ["Climate Finance Specialist"]


def test_adb_date(adb):
    assert adb[0][0]["date"] == "2026-09-21"


def test_adb_lieu(adb):
    assert adb[0][0]["location"] == "Asian Development Bank Headquarters"


# ── PeopleSoft Fluid (BEI): fields indexed by row ──────────────────────────
def ligne(i, titre, ident, date, lieu):
    return (
        f"<span class='ps_box-value' id='SCH_JOB_TITLE${i}' >{titre}</span>"
        f"<span class='ps_box-value' id='HRS_APP_JBSCH_I_HRS_JOB_OPENING_ID${i}' >{ident}</span>"
        f"<span class='ps_box-value' id='SCH_OPENED${i}' >{date}</span>"
        f"<span class='ps_box-value' id='LOCATION${i}' >{lieu}</span>"
    )


PS = (
    ligne(0, "Sustainable Finance Senior Officer", "111", "17/09/2026", "LU - Luxembourg")
    + ligne(1, "Executive Assistant", "112", "05/10/2026", "LU - Luxembourg")
    + ligne(2, "ESG Analyst &amp; Advisor", "113", "", "LU - Luxembourg")
)


@pytest.fixture
def bei(lire):
    return lire("peoplesoft", "erecruitment.eib.org/psc/hr/EIBJOBS/CAREERS", PS)


def test_peoplesoft_filtre_metier(bei):
    assert titres(bei[0]) == ["Sustainable Finance Senior Officer", "ESG Analyst & Advisor"]


def test_peoplesoft_date_iso(bei):
    assert bei[0][0]["date"] == "2026-09-17"


def test_peoplesoft_date_absente_vide(bei):
    assert bei[0][1]["date"] == ""


def test_peoplesoft_identifiant_dans_le_lien(bei):
    assert "JobOpeningId=111&" in bei[0][0]["url"]


def test_peoplesoft_une_seule_requete(bei):
    assert len(bei[1]) == 1


# ── Generali : JSON, publiees seulement, lien construit ────────────────────────
GG = JS(
    {
        "error": None,
        "response": [
            {
                "contestId": "ATS-P-1",
                "title": "Sustainable Investment Intern",
                "currentStatus": "PUBLISHED",
                "currentStatusDate": "2026-10-05T09:00:00Z",
                "primaryLocation": "Trieste",
                "descriptionInternalHTML": "<p>ESG fund analysis</p>",
                "internalQualificationHTML": "<ul><li>Finance</li></ul>",
            },
            {"contestId": "ATS-P-2", "title": "ESG Analyst", "currentStatus": "CLOSED"},
            {"contestId": "", "title": "Risk Analyst", "currentStatus": "PUBLISHED"},
        ],
    }
)


@pytest.fixture
def generali(lire):
    return lire("gogenerali", "gogenerali.com", GG)


def test_gogenerali_publiees_avec_identifiant(generali):
    assert titres(generali[0]) == ["Sustainable Investment Intern"]


def test_gogenerali_lien_de_fiche(generali):
    attendu = "https://gogenerali.com/home/job/ATS-P-1/sustainable-investment-intern"
    assert generali[0][0]["url"] == attendu


def test_gogenerali_date(generali):
    assert generali[0][0]["date"] == "2026-10-05"


def test_gogenerali_description_et_qualifications(generali):
    d = generali[0][0]["description"]
    assert "ESG fund analysis" in d and "Finance" in d


def test_gogenerali_perimetre_direzionale(generali):
    assert "onlyDirectionalPerimeter=true" in generali[1][0]


# ── Sitemap: index, age limit, leading identifier, h1 mode ────────────────
AUJ = datetime.date.today().isoformat()
VIEUX = (datetime.date.today() - datetime.timedelta(days=J.SITEMAP_JOURS + 5)).isoformat()
SM = {
    "sitemap.xml": "<sitemapindex><sitemap><loc>https://x.nl/sitemap.vacancy.xml</loc></sitemap></sitemapindex>",
    "sitemap.vacancy.xml": f"""<urlset>
<url><loc>https://x.nl/vacature/7827/senior-esg-risk-analyst</loc><lastmod>{AUJ}T22:00:00+02:00</lastmod></url>
<url><loc>https://x.nl/vacature/8460/sustainable-finance-analyst-4</loc><lastmod>{AUJ}</lastmod></url>
<url><loc>https://x.nl/vacature/9000/esg-analyst-ancien</loc><lastmod>{VIEUX}</lastmod></url>
<url><loc>https://x.nl/blog/esg-analyst-story</loc><lastmod>{AUJ}</lastmod></url></urlset>""",
}


@pytest.fixture
def sitemap(lire):
    return lire("sitemap", "https://x.nl/sitemap.xml|/vacature/", SM)


def test_sitemap_identifiant_et_suffixe_retires(sitemap):
    assert titres(sitemap[0]) == ["Senior esg risk analyst", "Sustainable finance analyst"]


def test_sitemap_date_lastmod(sitemap):
    assert sitemap[0][0]["date"] == AUJ


KBC = {
    "en.sitemap.xml": f"""<urlset>
<url><loc>https://www.kbc.be/jobs/en/vacancies/ID90684.html</loc><lastmod>{AUJ}T13:01:57Z</lastmod></url>
<url><loc>https://www.kbc.be/jobs/en/vacancies/ID90685.html</loc><lastmod>{AUJ}</lastmod></url>
<url><loc>https://www.kbc.be/jobs/en/vacancies/general-vacancy.html</loc><lastmod>{AUJ}</lastmod></url></urlset>""",
    "ID90684": "<html><h1 class='t'>ESG &amp; Climate <span>Risk Analyst</span></h1></html>",
    "ID90685": "<html><p>pas de titre</p></html>",
}


@pytest.fixture
def kbc(lire):
    return lire("sitemap", "https://www.kbc.be/jobs/en.sitemap.xml|/jobs/en/vacancies/ID|h1", KBC)


def test_sitemap_h1_titre_lu_dans_la_page(kbc):
    assert titres(kbc[0]) == ["ESG & Climate Risk Analyst"]


def test_sitemap_h1_page_sans_h1_ignoree(kbc):
    assert len(kbc[1]) == 3  # 1 sitemap + 2 pages


# ── Teamtailor : RSS, lieu ville + pays, domaine propre ────────────────────────
TT = """<rss><channel><item><title>ESG Analyst</title><link>https://jobs.tennaxia.com/jobs/1-esg</link>
<description>&lt;p&gt;Reporting CSRD&lt;/p&gt;</description><tt:city>Paris</tt:city><tt:country>France</tt:country></item>
<item><title>Office Manager</title><link>https://jobs.tennaxia.com/jobs/2</link></item></channel></rss>"""


@pytest.fixture
def teamtailor(lire):
    return lire("teamtailor", "jobs.tennaxia.com", TT, ats=True)


def test_teamtailor_domaine_propre(teamtailor):
    assert teamtailor[1][0] == "https://jobs.tennaxia.com/jobs.rss"


def test_teamtailor_filtre_metier(teamtailor):
    assert titres(teamtailor[0]) == ["ESG Analyst"]


def test_teamtailor_lieu(teamtailor):
    assert teamtailor[0][0]["location"] == "Paris, France"


def test_teamtailor_description_sans_balises(teamtailor):
    assert teamtailor[0][0]["description"].strip() == "Reporting CSRD"


def test_teamtailor_sous_domaine_par_defaut(lire):
    assert lire("teamtailor", "southpole", TT, ats=True)[1][0] == (
        "https://southpole.teamtailor.com/jobs.rss"
    )


# ── Workable / Pinpoint / Eightfold : JSON public ──────────────────────────────
def test_workable_filtre_et_lieu(lire):
    r = lire(
        "workable",
        "quantis",
        JS(
            {
                "jobs": [
                    {
                        "title": "Sustainability Consultant",
                        "url": "https://apply.workable.com/j/1",
                        "city": "Lausanne",
                        "country": "Switzerland",
                        "published_on": "2026-10-01",
                    },
                    {"title": "Receptionist", "url": "https://apply.workable.com/j/2"},
                ]
            }
        ),
    )[0]
    assert [(o["titre"], o["location"]) for o in r] == [
        ("Sustainability Consultant", "Lausanne, Switzerland")
    ]


# ── Personio (XML) / Breezy (JSON): public career page feeds ─────────────────────
PERSONIO = """<?xml version="1.0" encoding="UTF-8"?>
<workzag-jobs>
<position>
    <id>1834171</id>
    <office>Paris</office>
    <additionalOffices><office>Lyon</office></additionalOffices>
    <name>Sustainable Finance Analyst</name>
    <jobDescriptions>
      <jobDescription><name>Missions</name><value><![CDATA[<p>SFDR &amp; taxonomy reporting.</p>]]></value></jobDescription>
    </jobDescriptions>
    <createdAt>2026-10-20T14:10:41+00:00</createdAt>
</position>
<position><id>2</id><office>Paris</office><name>Office Manager</name></position>
</workzag-jobs>"""


def test_personio_titre_lieu_date_et_description(lire):
    r, appels, _ = lire("personio", "acme", PERSONIO)
    assert appels == ["https://acme.jobs.personio.de/xml"]
    assert [(o["titre"], o["url"], o["location"]) for o in r] == [
        (
            "Sustainable Finance Analyst",
            "https://acme.jobs.personio.de/job/1834171",
            "Paris",  # the main office, not the additional one
        )
    ]
    assert "SFDR & taxonomy reporting." in r[0]["description"]


def test_personio_hote_complet_et_refus(lire):
    r, appels, incidents = lire("personio", "acme.jobs.personio.com", "", statut=503)
    assert r == [] and appels == ["https://acme.jobs.personio.com/xml"]
    assert incidents == {"ats:personio": {"HTTP 503": 1}}  # a 404 (no such account) stays silent


def test_breezy_lieu_et_filtre(lire):
    r, appels, _ = lire(
        "breezy",
        "acme",
        [
            {
                "name": "ESG Risk Analyst",
                "url": "https://acme.breezy.hr/p/1-esg",
                "published_date": "2026-10-01T10:00:00.000Z",
                "location": {"city": "Paris", "country": {"name": "France"}},
            },
            {"name": "Receptionist", "url": "https://acme.breezy.hr/p/2"},
        ],
    )
    assert appels == ["https://acme.breezy.hr/json"]
    assert [(o["titre"], o["location"]) for o in r] == [("ESG Risk Analyst", "Paris, France")]


@pytest.fixture
def pinpoint(lire):
    return lire(
        "pinpoint",
        "jobs.clientearth.org",
        JS(
            {
                "data": [
                    {
                        "title": "Climate Finance Lawyer",
                        "url": "https://jobs.clientearth.org/p/1",
                        "location": {"name": "London"},
                    }
                ]
            }
        ),
    )


def test_pinpoint_domaine_propre(pinpoint):
    assert pinpoint[1][0] == "https://jobs.clientearth.org/postings.json"


def test_pinpoint_lieu(pinpoint):
    assert pinpoint[0][0]["location"] == "London"


@pytest.fixture
def eightfold(lire):
    return lire(
        "eightfold",
        "portal.careers.hsbc.com|hsbc.com",
        JS(
            {
                "positions": [
                    {
                        "name": "Climate Risk Analyst",
                        "canonicalPositionUrl": "https://portal.careers.hsbc.com/careers/job/1",
                        "location": "London",
                        "job_description": "<p>TCFD</p>",
                    }
                ]
            }
        ),
    )


def test_eightfold_domaine_dans_la_requete(eightfold):
    assert "domain=hsbc.com" in eightfold[1][0] and "query=esg" in eightfold[1][0]


def test_eightfold_offre(eightfold):
    o = eightfold[0][0]
    assert (o["titre"], o["url"]) == (
        "Climate Risk Analyst",
        "https://portal.careers.hsbc.com/careers/job/1",
    )


# ── SuccessFactors and TalentSoft RSS ───────────────────────────────────────────
SF = """<rss><item><title><![CDATA[ESG Analyst - Paris (Paris, FR)]]></title>
<link><![CDATA[https://careers.ey.com/job/1]]></link><description><![CDATA[<p>CSRD</p>]]></description></item>
<item><title>Job | Sustainable Finance Analyst</title><link>https://jobs.belfius.be/job/2</link></item></rss>"""


@pytest.fixture
def sfrss(lire):
    return lire("sfrss", "careers.ey.com", SF)


def test_sfrss_titres_nettoyes(sfrss):
    assert titres(sfrss[0]) == ["ESG Analyst - Paris", "Sustainable Finance Analyst"]


def test_sfrss_lieu_tire_de_la_parenthese(sfrss):
    assert sfrss[0][0]["location"] == "Paris, FR"


def test_sfrss_lien_hors_cdata(sfrss):
    assert sfrss[0][0]["url"] == "https://careers.ey.com/job/1"


TS = """<rss><item><title>2026-116250 - Analyste ESG H/F</title><link>https://jobs.amundi.com/offre/1</link>
<category>CDI</category><category>Finance</category><category>Paris</category></item></rss>"""


@pytest.fixture
def talentsoft(lire):
    return lire("talentsoft", "jobs.amundi.com", TS)


def test_talentsoft_reference_retiree(talentsoft):
    assert titres(talentsoft[0]) == ["Analyste ESG H/F"]


def test_talentsoft_lieu(talentsoft):
    assert talentsoft[0][0]["location"] == "Paris"


# ── Phenom, Jibe, Oracle ───────────────────────────────────────────────────────
DDO = {
    "eagerLoadRefineSearch": {
        "data": {
            "jobs": [
                {
                    "jobId": "R1",
                    "title": "ESG Data Analyst",
                    "cityStateCountry": "Paris, France",
                    "postedDate": "2026-10-02T00:00:00",
                }
            ]
        }
    }
}


@pytest.fixture
def phenom(lire):
    return lire(
        "phenom",
        "careers.allianz.com/global/en",
        "<script>phApp.ddo = " + json.dumps(DDO) + ";</script>",
    )


def test_phenom_offre(phenom):
    o = phenom[0][0]
    assert (o["titre"], o["url"], o["date"]) == (
        "ESG Data Analyst",
        "https://careers.allianz.com/global/en/job/R1",
        "2026-10-02",
    )


def test_phenom_une_seule_page(phenom):
    assert len(phenom[1]) == 1  # fewer than 10 offers


def test_jibe_lien_construit_sans_slug_ignore(lire):
    r = lire(
        "jibe",
        "careers.se.com",
        JS(
            {
                "jobs": [
                    {
                        "data": {
                            "slug": "123",
                            "title": "Sustainability Analyst",
                            "location_name": "Rueil",
                            "description": "<b>x</b>",
                        }
                    },
                    {"data": {"title": "Sans slug"}},
                ]
            }
        ),
    )[0]
    assert [o["url"] for o in r] == ["https://careers.se.com/jobs/123?lang=en-us"]


@pytest.fixture
def oracle(lire):
    return lire(
        "oracle",
        "ejqi.fa.ocs.oraclecloud.eu|CX_1001",
        JS(
            {
                "items": [
                    {
                        "requisitionList": [
                            {
                                "Id": "24752",
                                "Title": "Analyst, Corporate & Sustainability Advisory",
                                "PrimaryLocation": "Copenhagen",
                                "PostedDate": "2026-10-01",
                            },
                            {"Title": "Sans Id"},
                        ]
                    }
                ]
            }
        ),
    )


def test_oracle_lien_de_fiche(oracle):
    assert [o["url"] for o in oracle[0]] == [
        "https://ejqi.fa.ocs.oraclecloud.eu/hcmUI/CandidateExperience/en/sites/CX_1001/job/24752"
    ]


def test_oracle_site_dans_la_requete(oracle):
    assert "siteNumber=CX_1001" in oracle[1][0]


def test_oracle_liste_vide_sans_erreur(lire):
    r, _, incidents = lire("oracle", "x.oraclecloud.com|CX", JS({"items": []}))
    assert (r, incidents) == ([], {})


# ── Cornerstone: the page's anonymous token, then API ───────────────────────────
CSOD = {
    "/ux/ats/careersite/": 'csod.context = {"token": "abc", "endpoints": {"cloud": "https://eu.api.csod.com/"}};',
    "rec-job-search": JS(
        {
            "data": {
                "requisitions": [
                    {
                        "displayJobTitle": "Climate Finance Officer",
                        "requisitionId": 77,
                        "locations": [{"city": "Paris", "country": "FR"}],
                    }
                ]
            }
        }
    ),
}


@pytest.fixture
def csod(lire):
    return lire("csod", "afd.csod.com|5", CSOD)


def test_csod_api_du_contexte_appelee(csod):
    assert csod[1][1] == "https://eu.api.csod.com/rec-job-search/external/jobs"


def test_csod_offre(csod):
    assert (csod[0][0]["titre"], csod[0][0]["location"]) == ("Climate Finance Officer", "Paris, FR")


def test_csod_lien_de_fiche(csod):
    assert csod[0][0]["url"] == "https://afd.csod.com/ux/ats/careersite/5/home/requisition/77?c=afd"


def test_csod_sans_jeton_pas_d_appel_api(lire):
    r, appels, _ = lire(
        "csod", "afd.csod.com|5", {"/ux/ats/careersite/": "<html>pas de contexte</html>"}
    )
    assert (r, len(appels)) == ([], 1)


# ── iCIMS: pagination up to a page with nothing new ─────────────────────────
CARTE = (
    '<li class="iCIMS_JobCardItem"><a href="https://careers-msci.icims.com/jobs/{n}/x/job?in_iframe=1" '
    'title="{n} - {t}">x</a><span>Job Locations</span> </dt> <dd class="x"><span > Paris </span></li>'
)


@pytest.fixture
def icims(lire):
    page = CARTE.format(n=1, t="ESG Research Analyst") + CARTE.format(n=2, t="Software Engineer")
    return lire("icims", "careers-msci.icims.com", page)


def test_icims_filtre_et_lien_sans_iframe(icims):
    assert [(o["titre"], o["url"]) for o in icims[0]] == [
        ("ESG Research Analyst", "https://careers-msci.icims.com/jobs/1/x/job")
    ]


def test_icims_arret_sans_nouveaute(icims):
    assert len(icims[1]) == 2


def test_icims_lieu(icims):
    assert icims[0][0]["location"] == "Paris"


# ── Choisir le service public: financial employer OR ESG title ────────────
def carte_csp(href, titre, employeur):
    return (
        f'<li class="fr-col-12 item"><h3 class="fr-card__title"><a\n href="{href}">{titre}</a></h3>'
        f'<ul><li><span class="sr-only">Employeur : </span> {employeur} </li>'
        f'<li><span class="sr-only">Localisation : </span> Paris </li></ul>'
    )


@pytest.fixture
def service_public(lire):
    csp = (
        carte_csp("/o/1", "Analyste financier", "Caisse des Dépôts")
        + carte_csp("/o/2", "Chargé de mission climat", "Commune de Trifouillis")
        + carte_csp("/o/3", "Chargé de mission RSE", "Commune de Trifouillis")
    )
    return lire(None, None, csp, appel=J.fetch_service_public)


def test_service_public_employeur_financier_ou_intitule_esg(service_public):
    assert sorted(o["url"] for o in service_public[0]) == ["/o/1", "/o/3"]


def test_service_public_employeur_et_lieu(service_public):
    o = service_public[0][0]
    assert (o["entreprise"], o["location"]) == ("Caisse des Dépôts", "Paris")


# ── refusals: 403 counts an incident, 404 stays silent ────────────────────────────────
@pytest.fixture
def refus_403(lire):
    return lire("talentbrew", "careers.moodys.com/en|49841", "", 403)


def test_403_rien(refus_403):
    assert refus_403[0] == []


def test_403_incident_compte(refus_403):
    assert refus_403[2].get("ats:talentbrew") == {"HTTP 403": 1}


@pytest.fixture
def absent_404(lire):
    return lire("peoplesoft", "erecruitment.eib.org/psc/hr/EIBJOBS/CAREERS", "", 404)


def test_404_rien(absent_404):
    assert absent_404[0] == []


def test_404_silence(absent_404):
    assert absent_404[2].get("ats:peoplesoft", {}) == {}


def test_reponse_illisible_exception_comptee(lire):
    r, _, incidents = lire("gogenerali", "gogenerali.com", "<html>pas du json</html>")
    assert (r, incidents.get("ats:gogenerali", {})) == ([], {"JSONDecodeError": 1})
