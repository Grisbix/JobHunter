#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_lecteurs_ats.py — lecteurs de pages carriere et d'ATS publics (job_sources).

Sans reseau : _get_borne / _post_borne sont remplaces par une doublure qui rend
des reponses figees, copiees de la structure reelle des sites au 2026-10-08.

Run : python test_lecteurs_ats.py
"""
import _profil_test  # noqa: F401  — les tests tournent sur le profil d'exemple
import sys
import json
import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent))

import job_sources as J

ok = ko = 0


def verifie(nom, obtenu, attendu):
    global ok, ko
    if obtenu == attendu:
        ok += 1
    else:
        ko += 1
        print(f"❌ {nom} → {obtenu!r}, attendu {attendu!r}")


class Rep:
    def __init__(self, corps, statut=200):
        self.text = corps if isinstance(corps, str) else json.dumps(corps)
        self.status_code = statut

    def json(self):
        return json.loads(self.text)


class JS(dict):
    """Corps JSON d'une reponse — a distinguer d'une table de routes."""


APPELS = []


def route(table, statut=200):
    """Doublure de _get_borne/_post_borne : premier motif de `table` contenu
    dans l'URL -> sa reponse. Une page seule vaut pour toute URL."""
    def envoi(_httpx, url, **kw):
        APPELS.append(url)
        if not isinstance(table, dict) or isinstance(table, JS):
            return Rep(table, statut)
        for motif, corps in table.items():
            if motif in url:
                return Rep(corps, statut)
        return Rep("", 404)
    return envoi


J.WORKDAY_MOTS = ["esg"]        # un seul mot : une requete par lecteur a mot-cle
J.WORKDAY_PAUSE = 0


def lit(kind, cle, pages, statut=200, ats=False):
    APPELS.clear()
    J.INCIDENTS.clear()
    J._get_borne = J._post_borne = route(pages, statut)
    return J.fetch_ats(kind, cle) if ats else J.fetch_autre(kind, cle, "Societe")


def titres(r):
    return [o["titre"] for o in r]


# Garde-fou : les intitules de test passent bien le filtre metier.
verifie("title_ok accepte l'intitule de test", J.title_ok("Sustainable Finance Analyst"), True)
verifie("title_ok refuse l'intitule hors metier", J.title_ok("Software Engineer"), False)

# ── Avature : deux gabarits, avec et sans class="link" (TotalEnergies / BCE) ──
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
r = lit("avature", "talent.ecb.europa.eu/careers", AVATURE)
verifie("avature : deux gabarits lus", titres(r), ["Sustainable Finance Analyst", "ESG Risk Analyst & Reporting"])
verifie("avature : date jj-mm-aaaa remise en ISO", r[0]["date"], "2026-10-05")
verifie("avature : pays", r[0]["location"], "France")
verifie("avature : mot-cle dans l'URL", "search=esg" in APPELS[0], True)
verifie("avature : source", r[1]["source"], "avature:talent.ecb.europa.eu/careers")

# ── TalentBrew (Moody's) : liens relatifs, mot-cle dans le chemin ──
TALENTBREW = """
<li class="search-results-list__item"><div class="search-results-list__content">
 <h2 class="search-results-list__job-title"><a class="search-results-list__job-link"
 href="/en/job/stockholm/analyst-sustainable-finance/49841/101" data-job-id="101" id="job-101">Analyst - Sustainable Finance</a></h2>
 <ul><li class="search-results-list__job-info job-location"> Stockholm, Sweden </li></ul></div></li>
<li class="search-results-list__item"><div class="search-results-list__content">
 <h2><a class="search-results-list__job-link" href="/en/job/x/software-engineer/49841/102" data-job-id="102">Software Engineer</a></h2></div></li>
"""
r = lit("talentbrew", "careers.moodys.com/en|49841", TALENTBREW)
verifie("talentbrew : URL de recherche", APPELS[0], "https://careers.moodys.com/en/search-jobs/esg/49841/1")
verifie("talentbrew : intitule hors metier ecarte", titres(r), ["Analyst - Sustainable Finance"])
verifie("talentbrew : lien absolu", r[0]["url"],
        "https://careers.moodys.com/en/job/stockholm/analyst-sustainable-finance/49841/101")
verifie("talentbrew : lieu", r[0]["location"], "Stockholm, Sweden")

