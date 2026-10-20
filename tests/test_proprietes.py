"""Properties that must hold for ANY input, checked on generated cases (Hypothesis).

The example tests check the cases we thought of; these look for the ones we did not.
When Hypothesis finds a counterexample, it shrinks it to the smallest failing input
and prints it: that input then becomes an ordinary regression test.

Invariants taken from the rules of the project, not invented for the occasion:
cleaning a title again changes nothing (refresh_letters reruns it), a tracking
parameter never makes two URLs different, the score stays in 1..10 and its decimal
part never moves the level, merging the same collection twice adds nothing, and an
offer of the tracker survives any merge.
"""

import json

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from jobhunter import documents as T
from jobhunter import sources as J
from jobhunter.scoring.fit import fit_detail
from jobhunter.sources.commun import _norm_url
from jobhunter.stockage import file as queue_io
from jobhunter.stockage import suivi as suivi_io

# Pieces of real titles: words, gender and contract mentions, separators. A title
# drawn from them looks like what the collection brings back, which finds more than
# random characters do.
MORCEAUX = [
    "Analyste",
    "ESG",
    "Chargé",
    "de",
    "mission",
    "Junior",
    "Finance",
    "Risk",
    "Analyst",
    "DAF",
    "LCB-FT",
    "H2-Power",
    "M&A",
    "(H/F)",
    "F/H",
    "(h/f/x)",
    "F/M/X",
    "CDI",
    "CDD",
    "Stage",
    "6 mois",
    "-",
    "–",
    ",",
    "|",
    ":",
    "#00137324",
    "Paris",
    "Zürich",
    "Île-de-France",
]
titres = st.lists(st.sampled_from(MORCEAUX), min_size=1, max_size=14).map(" ".join)


@given(titres)
def test_titre_nettoye_deux_fois_ne_change_plus(titre):
    une = T.titre_poste(titre)
    assert T.titre_poste(une) == une


@given(titres)
def test_titre_borne_et_sans_backspace(titre):
    r = T.titre_poste(titre)
    assert len(r) <= 80
    assert "\x08" not in r


segment = st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789-", min_size=1, max_size=8)
hotes = st.lists(segment, min_size=1, max_size=3).map(lambda p: ".".join(p) + ".com")
chemins = st.lists(segment, max_size=4).map(lambda p: "/" + "/".join(p))
params = st.dictionaries(st.sampled_from(["jk", "id", "ref", "lang", "page"]), segment, max_size=3)
traceurs = st.dictionaries(
    st.sampled_from(["utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term"]),
    segment,
    min_size=1,
    max_size=3,
)


def _url(hote, chemin, couples):
    qs = "&".join(f"{k}={v}" for k, v in couples)
    return f"https://{hote}{chemin}" + (f"?{qs}" if qs else "")


@given(hotes, chemins, params, traceurs)
def test_url_les_traceurs_ne_comptent_pas(hote, chemin, vrais, pistes):
    propre = _url(hote, chemin, vrais.items())
    pistee = _url(hote, chemin, [*vrais.items(), *pistes.items()])
    assert _norm_url(pistee) == _norm_url(propre)


@given(hotes, chemins, params.map(lambda d: list(d.items())), st.randoms())
def test_url_ordre_des_parametres_www_et_slash_final(hote, chemin, couples, hasard):
    melange = couples[:]
    hasard.shuffle(melange)
    a = _url(hote, chemin, couples)
    b = _url("www." + hote.upper(), chemin + "/", melange)
    assert _norm_url(a) == _norm_url(b)


@given(hotes, chemins, st.sampled_from(["jk", "id"]), segment, segment)
def test_url_les_vrais_identifiants_restent(hote, chemin, cle, v1, v2):
    if v1 != v2:
        assert _norm_url(_url(hote, chemin, [(cle, v1)])) != _norm_url(
            _url(hote, chemin, [(cle, v2)])
        )


mots_offre = st.sampled_from(
    [
        "ESG",
        "durabilité",
        "reporting",
        "CSRD",
        "finance",
        "analyste",
        "senior",
        "10 ans d'expérience",
        "3 years of experience",
        "Python",
        "commercial",
        "stage",
        "climat",
        "audit",
        "manager",
        "IA",
        "data",
        "vente",
    ]
)
textes = st.lists(mots_offre, max_size=40).map(" ".join)


@settings(max_examples=60, deadline=None)
@given(textes, titres)
def test_note_dans_ses_bornes_et_niveau_stable(texte, titre):
    fit, _ans, fin = fit_detail(texte, titre)
    assert 1 <= fit <= 10
    # fit_fin only orders offers WITHIN a level: its rounding must give back fit.
    assert round(fin) == fit
    assert abs(fin - fit) <= 0.5


entreprises = st.sampled_from(["Mirova", "Bpifrance", "Deloitte", "Axa", "Engie", "Sanofi"])
postes = st.sampled_from(
    [
        "Analyste ESG",
        "Chargé de mission RSE",
        "Analyste financier",
        "Consultant durabilité",
        "Data analyst ESG",
    ]
)
collectes = st.lists(
    st.tuples(entreprises, postes, st.integers(1, 40)), min_size=1, max_size=12
).map(
    lambda lignes: [
        J._mk(p, f"https://www.linkedin.com/jobs/view/{n}", e, location="Paris")
        for e, p, n in lignes
    ]
)


def _preparer(tmp_path, monkeypatch, offres=(), suivi=None):
    q = tmp_path / "q.json"
    q.write_text(json.dumps(list(offres), ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(J, "QUEUE", q)
    monkeypatch.setattr(J, "REJETS_TRI", tmp_path / "rej.json")
    monkeypatch.setattr(queue_io, "DESCRIPTIONS", tmp_path / "descriptions.json")
    monkeypatch.setattr(suivi_io, "CHEMIN", tmp_path / "suivi.json")
    (tmp_path / "suivi.json").write_text(json.dumps(suivi or {}), encoding="utf-8")
    return q


# A merge writes files: the temporary folder is shared by the generated cases, so
# each case starts by rewriting the queue and the tracker it uses.
_FICHIERS = settings(
    max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)


@_FICHIERS
@given(collectes)
def test_fusionner_deux_fois_n_ajoute_rien(tmp_path, monkeypatch, collecte):
    q = _preparer(tmp_path, monkeypatch)
    J.merge_into_queue([dict(o) for o in collecte])
    avant = queue_io.charger(q)
    assert avant  # the generated offers do enter the queue: the property is not empty
    bilan = J.merge_into_queue([dict(o) for o in collecte])
    apres = queue_io.charger(q)
    assert bilan["added"] == 0
    assert len(apres) == len(avant)
    ids = [queue_io.oid(x) for x in apres]
    assert len(ids) == len(set(ids))


@_FICHIERS
@given(collectes)
def test_une_offre_suivie_survit_a_toute_fusion(tmp_path, monkeypatch, collecte):
    suivie = {
        "entreprise": "Suivie SA",
        "poste": "Brand Design Intern",  # a title the noise filter rejects
        "statut": "Scan 2026-10-01",
        "url": "https://example.com/suivie",
        "fit": 3,
    }
    q = _preparer(
        tmp_path,
        monkeypatch,
        [suivie],
        {queue_io.oid(suivie): {"s": "postulé", "d": "2026-10-02"}},
    )
    J.merge_into_queue([dict(o) for o in collecte])
    assert queue_io.oid(suivie) in {queue_io.oid(x) for x in queue_io.charger(q)}
