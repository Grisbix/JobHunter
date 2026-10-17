#!/usr/bin/env python3
"""test_audit_dispo.py — audit de disponibilite, sans reseau.

Couvre : la boucle sur limite de debit (429 -> pause -> reprise), l'arret net
sur refus d'entree (403), la verification par le canal de collecte (recherche
APEC, sitemap WTJ) et la regle « plus servie par sa source ».

Run : python test_audit_dispo.py
"""

import _profil_test  # noqa: F401  — les tests tournent sur le profil d'exemple

import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, __import__("os").path.dirname(__file__))

import audit_dispo as a
import job_sources

ok = ko = 0


def ck(nom, cond):
    global ok, ko
    if cond:
        ok += 1
        print(f"✅ {nom}")
    else:
        ko += 1
        print(f"❌ {nom}")


a.sauver_etat = lambda e: None
dormi = []
a.time.sleep = lambda s: dormi.append(s)


class R:
    def __init__(self, code, txt=""):
        self.status_code, self.text, self.headers = code, txt, {}


def scenario(reponses):
    it = iter(reponses)

    class Client:
        def __init__(self, **k):
            pass

        def get(self, url):
            return next(it)

    import httpx

    httpx.Client = Client


def offre(i, url=None, poste="P", **k):
    o = {
        "entreprise": f"E{i}",
        "poste": poste,
        "url": url or f"https://www.linkedin.com/jobs/view/12345{i}0",
    }
    o.update(k)
    return o


OUVERTE = R(200, "x" * 500)
FERMEE = R(200, "closed-job" + "x" * 500)
JOUR = "2026-10-02"

# ── 1. limite de debit : attendre, reprendre ──────────────────────────────────
offres = [offre(i) for i in range(3)]
dormi.clear()
etat = {}
scenario([OUVERTE, R(429), R(429), R(429), OUVERTE, FERMEE])
fini = a.verifier(offres, etat, 4, JOUR)
ck("429 x3 : la passe reprend et finit", fini)
ck("429 x3 : une pause longue de 15 min", 900 in dormi)
ck("429 x3 : aucune offre perdue", [v[0] for v in etat.values()] == ["OK", "OK", "FERMEE"])

dormi.clear()
etat = {}
scenario([OUVERTE] + [R(429)] * 50)
fini = a.verifier(offres, etat, 2, JOUR)
ck("429 sans fin : rend la main au bout de --pauses", not fini)
ck("429 sans fin : pauses 15 puis 30 min", [s for s in dormi if s > 30] == [900, 1800])

dormi.clear()
etat = {}
scenario([R(403)] * 5)
fini = a.verifier(offres, etat, 4, JOUR)
ck("403 : arret immediat", not fini)
ck("403 : aucune pause, pas de boucle", not [s for s in dormi if s > 1])


# ── 2. APEC : retrouver l'offre par la recherche qui l'a trouvee ─────────────
def apec(num, poste="Analyste ESG"):
    return offre(
        num,
        url=f"https://www.apec.fr/candidat/recherche-emploi.html/emploi/detail-offre/{num}",
        poste=poste,
    )


def file_et_etat(offres_):
    return offres_, {a.queue_io.oid(o): [None, "HTTP 403", o["url"], JOUR] for o in offres_}


reponses = {}
job_sources._apec_page = lambda mot, debut: reponses[mot]
job_sources.APEC_PAUSE = 0

q, etat = file_et_etat(
    [apec("111W", "Poste vivant"), apec("222W", "Poste ferme"), apec("333W", "Analyste")]
)
reponses = {
    "Poste vivant": ([{"numeroOffre": "999W"}, {"numeroOffre": "111W"}], 2),
    "Poste ferme": ([{"numeroOffre": "999W"}], 1),
    "Analyste": ([{"numeroOffre": f"{i}X"} for i in range(50)], 400),
}
a.par_la_source(q, etat, JOUR, "2026-09-25")
st = {o["poste"]: etat[a.queue_io.oid(o)][0] for o in q}
ck("APEC : revue dans la recherche -> OK", st["Poste vivant"] == "OK")
ck("APEC : absente d'une recherche complete -> retiree", st["Poste ferme"] == "FERMEE_SOURCE")
ck("APEC : absente d'une recherche tronquee -> indecis, pas retiree", st["Analyste"] is None)

q, etat = file_et_etat([apec(f"{i}0W", f"T{i}") for i in range(6)])
appels = []


def refus(mot, debut):
    appels.append(mot)
    return None, 0


job_sources._apec_page = refus
a.par_la_source(q, etat, JOUR, "2026-09-25")
ck("APEC 403 : arret au 3e refus d'affilee", len(appels) == job_sources.APEC_ABANDON)
ck("APEC 403 : rien n'est tranche", all(v[0] is None for v in etat.values()))

# ── 3. WTJ : le sitemap liste ce qui est en ligne ────────────────────────────
U = "https://www.welcometothejungle.com/fr/companies/x/jobs/"
q, etat = file_et_etat([offre(1, url=U + "en-ligne"), offre(2, url=U + "retiree")])
a._wtj_urls = lambda: {(U + "en-ligne").lower()} | {f"u{i}" for i in range(20000)}
a.par_la_source(q, etat, JOUR, "2026-09-25")
ck("WTJ : au sitemap -> OK", etat[a.queue_io.oid(q[0])][0] == "OK")
ck("WTJ : absente du sitemap -> retiree", etat[a.queue_io.oid(q[1])][0] == "FERMEE_SOURCE")