# Second theme TalentBrew (ING) : titre dans un <h2> sous le lien, lieu plus loin.
ING = """
<li class="search-results-item vacancy-item"><div class="vacancy-item__content">
 <a href="/en/job/makati-city/esg-expert/3121/415" data-job-id="415">
  <h2 class="search-results-item__title vacancy-item__title">ESG Expert</h2> </a>
 <ul class="vacancy-item__metas"><li><span class="job-location">Makati City, Philippines</span></li></ul></div></li>
<button class="js-save-job-btn" data-job-id="415">Save</button>
"""
r = lit("talentbrew", "careers.ing.com/en|3121", ING)
verifie("talentbrew ING : titre dans le h2", titres(r), ["ESG Expert"])
verifie("talentbrew ING : lieu apres le lien", r[0]["location"], "Makati City, Philippines")

# ── ADB : tableau HTML, « Intitule / reference » ──
ADB = """<tbody><tr class=" table-striped"><td headers="view-title-table-column"><span class="meta"></span>
<a href="https://www.adb.org/careers/260893">Climate Finance Specialist / 260893</a> </td>
<td class="views-field views-field-field-location">Asian Development Bank Headquarters </td>
<td class="views-field views-field-field-date-content"><time datetime="2026-09-21T12:00:00Z">21 Sep 2026</time></td></tr>
<tr><td><a href="https://www.adb.org/careers/260900">Director / 260900</a></td></tr></tbody>"""
r = lit("adb", "www.adb.org/work-with-us/careers/current-opportunities", ADB)
verifie("adb : reference retiree, hors metier ecarte", titres(r), ["Climate Finance Specialist"])
verifie("adb : date", r[0]["date"], "2026-09-21")
verifie("adb : lieu", r[0]["location"], "Asian Development Bank Headquarters")

# ── PeopleSoft Fluid (BEI) : champs indexes par ligne ──
def ligne(i, titre, ident, date, lieu):
    return (f"<span class='ps_box-value' id='SCH_JOB_TITLE${i}' >{titre}</span>"
            f"<span class='ps_box-value' id='HRS_APP_JBSCH_I_HRS_JOB_OPENING_ID${i}' >{ident}</span>"
            f"<span class='ps_box-value' id='SCH_OPENED${i}' >{date}</span>"
            f"<span class='ps_box-value' id='LOCATION${i}' >{lieu}</span>")

PS = (ligne(0, "Sustainable Finance Senior Officer", "111", "17/09/2026", "LU - Luxembourg")
      + ligne(1, "Executive Assistant", "112", "05/10/2026", "LU - Luxembourg")
      + ligne(2, "ESG Analyst &amp; Advisor", "113", "", "LU - Luxembourg"))
r = lit("peoplesoft", "erecruitment.eib.org/psc/hr/EIBJOBS/CAREERS", PS)
verifie("peoplesoft : filtre metier", titres(r), ["Sustainable Finance Senior Officer", "ESG Analyst & Advisor"])
verifie("peoplesoft : date jj/mm/aaaa en ISO", r[0]["date"], "2026-09-17")
verifie("peoplesoft : date absente reste vide", r[1]["date"], "")
verifie("peoplesoft : identifiant dans le lien", "JobOpeningId=111&" in r[0]["url"], True)
verifie("peoplesoft : une seule requete, sans mot-cle", len(APPELS), 1)

# ── Generali (gogenerali.com) : JSON, publiees seulement, lien construit ──
GG = JS({"error": None, "response": [
    {"contestId": "ATS-P-1", "title": "Sustainable Investment Intern", "currentStatus": "PUBLISHED",
     "currentStatusDate": "2026-10-05T09:00:00Z", "primaryLocation": "Trieste",
     "descriptionInternalHTML": "<p>ESG fund analysis</p>", "internalQualificationHTML": "<ul><li>Finance</li></ul>"},
    {"contestId": "ATS-P-2", "title": "ESG Analyst", "currentStatus": "CLOSED"},
    {"contestId": "", "title": "Risk Analyst", "currentStatus": "PUBLISHED"}]})
r = lit("gogenerali", "gogenerali.com", GG)
verifie("gogenerali : publiees avec identifiant seulement", titres(r), ["Sustainable Investment Intern"])
verifie("gogenerali : lien de fiche", r[0]["url"],
        "https://gogenerali.com/home/job/ATS-P-1/sustainable-investment-intern")
