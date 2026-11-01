"""One test per defect found in the pilot 1 manual review (data/pilots/pilot1/PILOT1_FINDINGS.md)."""
import pytest

from company_dataset import careersite
from company_dataset.enrichment import clean_description, clean_name, is_auxiliary_board, is_english, is_test_board
from company_dataset.identity import (
    CONFIRMED, HOMEPAGE, MISMATCH, SOURCE_LIST, UNRESOLVED, VENDOR_API, VENDOR_PAGE,
    NameClaim, brand_segments, linkedin_compatible, names_compatible, resolve_identity,
)
from company_dataset.normalize import clean_website
from company_dataset.pilot import company_names_for_homepage, official_site, verify_homepage

LEVER = {"ats": "pinpoint", "code": "x"}


def _page(title="", site_name="", description="", refs=()):
    return {"status": "ok", "title": title, "site_name": site_name, "description": description, "board_refs": list(refs)}


# --- Wrong-entity websites --------------------------------------------------------------

def test_name_inside_a_marketing_title_does_not_verify_a_homepage():
    # smartthings -> samsung.com
    page = _page("Smart home with Samsung SmartThings | Samsung US")
    assert verify_homepage(page, LEVER, ["SmartThings"]) is None


def test_parent_company_homepage_does_not_verify_the_subsidiary():
    # beitzelcareers -> pillarinnovations.com
    page = _page("Solutions Driven. Customer Focused. | Pillar InnovationsPillar InnovationsPillar InnovationsBeitzel Corporation")
    assert verify_homepage(page, LEVER, ["Beitzel Corporation"]) is None


def test_board_page_brand_differing_from_vendor_name_cannot_pick_the_website():
    # etraveligroup-tripstack: vendor "Etraveli Group", board page og:site_name "Tripstack"
    res = {"board": {"ats": "teamtailor", "code": "etraveligroup-tripstack", "codes": ["etraveligroup-tripstack"], "region": None,
                     "names": [("kalil", "Etraveli Group")]},
           "validation": {"company_name": "Etraveli Group"},
           "board_extract": {"names": [("Tripstack", "og_site_name")], "websites": [], "linkedin_slugs": []}}
    names = company_names_for_homepage(res)
    assert "Tripstack" not in names
    assert verify_homepage(_page("TripStack", "TripStack"), res["board"], names) is None


@pytest.mark.parametrize("title,description", [
    ("WorkAndTravelGuide.com is for sale | HugeDomains", "Get this domain name before someone else does."),
    ("GREENTOWN.CO.UK", "Saw.com has successfully helped thousands of buyers acquire the perfect domain name. GREENTOWN.CO.UK is for sale"),
])
def test_parked_or_for_sale_pages_never_verify(title, description):
    assert verify_homepage(_page(title, title, description), LEVER, ["Work and Travel Guide", "Greentown"]) is None


def test_parking_marketplaces_are_not_company_websites():
    assert clean_website("https://www.hugedomains.com") is None
    assert clean_website("https://saw.com") is None


@pytest.mark.parametrize("site,expected", [
    ("https://career.knauf.com", "https://knauf.com"),
    ("https://careers.actalentservices.com", "https://actalentservices.com"),
    ("https://investor.lennox.com", "https://lennox.com"),
    ("https://careers.acme.co.uk", "https://acme.co.uk"),
    ("https://app.rwa.xyz", "https://rwa.xyz"),
    ("https://www.acme.com", "https://www.acme.com"),
    ("https://corporate.viamericas.com", "https://corporate.viamericas.com"),
])
def test_careers_investor_and_app_hosts_resolve_to_the_main_site(site, expected):
    assert official_site(site) == expected


def test_homepage_naming_itself_compatibly_still_verifies():
    assert verify_homepage(_page("Lennox | Heating & Cooling", "Lennox"), LEVER, ["Lennox International"])
    assert verify_homepage(_page("Find jobs", "Actalent Services"), LEVER, ["Actalent"])
    assert verify_homepage(_page("Home"), {"ats": "teamtailor", "code": "sospro"}, [], ) is None
    assert verify_homepage(_page("Home", refs=["teamtailor:sospro"]), {"ats": "teamtailor", "code": "sospro"}, [])


# --- LinkedIn ---------------------------------------------------------------------------

@pytest.mark.parametrize("slug,name,site,ok", [
    ("eyecare-partners.com", "EyeCare Associates", "https://www.webeca.com", False),   # parent's page
    ("pillar-innovations", "Beitzel Corporation", None, False),                        # parent's page
    ("trip-stack", "Etraveli Group", None, False),
    ("fortusadv", "Fortus", "https://www.fortus.co.uk", True),
    ("carbon60-networks", "Carbon60", "https://www.carbon60.com", True),
    ("athletic-training-solutions", "Athletic Training Solutions", "https://atshws.com", True),
    ("teal-healthco", "Teal Health", "https://www.getteal.com", True),
    ("viamericas-corporation", "Viamericas", None, True),
    # Known cost of precision: a translated page name is not accepted.
    ("swedish-film-institute", "Svenska Filminstitutet", "https://www.filminstitutet.se", False),
])
def test_linkedin_slug_must_name_the_company_or_its_domain(slug, name, site, ok):
    assert linkedin_compatible(slug, name, site) is ok


# --- Descriptions -----------------------------------------------------------------------

