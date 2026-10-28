"""3.54: a site is recognised by the URL's host (CodeQL py/incomplete-url-substring-sanitization)."""

from jobhunter.links import hote, sur_site


def test_le_site_par_son_hote():
    assert sur_site("https://fr.linkedin.com/jobs/view/1", "linkedin.com")
    assert sur_site("linkedin.com/jobs/view/1", "linkedin.com")  # no scheme
    assert not sur_site("https://linkedin.com.example.org/x", "linkedin.com")
    assert not sur_site("https://example.org/?ref=linkedin.com", "linkedin.com")
    assert not sur_site("https://notlinkedin.com/", "linkedin.com")


def test_toutes_les_extensions_d_un_site():
    for u in (
        "https://fr.indeed.com/viewjob?jk=1",
        "https://www.indeed.fr/x",
        "https://uk.indeed.co.uk/",
    ):
        assert sur_site(u, "indeed."), u
    assert not sur_site("https://indeed-jobs.example.com/", "indeed.")
    assert not sur_site("https://example.indeed/", "indeed.")  # "indeed" as the extension


def test_sans_hote():
    assert hote(None) == "" and not sur_site("", "linkedin.com")
    assert hote("https://WWW.Example.org./a") == "www.example.org"