verifie("gogenerali : date ISO tronquee", r[0]["date"], "2026-10-05")
verifie("gogenerali : description + qualifications", "ESG fund analysis" in r[0]["description"]
        and "Finance" in r[0]["description"], True)
verifie("gogenerali : perimetre direzionale demande", "onlyDirectionalPerimeter=true" in APPELS[0], True)

# ── Sitemap : index, limite d'age, identifiant en tete, mode h1 ──
AUJ = datetime.date.today().isoformat()
VIEUX = (datetime.date.today() - datetime.timedelta(days=J.SITEMAP_JOURS + 5)).isoformat()
SM = {
    "sitemap.xml": "<sitemapindex><sitemap><loc>https://x.nl/sitemap.vacancy.xml</loc></sitemap></sitemapindex>",
    "sitemap.vacancy.xml": f"""<urlset>
<url><loc>https://x.nl/vacature/7827/senior-esg-risk-analyst</loc><lastmod>{AUJ}T22:00:00+02:00</lastmod></url>
<url><loc>https://x.nl/vacature/8460/sustainable-finance-analyst-4</loc><lastmod>{AUJ}</lastmod></url>
<url><loc>https://x.nl/vacature/9000/esg-analyst-ancien</loc><lastmod>{VIEUX}</lastmod></url>
<url><loc>https://x.nl/blog/esg-analyst-story</loc><lastmod>{AUJ}</lastmod></url></urlset>"""}
r = lit("sitemap", "https://x.nl/sitemap.xml|/vacature/", SM)
verifie("sitemap : identifiant et suffixe retires", titres(r), ["Senior esg risk analyst", "Sustainable finance analyst"])
verifie("sitemap : date lastmod", r[0]["date"], AUJ)

KBC = {"en.sitemap.xml": f"""<urlset>
<url><loc>https://www.kbc.be/jobs/en/vacancies/ID90684.html</loc><lastmod>{AUJ}T13:01:57Z</lastmod></url>
<url><loc>https://www.kbc.be/jobs/en/vacancies/ID90685.html</loc><lastmod>{AUJ}</lastmod></url>
<url><loc>https://www.kbc.be/jobs/en/vacancies/general-vacancy.html</loc><lastmod>{AUJ}</lastmod></url></urlset>""",
       "ID90684": "<html><h1 class='t'>ESG &amp; Climate <span>Risk Analyst</span></h1></html>",
       "ID90685": "<html><p>pas de titre</p></html>"}
r = lit("sitemap", "https://www.kbc.be/jobs/en.sitemap.xml|/jobs/en/vacancies/ID|h1", KBC)
verifie("sitemap h1 : titre lu dans la page, balises retirees", titres(r), ["ESG & Climate Risk Analyst"])
verifie("sitemap h1 : page sans h1 ignoree, 1 sitemap + 2 pages", len(APPELS), 3)

# ── Teamtailor (fetch_ats) : RSS, lieu ville + pays, domaine propre ──
TT = """<rss><channel><item><title>ESG Analyst</title><link>https://jobs.tennaxia.com/jobs/1-esg</link>
<description>&lt;p&gt;Reporting CSRD&lt;/p&gt;</description><tt:city>Paris</tt:city><tt:country>France</tt:country></item>
<item><title>Office Manager</title><link>https://jobs.tennaxia.com/jobs/2</link></item></channel></rss>"""
r = lit("teamtailor", "jobs.tennaxia.com", TT, ats=True)
verifie("teamtailor : domaine propre", APPELS[0], "https://jobs.tennaxia.com/jobs.rss")
verifie("teamtailor : filtre metier", titres(r), ["ESG Analyst"])
verifie("teamtailor : lieu", r[0]["location"], "Paris, France")
verifie("teamtailor : description sans balises", r[0]["description"].strip(), "Reporting CSRD")
lit("teamtailor", "southpole", TT, ats=True)
verifie("teamtailor : sous-domaine par defaut", APPELS[0], "https://southpole.teamtailor.com/jobs.rss")

# ── Workable / Pinpoint : JSON public ──
r = lit("workable", "quantis", JS({"jobs": [
    {"title": "Sustainability Consultant", "url": "https://apply.workable.com/j/1", "city": "Lausanne",
     "country": "Switzerland", "published_on": "2026-10-01"},
    {"title": "Receptionist", "url": "https://apply.workable.com/j/2"}]}))
verifie("workable : filtre et lieu", [(o["titre"], o["location"]) for o in r],
        [("Sustainability Consultant", "Lausanne, Switzerland")])
