from company_dataset.enrichment import Board
from company_dataset.reference import Reference
from company_dataset.resolve import resolve_board, slug_matches


def _board(ats="greenhouse", code="acme"):
    return Board(key=f"{ats}:{code}", ats=ats, code=code, region=None, careersite_url=f"https://board.example/{code}")


def _home(**kw):
    base = {"status": "ok", "final_url": "https://acme.com/", "site_name": "Acme", "title": "Acme",
            "description": "Acme makes anvils for the construction industry.", "linkedin_slugs": [], "board_refs": []}
    base.update(kw)
    return base


REF = Reference(
    by_domain={"acme.com": [{"name": "Acme Inc", "website": "acme.com", "handle": "company/acme-inc", "country": "US"}]},
    by_name={"acme": [{"name": "Acme", "website": "acme.com", "handle": "company/acme-inc", "country": "US"}]},
)


def test_vendor_website_homepage_and_reference_agree():
    outcome = {"company_name": "Acme", "website_url": "https://acme.com"}
    pages = {"https://acme.com": _home(linkedin_slugs=["partner", "acme-inc"])}
    res = resolve_board(_board(), outcome, pages, REF)
    assert res.website_url == "https://acme.com"
    assert res.linkedin_url == "https://www.linkedin.com/company/acme-inc"
    assert res.sources["linkedin_source"] == "homepage_and_reference"
    assert res.description.startswith("Acme makes anvils")
    assert res.country == "US" and res.sources["country_source"] == "reference_hq"


def test_unrelated_homepage_linkedin_is_not_used():
    outcome = {"company_name": "BrightHire", "website_url": "https://brighthire.com"}
    pages = {"https://brighthire.com": _home(final_url="https://brighthire.com/", linkedin_slugs=["the-debrief-podcast"])}
    res = resolve_board(_board(code="brighthire"), outcome, pages, Reference())
    assert res.linkedin_url == ""


def test_single_numeric_linkedin_id_on_own_homepage_accepted():
    outcome = {"company_name": "Agero", "website_url": "https://www.agero.com"}
    pages = {"https://www.agero.com": _home(final_url="https://www.agero.com/", linkedin_slugs=["9477"])}
    res = resolve_board(_board(code="agero"), outcome, pages, Reference())
    assert res.linkedin_url == "https://www.linkedin.com/company/9477"
    pages["https://www.agero.com"]["linkedin_slugs"] = ["9477", "1234"]
    assert resolve_board(_board(code="agero"), outcome, pages, Reference()).linkedin_url == ""


def test_name_match_website_needs_homepage_confirmation():
    outcome = {"company_name": "Acme"}
    confirmed = resolve_board(_board(), outcome, {"https://acme.com": _home()}, REF)
    assert confirmed.website_url == "https://acme.com"
    assert confirmed.sources["website_source"] == "reference_name_match_homepage_verified"
    unconfirmed = resolve_board(_board(), outcome, {"https://acme.com": _home(site_name="Parked Domain", title="Parked")}, REF)
    assert unconfirmed.website_url == ""
    assert unconfirmed.linkedin_url == ""


def test_greenhouse_intro_used_only_when_clean_and_no_homepage_description():
    outcome = {"company_name": "Acme", "description": "We are always looking for self-starting individuals to join."}
    assert resolve_board(_board(), outcome, {}, Reference()).description == ""
    outcome["description"] = "Acme is a payroll platform for restaurants across North America."
    assert resolve_board(_board(), outcome, {}, Reference()).sources["description_source"] == "greenhouse_board_intro"


def test_board_label_name_falls_back_to_source_name():
    outcome = {"company_name": "Open Roles"}
    res = resolve_board(_board(code="trillium"), outcome, {}, Reference(), source_name="Trillium Trading", source_name_origin="lastroundai")
    assert res.name == "Trillium Trading" and res.sources["name_source"] == "lastroundai"


def test_redirect_to_platform_host_drops_website():
    outcome = {"company_name": "Acme", "website_url": "https://acme.com"}
    pages = {"https://acme.com": _home(final_url="https://www.linkedin.com/company/acme")}
    assert resolve_board(_board(), outcome, pages, Reference()).website_url == ""


def test_slug_matches():
    assert slug_matches("iyzi-payments", "iyzico", "https://www.iyzico.com")
    assert slug_matches("deliverecthq", "Deliverect", None)
    assert not slug_matches("crocker-group", "CP Group", "https://cpgcre.com")
    assert not slug_matches("1252860", "Adaptive Biotechnologies", None)
