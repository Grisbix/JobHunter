"""The desktop's background work in the web window (web/background.py), programs faked."""

import subprocess

import pytest

from jobhunter.web import background as bg


@pytest.fixture
def lances(monkeypatch):
    """Records the programs started; each returns what `sortie` says."""

    class Lances(list):
        code, sortie = 0, ""

    vu = Lances()

    def lancer(args, delai):
        vu.append(args[0])
        return subprocess.CompletedProcess(args, vu.code, vu.sortie, "")

    monkeypatch.setattr(bg, "_lancer", lancer)
    return vu


def test_les_descriptions_par_lots_tant_que_ca_avance(monkeypatch, lances):
    restes = iter([10, 4, 4, 4])
    monkeypatch.setattr(bg, "descriptions_manquantes", lambda: next(restes))
    f = bg.Fond(lambda: False)
    f.descriptions()
    assert lances == ["jobhunter.programs.scrape_desc", "jobhunter.programs.rescore_ats"]
    assert f.version == 1 and "+6 récupérées (4 restantes)" in f.messages[-1]["texte"]
    assert "descriptions" in f.prochain  # it helped: another batch
    f.descriptions()
    assert f.version == 1 and "descriptions" not in f.prochain  # nothing gained: stop


def test_plafond_de_lots(monkeypatch, lances):
    monkeypatch.setattr(bg, "descriptions_manquantes", lambda: 99)
    f = bg.Fond(lambda: False)
    f.lots = bg.LOT_DESCRIPTIONS
    f.descriptions()
    assert lances == []


def test_la_synchro_ne_dit_rien_quand_rien_ne_change(lances):
    f = bg.Fond(lambda: False)
    lances.sortie = (  # sync_docs' real summary, nothing changed
        "pdf créés: 0 · pdf resynchronisés: 0 · pdf orphelins: 3\n"
        "liens queue réparés: 0 · liens toujours cassés: 1\n"
        "✅ docx = source, pdf = dérivé — tout est aligné.\n"
    )
    f.sync()
    assert f.messages == [] and f.version == 0
    lances.sortie = "pdf créés: 2 · pdf resynchronisés: 0\nliens queue réparés: 1\n"
    f.sync()
    assert f.version == 1 and "2 pdf créés, 0 refaits, 1 liens" in f.messages[-1]["texte"]


def test_le_scan_au_plus_quatre_fois(monkeypatch, lances):
    monkeypatch.setattr("jobhunter.storage.queue.charger", lambda descriptions=False: [])
    f = bg.Fond(lambda: False)
    for _ in range(bg.SCANS_MAX):
        f.scan()
    assert lances.count("jobhunter.programs.scrape_jobs") == bg.SCANS_MAX
    assert f.prochain["scan"] == float("inf")


def test_rien_quand_une_tache_tourne_ni_sans_fond(monkeypatch):
    class Api(bg.FondApi):
        pass

    a = Api()
    a._tache = type("T", (), {"code": None})()
    assert a._occupe() is True
    monkeypatch.setenv("JOBHUNTER_SANS_FOND", "1")
    a.demarrer_fond()
    assert a._fond is None
    assert a.fond_etat()["messages"] == []


def test_la_version_suit_la_file(monkeypatch, tmp_path):
    from jobhunter.storage import applications, queue

    f = tmp_path / "apply_queue.json"
    f.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(queue, "CHEMIN", f)
    monkeypatch.setattr(applications, "CHEMIN", tmp_path / "absent.json")
    avant = bg.FondApi().fond_etat()["version"]
    import os

    os.utime(f, (1, 2_000_000_000))  # another program wrote the queue
    assert bg.FondApi().fond_etat()["version"] != avant


def test_demarrage_dit_si_la_mise_a_jour_a_abouti(monkeypatch):
    monkeypatch.setattr(
        "jobhunter.programs.update.confirmer_demarrage", lambda: "Mise à jour confirmée"
    )
    assert bg.FondApi().demarrage() == "Mise à jour confirmée"