r = lit("pinpoint", "jobs.clientearth.org", JS({"data": [
    {"title": "Climate Finance Lawyer", "url": "https://jobs.clientearth.org/p/1", "location": {"name": "London"}}]}))
verifie("pinpoint : domaine propre accepte", APPELS[0], "https://jobs.clientearth.org/postings.json")
verifie("pinpoint : lieu", r[0]["location"], "London")

# ── Eightfold : positions JSON ──
r = lit("eightfold", "portal.careers.hsbc.com|hsbc.com", JS({"positions": [
    {"name": "Climate Risk Analyst", "canonicalPositionUrl": "https://portal.careers.hsbc.com/careers/job/1",
     "location": "London", "job_description": "<p>TCFD</p>"}]}))
verifie("eightfold : domaine dans la requete", "domain=hsbc.com" in APPELS[0] and "query=esg" in APPELS[0], True)
verifie("eightfold : offre", (r[0]["titre"], r[0]["url"]),
        ("Climate Risk Analyst", "https://portal.careers.hsbc.com/careers/job/1"))

# ── RSS SuccessFactors : CDATA, lieu final entre parentheses, prefixe « Job | » ──
SF = """<rss><item><title><![CDATA[ESG Analyst - Paris (Paris, FR)]]></title>
<link><![CDATA[https://careers.ey.com/job/1]]></link><description><![CDATA[<p>CSRD</p>]]></description></item>
<item><title>Job | Sustainable Finance Analyst</title><link>https://jobs.belfius.be/job/2</link></item></rss>"""
r = lit("sfrss", "careers.ey.com", SF)
verifie("sfrss : titres nettoyes", titres(r), ["ESG Analyst - Paris", "Sustainable Finance Analyst"])
verifie("sfrss : lieu tire de la parenthese", r[0]["location"], "Paris, FR")
verifie("sfrss : lien hors CDATA", r[0]["url"], "https://careers.ey.com/job/1")

# ── RSS TalentSoft : reference en tete, lieu = 3e categorie ──
TS = """<rss><item><title>2026-116250 - Analyste ESG H/F</title><link>https://jobs.amundi.com/offre/1</link>
<category>CDI</category><category>Finance</category><category>Paris</category></item></rss>"""
r = lit("talentsoft", "jobs.amundi.com", TS)
verifie("talentsoft : reference retiree", titres(r), ["Analyste ESG H/F"])
verifie("talentsoft : lieu", r[0]["location"], "Paris")

# ── Phenom : JSON embarque dans phApp.ddo ──
DDO = {"eagerLoadRefineSearch": {"data": {"jobs": [
    {"jobId": "R1", "title": "ESG Data Analyst", "cityStateCountry": "Paris, France", "postedDate": "2026-10-02T00:00:00"}]}}}
r = lit("phenom", "careers.allianz.com/global/en", "<script>phApp.ddo = " + json.dumps(DDO) + ";</script>")
verifie("phenom : offre", (r[0]["titre"], r[0]["url"], r[0]["date"]),
        ("ESG Data Analyst", "https://careers.allianz.com/global/en/job/R1", "2026-10-02"))
verifie("phenom : moins de 10 offres = une seule page", len(APPELS), 1)

# ── Jibe : /api/jobs ──
r = lit("jibe", "careers.se.com", JS({"jobs": [
    {"data": {"slug": "123", "title": "Sustainability Analyst", "location_name": "Rueil", "description": "<b>x</b>"}},
    {"data": {"title": "Sans slug"}}]}))
verifie("jibe : lien construit, sans slug ignore", [o["url"] for o in r], ["https://careers.se.com/jobs/123?lang=en-us"])

# ── Oracle Recruiting : requisitionList ──
r = lit("oracle", "ejqi.fa.ocs.oraclecloud.eu|CX_1001", JS({"items": [{"requisitionList": [
    {"Id": "24752", "Title": "Analyst, Corporate & Sustainability Advisory", "PrimaryLocation": "Copenhagen",
     "PostedDate": "2026-10-01"}, {"Title": "Sans Id"}]}]}))
verifie("oracle : lien de fiche", [o["url"] for o in r],
        ["https://ejqi.fa.ocs.oraclecloud.eu/hcmUI/CandidateExperience/en/sites/CX_1001/job/24752"])
