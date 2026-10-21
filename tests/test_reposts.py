"""reposts: an offer back under a new address, and one text under two companies."""

import json

import pytest

from jobhunter.programs import reposts as rp
from jobhunter.storage import queue as queue_io

TEXTE = (
    "Au sein de la direction des risques, vous rejoignez une équipe de six analystes qui "
    "accompagne les métiers dans la mesure des risques climatiques physiques et de transition. "
    "Vous construisez les scénarios de stress test, suivez les indicateurs de la taxonomie "
    "européenne et préparez le reporting CSRD avec les équipes finance. Vous participez aux "
    "comités trimestriels, rédigez les notes de synthèse pour la direction générale et "
    "contribuez à l'amélioration continue des modèles internes. Profil : diplômé d'une école "
    "d'ingénieurs ou de commerce, première expérience en banque ou en conseil, maîtrise de "
    "Python et d'Excel, anglais courant. Poste basé à Paris, deux jours de télétravail."
)


def o(entreprise, poste, url, description=""):
    return {"entreprise": entreprise, "poste": poste, "url": url, "description": description}


def test_cle_ensemble_de_mots_sans_marqueur_de_genre():
    assert rp.cle("BNP Paribas", "Analyste ESG - H/F") == rp.cle(
        "BNP Paribas", "ESG Analyste (F/H)"
    )
    assert rp.cle("Acme", "Analyst - Paris") != rp.cle("Acme", "Analyst - Lyon")
    assert rp.cle("Acme", "Specialist I") != rp.cle("Acme", "Specialist II")


def test_adresse_linkedin_par_numero_quel_que_soit_le_pays():
    assert rp.adresse("https://fr.linkedin.com/jobs/view/analyste-esg-4012345678") == (
        rp.adresse("https://www.linkedin.com/jobs/view/4012345678/?trk=x")
    )
    assert rp.adresse("pas une adresse") is None


def test_republiee_seulement_un_autre_jour_et_sur_le_meme_site():
    hist = {}
    rp.mettre_a_jour(
        hist, [o("Acme", "Analyst", "https://acme.wd3.myworkdayjobs.com/x/job/A_1")], "2026-10-01"
    )
    # the same day, a second address: parallel openings, not a repost
    rp.mettre_a_jour(
        hist, [o("Acme", "Analyst", "https://acme.wd3.myworkdayjobs.com/x/job/A_2")], "2026-10-01"
    )
    h = hist[rp.cle("Acme", "Analyst")]
    assert rp.republications(h, "2026-10-02") == 0
    # a better link on another site (LinkedIn → employer): one offer
    rp.mettre_a_jour(
        hist, [o("Acme", "Analyst", "https://www.linkedin.com/jobs/view/4000000001")], "2026-10-05"
    )
    assert rp.republications(h, "2026-10-05") == 0
    # back on the employer's site under a new number, later: a repost
    rp.mettre_a_jour(
        hist, [o("Acme", "Analyst", "https://acme.wd3.myworkdayjobs.com/x/job/A_3")], "2026-10-12"
    )
    assert rp.republications(h, "2026-10-12") == 1
    # beyond 90 days, the old sightings no longer count
    assert rp.republications(h, "2027-01-08") == 0


def test_elaguer_oublie_le_vieux():
    hist = {}
    rp.mettre_a_jour(hist, [o("Acme", "Analyst", "https://acme.com/jobs/1")], "2026-01-01")
    rp.mettre_a_jour(hist, [o("Beta", "Analyst", "https://beta.com/jobs/1")], "2026-10-01")
    rp.elaguer(hist, "2026-10-21")
    assert list(hist) == [rp.cle("Beta", "Analyst")]


def test_empreinte_proches_et_courtes():
    a = rp.empreinte(TEXTE)
    b = rp.empreinte(TEXTE.replace("six analystes", "sept analystes"))
    assert len(a) == 16 and rp.similarite(a, b) >= rp.SEUIL
    assert rp.similarite(a, rp.empreinte("Tout autre chose. " * 40)) < rp.SEUIL
    assert rp.empreinte("Trop court.") == ""
    assert rp.empreinte("<p>" + "x" * 400 + "</p>") == ""  # one long token: no shingle


def test_meme_texte_autre_entreprise_et_doublon_de_groupe():
    offres = [
        o("Acme Energy", "Analyste climat", "https://acme.com/1", TEXTE),
        o("Cabinet Recrut", "Analyste climat", "https://recrut.fr/2", TEXTE),
        o("Acme", "Analyste climat (F/H)", "https://acme.fr/3", TEXTE),
        o("Autre", "Analyste", "https://autre.com/4", "Rien à voir. " * 40),
    ]
    sig = rp.signaux({}, offres, "2026-10-21")
    assert sig["Acme Energy|Analyste climat"] == "doublon : Acme · même texte : Cabinet Recrut"
    assert "même texte : Acme, Acme Energy" in sig["Cabinet Recrut|Analyste climat"]
    assert sig["Autre|Analyste"] == ""


@pytest.fixture
def racine(tmp_path, monkeypatch):
    data = tmp_path / "data"
    (data / "_backups" / "2026-10-15").mkdir(parents=True)
    file = data / "apply_queue.json"
    vieille = [o("Acme", "Analyst", "https://acme.com/jobs/1")]
    (data / "_backups" / "2026-10-15" / "apply_queue.json").write_text(
        json.dumps(vieille), encoding="utf-8"
    )
    actuelle = [
        o("Acme", "Analyst", "https://acme.com/jobs/2"),
        o("Beta", "Analyst", "https://beta.com/jobs/1"),
    ]
    file.write_text(json.dumps(actuelle), encoding="utf-8")
    monkeypatch.setattr(rp._racine, "scripts", lambda: data)
    monkeypatch.setattr(queue_io, "CHEMIN", file)
    return data


def test_main_amorce_par_les_sauvegardes_et_ecrit_le_signal(racine, capsys):
    assert rp.main(["--sauvegardes"]) == 0
    assert "1 republiée(s)" in capsys.readouterr().out
    file = {queue_io.oid(x): x for x in queue_io.charger()}
    assert file["Acme|Analyst"]["signal"] == "republiée ×1"
    assert "signal" not in file["Beta|Analyst"]
    assert (racine / rp.HISTORIQUE).exists()


def test_dry_n_ecrit_rien(racine):
    assert rp.main(["--dry", "--sauvegardes"]) == 0
    assert not (racine / rp.HISTORIQUE).exists()
    assert all("signal" not in x for x in queue_io.charger())
