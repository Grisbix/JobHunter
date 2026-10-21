"""A copy of the posting, written once when the user applies (jobhunter.postings)."""

from jobhunter import postings

DESC = (
    "Vous rejoignez l'équipe climat.\n\nMissions : mesurer les risques physiques, "
    "préparer le reporting CSRD, suivre la taxonomie européenne et animer les comités. "
) * 3
OFFRE = {
    "entreprise": "Acme / Énergie",
    "poste": "Analyste climat (F/H)",
    "url": "https://acme.example/jobs/1",
    "localisation": "Paris",
    "description": DESC,
}


def test_nom_de_fichier_sur():
    assert postings.nom_fichier(OFFRE) == "Acme_Énergie_Analyste_climat_F_H"
    assert postings.nom_fichier({}) == "annonce"
    assert len(postings.nom_fichier({"poste": "x" * 300})) == 100


def test_archiver_ecrit_pdf_et_texte_une_seule_fois(tmp_path):
    p = postings.archiver(OFFRE, tmp_path, "2026-10-22")
    assert p == tmp_path / "Acme_Énergie_Analyste_climat_F_H.pdf" and p.stat().st_size > 1000
    txt = p.with_suffix(".txt").read_text(encoding="utf-8")
    assert txt.startswith("Entreprise : Acme / Énergie\nPoste : Analyste climat (F/H)\n")
    assert "Copie faite le : 2026-10-22" in txt and "taxonomie européenne" in txt
    # the posting changes later: the copy stays the version applied to
    postings.archiver({**OFFRE, "description": "autre " * 100}, tmp_path, "2026-11-01")
    assert "taxonomie" in p.with_suffix(".txt").read_text(encoding="utf-8")
    import fitz

    with fitz.open(p) as doc:
        assert "Analyste climat" in doc[0].get_text()


def test_description_trop_courte_reessayee_plus_tard(tmp_path):
    assert postings.archiver({**OFFRE, "description": "Court."}, tmp_path) is None
    assert not any(tmp_path.iterdir())


def test_a_archiver(tmp_path, monkeypatch):
    monkeypatch.setattr(postings, "dossier", lambda: tmp_path)
    b = {**OFFRE, "entreprise": "Beta"}
    c = {**OFFRE, "entreprise": "Gamma"}
    suivi = {"Acme / Énergie|x": {}, "Beta|x": {"s": "postulé"}, "Gamma|x": {"s": "mauvaise"}}
    oid = lambda o: f"{o['entreprise']}|x"  # noqa: E731
    assert postings.a_archiver([OFFRE, b, c], suivi, oid) == [b]
    postings.archiver(b)
    assert postings.a_archiver([OFFRE, b, c], suivi, oid) == []
    assert postings.existante(b) == tmp_path / "Beta_Analyste_climat_F_H.pdf"