verifie("oracle : site dans la requete", "siteNumber=CX_1001" in APPELS[0], True)
r = lit("oracle", "x.oraclecloud.com|CX", JS({"items": []}))
verifie("oracle : liste vide sans erreur", (r, dict(J.INCIDENTS)), ([], {}))

# ── Cornerstone : jeton anonyme de la page, puis API ──
CSOD = {"/ux/ats/careersite/": 'csod.context = {"token": "abc", "endpoints": {"cloud": "https://eu.api.csod.com/"}};',
        "rec-job-search": JS({"data": {"requisitions": [
            {"displayJobTitle": "Climate Finance Officer", "requisitionId": 77,
             "locations": [{"city": "Paris", "country": "FR"}]}]}})}
r = lit("csod", "afd.csod.com|5", CSOD)
verifie("csod : API du contexte appelee", APPELS[1], "https://eu.api.csod.com/rec-job-search/external/jobs")
verifie("csod : offre", (r[0]["titre"], r[0]["location"]), ("Climate Finance Officer", "Paris, FR"))
verifie("csod : lien de fiche", r[0]["url"], "https://afd.csod.com/ux/ats/careersite/5/home/requisition/77?c=afd")
r = lit("csod", "afd.csod.com|5", {"/ux/ats/careersite/": "<html>pas de contexte</html>"})
verifie("csod : sans jeton, rien et pas d'appel API", (r, len(APPELS)), ([], 1))

# ── iCIMS : pagination jusqu'a une page sans nouveaute ──
CARTE = ('<li class="iCIMS_JobCardItem"><a href="https://careers-msci.icims.com/jobs/{n}/x/job?in_iframe=1" '
         'title="{n} - {t}">x</a><span>Job Locations</span> </dt> <dd class="x"><span > Paris </span></li>')
ICIMS = CARTE.format(n=1, t="ESG Research Analyst") + CARTE.format(n=2, t="Software Engineer")
r = lit("icims", "careers-msci.icims.com", ICIMS)
verifie("icims : filtre et lien sans iframe", [(o["titre"], o["url"]) for o in r],
        [("ESG Research Analyst", "https://careers-msci.icims.com/jobs/1/x/job")])
verifie("icims : arret quand la page n'apporte rien de neuf", len(APPELS), 2)
verifie("icims : lieu", r[0]["location"], "Paris")

# ── Choisir le service public : employeur financier OU intitule ESG ──
def carte_csp(href, titre, employeur):
    return (f'<li class="fr-col-12 item"><h3 class="fr-card__title"><a\n href="{href}">{titre}</a></h3>'
            f'<ul><li><span class="sr-only">Employeur : </span> {employeur} </li>'
            f'<li><span class="sr-only">Localisation : </span> Paris </li></ul>')
CSP = (carte_csp("/o/1", "Analyste financier", "Caisse des Dépôts")
       + carte_csp("/o/2", "Chargé de mission climat", "Commune de Trifouillis")
       + carte_csp("/o/3", "Chargé de mission RSE", "Commune de Trifouillis"))
APPELS.clear(); J.INCIDENTS.clear(); J._get_borne = route(CSP)
r = J.fetch_service_public()
verifie("service public : employeur financier ou intitule ESG", sorted(o["url"] for o in r), ["/o/1", "/o/3"])
verifie("service public : employeur et lieu lus", (r[0]["entreprise"], r[0]["location"]), ("Caisse des Dépôts", "Paris"))

# ── Refus : 403 compte un incident, 404 se tait ──
r = lit("talentbrew", "careers.moodys.com/en|49841", "", 403)
verifie("403 : rien", r, [])
verifie("403 : incident compte", dict(J.INCIDENTS.get("ats:talentbrew", {})), {"HTTP 403": 1})
r = lit("peoplesoft", "erecruitment.eib.org/psc/hr/EIBJOBS/CAREERS", "", 404)
verifie("404 : rien", r, [])
verifie("404 : silence", dict(J.INCIDENTS.get("ats:peoplesoft", {})), {})
r = lit("gogenerali", "gogenerali.com", "<html>pas du json</html>")
verifie("reponse illisible : rien, exception comptee", (r, dict(J.INCIDENTS.get("ats:gogenerali", {}))),
        ([], {"JSONDecodeError": 1}))