@pytest.mark.parametrize("text", [
    "https://atshws.com/wp-content/uploads/2026/09/ATS-SIzzle-with-Captions.mp4",
    "https://MBD-Video.s3.us-west-002.backblazeb2.com/ScrollingHeader.mp4https://example.com",
    "Get this domain name before someone else does. Quick and painless shopping. Affordable payment options available.",
    "Saw.com has successfully helped thousands of buyers acquire the perfect domain name. Interested in GREENTOWN.CO.UK?",
    "In this talk we explore how a strategic partnership between General Motors and FocalPoint improves positioning.",
    "Biden admin asks SCOTUS to dismiss appeals LOS ANGELES— Today marks the anniversary of the program's launch.",
])
def test_non_descriptions_are_rejected(text):
    assert clean_description(text) is None


def test_finnish_text_with_english_lookalike_words_is_not_english():
    fi = ("Usva on seitsemänpaikkainen lastensuojelun sijaishuollon erityistason tason asuinyksikkö noin 10–17-vuotiaille "
          "lapsille Kanta-Hämeessä, Jokioisilla. Henkilöstömitoituksemme on 1,3.")
    assert not is_english(fi)
    assert is_english("Payroll software for small businesses in Canada helps you pay your employees on time.")


def test_ordinary_descriptions_still_pass():
    d = "Export Development Canada (EDC) is Canada’s export credit agency, offering financing and insurance to exporters."
    assert clean_description(d) == d


# --- Names and boards -------------------------------------------------------------------

@pytest.mark.parametrize("raw", ["UNAVAILABLE", "starter-roundhouse.wpmudev.host", "n/a"])
def test_junk_vendor_names_are_not_names(raw):
    assert clean_name(raw, "careers-x") is None


@pytest.mark.parametrize("raw", ["RWA.xyz", "F2.ai", "Reo.Dev"])
def test_brand_names_that_look_like_domains_are_kept(raw):
    assert clean_name(raw, "zzz") == raw


def test_junk_vendor_name_does_not_cause_a_mismatch():
    # careers-scca: vendor name "UNAVAILABLE" made the board a mismatch against Fred Hutch.
    r = resolve_identity([NameClaim("UNAVAILABLE", VENDOR_API), NameClaim("Fred Hutchinson Cancer Center", SOURCE_LIST, "kalil")], code="careers-scca")
    assert r.status == UNRESOLVED


def test_boards_marked_old_and_staging_boards_are_not_companies():
    assert is_auxiliary_board("Fortus (old)")
    assert is_test_board("Staging Site Board", "staging")


# --- Name variants (conservative) -------------------------------------------------------

@pytest.mark.parametrize("a,b", [
    ("XXL Norge", "XXL"),
    ("deister UK", "deister electronic UK Ltd."),
    ("Pearl Abyss Europe", "Pearl Abyss Official Website"),
    ("Congres & Spa Hotel Mons", "Hotel Mons Congres & Spa"),
    ("Lennox", "Lennox International"),
    ("Charlie Health", "CharlieHealth"),
    ("Sun Auto Tire & Service", "Sun Auto Tire and Service"),
])
def test_reviewed_false_rejections_now_match(a, b):
    assert names_compatible(a, b)


@pytest.mark.parametrize("a,b", [
    ("Smart Working Solutions", "Software Development Outsourcing Solutions"),
    ("FLOWIT AG", "Home"),
    ("Maincode", "Matilda"),
    ("DU-HAR MAT AS", "NorgesGruppen"),
    ("Refraction Point, Inc.", "LimaCharlie Company"),
    ("SmartThings", "Samsung US"),
    ("SmartThings", "Smart home with Samsung SmartThings"),
    ("Patch", "Dispatch Health"),
    ("Apex", "Apex Systems"),
    ("BQ", "BQ Redovisning"),        # too short to call: stays unresolved
    ("SEI Investments", "SEIC"),
    ("Etraveli Group", "TripStack"),
])
def test_conservative_matching_rejects_different_or_unprovable_names(a, b):
    assert not names_compatible(a, b)


def test_identity_variants_confirm_with_vendor_and_homepage():
    r = resolve_identity([NameClaim("XXL Norge", VENDOR_API), NameClaim("XXL", HOMEPAGE)], code="xxlnorge")
    assert r.status == CONFIRMED and r.name == "XXL Norge"
    # A homepage naming a product ("Matilda") does not corroborate, and (Phase 1b) cannot contradict either.
    r = resolve_identity([NameClaim("Maincode", VENDOR_API), NameClaim("Matilda", HOMEPAGE)], code="maincode")
    assert r.status == UNRESOLVED


def test_brand_segments():
    assert brand_segments({"site_name": "Lennox", "title": "Lennox | Heating & Cooling"}) == ["Lennox", "Heating & Cooling"]


# --- Rippling names -----------------------------------------------------------------------

def test_rippling_next_data_company_name_and_job_ad_links():
    html = ('<script id="__NEXT_DATA__" type="application/json">{"x":"{{companyName}} has invited you",'
            '"companyName":"Community Resources for Justice","desc":"<a href=\\"https://www.crj.org/terms.pdf\\">t</a>"}</script>')
    x = careersite.extract(html, "https://ats.rippling.com/crjcareers/jobs")
    assert careersite.board_page_names(x, "crjcareers") == [("Community Resources for Justice", "next_data_company_name")]
    assert x["websites"][0][:2] == ("https://www.crj.org", "board_job_ad_link")