q, etat = file_et_etat([offre(1, url=U + "x")])
a._wtj_urls = lambda: None
a.par_la_source(q, etat, JOUR, "2026-09-25")
ck("WTJ : sitemap illisible -> rien tranche", etat[a.queue_io.oid(q[0])][0] is None)

# ── 4. plus servie par sa source (Glassdoor, Indeed) ─────────────────────────
GD = "https://www.glassdoor.fr/job-listing/x"
vieille = offre(1, url=GD, vu_le="2026-08-20", source="glassdoor 2026-08-20")
revue = offre(2, url=GD + "2", vu_le="2026-10-01", source="glassdoor 2026-08-20")
canal_mort = offre(3, url="https://fr.indeed.com/viewjob?jk=1", source="Indeed 2026-08-01")
etat = {a.queue_io.oid(o): [None, "HTTP 403", o["url"], JOUR] for o in (vieille, revue, canal_mort)}
absente = ("2026-09-02", {"glassdoor.fr": True})
ck(
    "source vivante, offre plus vue depuis 30 j -> retiree",
    a.motif(vieille, etat, {}, "", absente) == "plus servie par sa source",
)
ck("offre revue recemment par sa source -> gardee", a.motif(revue, etat, {}, "", absente) is None)
ck("canal en panne -> on ne conclut rien", a.motif(canal_mort, etat, {}, "", absente) is None)
ck(
    "offre suivie -> jamais retiree",
    a.motif(vieille, etat, {a.queue_io.oid(vieille): {}}, "", absente) is None,
)
etat[a.queue_io.oid(vieille)][0] = "FERMEE_SOURCE"
ck(
    "FERMEE_SOURCE -> motif dedie",
    a.motif(vieille, etat, {}, "", None).startswith("retiree par sa source"),
)

# ── 5. choix des cibles : revue = ouverte, rythme selon l'age, ordre ─────────
import datetime

J = datetime.date(2026, 10, 2)
L = "https://www.linkedin.com/jobs/view/"
revue = offre(1, url=L + "1000001", vu_le="2026-10-01", fit=10)
jeune = offre(2, url=L + "1000002", source="linkedin 2026-09-28", fit=9)
vieille = offre(3, url=L + "1000003", source="linkedin 2026-08-20", fit=9)
basse = offre(4, url=L + "1000004", source="linkedin 2026-08-01", fit=3)
haute = offre(5, url=L + "1000005", source="linkedin 2026-09-30", fit=10)
q = [revue, jeune, vieille, basse, haute]
etat = {
    a.queue_io.oid(jeune): ["OK", "ouverte", jeune["url"], "2026-09-26"],  # vue il y a 6 j
    a.queue_io.oid(vieille): ["OK", "ouverte", vieille["url"], "2026-09-26"],
}
cibles = a.choisir_cibles(q, etat, {}, J)
noms = [o["entreprise"] for o in cibles]
ck("revue par la collecte : pas de requete", "E1" not in noms)
ck("revue par la collecte : marquee OK", etat[a.queue_io.oid(revue)][0] == "OK")
ck("offre jeune vue il y a 6 j : pas encore (10 j)", "E2" not in noms)
ck("offre vieille vue il y a 6 j : a refaire (5 j)", "E3" in noms)
ck("meilleur fit d'abord", noms[0] == "E5")
ck("fit faible en dernier", noms[-1] == "E4")
ck(
    "--frais fixe l'emporte sur l'age",
    "E2" in [o["entreprise"] for o in a.choisir_cibles(q, dict(etat), {}, J, frais=3)],
)

# ── 6. linkedin_desc signale une fiche fermee au passage ─────────────────────
import linkedin_desc as ld


class RepLI:
    def __init__(self, txt):
        self.status_code, self.text = 200, txt


class CliLI:
    def __init__(self, txt):
        self.txt = txt

    def get(self, *x, **k):
        return RepLI(self.txt)


ld.FERMEES.clear()
t = ld.description("42", CliLI("<div>No longer accepting applications</div>" + "x" * 500))
ck("linkedin_desc : fiche fermee -> pas de description", t == "")
ck("linkedin_desc : fiche fermee -> reperee", "42" in ld.FERMEES)

# ── 7. la sauvegarde du jour n'est jamais ecrasee ────────────────────────────
import pathlib
import tempfile

sys.argv = ["x"]
import pipeline_quotidien as pq

with tempfile.TemporaryDirectory() as tmp:
    tmp = pathlib.Path(tmp)
    (tmp / "apply_queue.json").write_text("matin", encoding="utf-8")
    vrai = pq.SCRIPTS
    pq.SCRIPTS = tmp
    try:
        c1 = pq.sauvegarder()
        (tmp / "apply_queue.json").write_text("soir", encoding="utf-8")
        pq.sauvegarder()
        ck(
            "sauvegarde : la premiere du jour gagne",
            (c1 / "apply_queue.json").read_text(encoding="utf-8") == "matin",
        )
    finally:
        pq.SCRIPTS = vrai

print(f"\n=== BILAN : {ok} ✅  /  {ko} ❌  ({ok}/{ok + ko}) ===")
sys.exit(1 if ko else 0)