# ── LinkedIn : un 429 s'attend et reprend la MEME page ; 403/999 arretent tout ──
CARTE_LI = ('<li><div class="base-card"><a href="https://fr.linkedin.com/jobs/view/42?trk=x">'
            '<span class="sr-only">Sustainable Finance Analyst</span></a>'
            '<h4 class="base-search-card__subtitle"><a>Societe</a></h4>'
            '<span class="job-search-card__location">Paris</span></div></li>')


class RepLI(Rep):
    def __init__(self, corps, statut=200, entetes=None):
        super().__init__(corps, statut)
        self.headers = entetes or {}


def sequence(*reps):
    """Doublure qui rend les reponses dans l'ordre, puis la derniere pour toujours."""
    reste = list(reps)

    def envoi(_httpx, url, **kw):
        APPELS.append(url)
        return reste.pop(0) if len(reste) > 1 else reste[0]
    return envoi


PAUSES = []
DECALAGE = [0]                                   # temps ecoule hors pauses
J._dormir = PAUSES.append
J._horloge = lambda: sum(PAUSES) + DECALAGE[0]   # le temps n'avance que par les pauses
J.LI_PAUSE = 0


def li(*reps, mots=("esg",), lieux=None):
    APPELS.clear(); PAUSES.clear(); J.INCIDENTS.clear(); DECALAGE[0] = 0
    J.KEYWORDS = list(mots)
    J._get_borne = sequence(*reps)
    return J.scan_linkedin(lieux=lieux or {"France": 1})


r = li(RepLI("", 429), RepLI(CARTE_LI))
verifie("linkedin 429 : la page est redemandee apres la pause", (len(r), len(APPELS)), (1, 2))
verifie("linkedin 429 : pause de 60 s sans Retry-After", [p for p in PAUSES if p], [60])
verifie("linkedin 429 : compte en incident", dict(J.INCIDENTS["linkedin_http"]), {429: 1})
r = li(RepLI("", 429, {"Retry-After": "7"}), RepLI(CARTE_LI))
verifie("linkedin 429 : Retry-After respecte", [p for p in PAUSES if p], [7])
r = li(RepLI("", 429, {"Retry-After": "86400"}), RepLI(CARTE_LI))
verifie("linkedin 429 : Retry-After plafonne", [p for p in PAUSES if p], [240])
r = li(RepLI("", 429), RepLI("", 429), RepLI(CARTE_LI))
verifie("linkedin 429 : pauses doublees", [p for p in PAUSES if p], [60, 120])
r = li(RepLI("", 429), mots=("esg", "csrd", "isr"))
verifie("linkedin 429 persistant : arret a la duree max de la passe", sum(PAUSES) <= J.LI_DUREE_MAX, True)
verifie("linkedin 429 persistant : on a bien attendu avant d'abandonner", sum(PAUSES) > J.LI_DUREE_MAX - 240, True)
verifie("linkedin 429 persistant : plus aucun mot-cle apres l'arret",
        all("keywords=esg" in u for u in APPELS), True)
r = li(RepLI("", 999), mots=("esg", "csrd", "isr"), lieux={"France": 2, "Worldwide": 2})
verifie("linkedin 999 : une seule requete, aucune pause", (len(APPELS), [p for p in PAUSES if p]), (1, []))
r = li(RepLI("", 403), mots=("esg", "csrd"))
verifie("linkedin 403 : arret immediat", len(APPELS), 1)
r = li(RepLI("", 429), RepLI(CARTE_LI), RepLI("", 429), RepLI(CARTE_LI), mots=("esg", "csrd"))
verifie("linkedin : le compteur de pauses repart apres une page servie", [p for p in PAUSES if p], [60, 60])
r = li(RepLI(CARTE_LI), mots=("esg",))
verifie("linkedin sans incident : aucune pause de limite", [p for p in PAUSES if p], [])


def passe_trop_longue(_httpx, url, **kw):
    APPELS.append(url)
    DECALAGE[0] += J.LI_DUREE_MAX     # la premiere page a pris toute la duree
    return RepLI(CARTE_LI)


APPELS.clear(); PAUSES.clear(); J.INCIDENTS.clear(); DECALAGE[0] = 0
J.KEYWORDS = ["esg", "csrd", "isr"]; J._get_borne = passe_trop_longue
r = J.scan_linkedin(lieux={"France": 1})
verifie("linkedin : duree max depassee sans 429 -> mots-cles suivants sautes", (len(r), len(APPELS)), (1, 1))

print(f"\n{ok} ✅  {ko} ❌")
sys.exit(1 if ko else 0)
