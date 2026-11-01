"""Phase 1c: the two precision fixes from the pilot 3 review (data/pilots/pilot3/PHASE1B_REPORT.md).

1. Country/region-qualified names do not merge with differently qualified names on a shared key.
2. A website reached only because it links to the board must itself name the company.
"""
import pytest

from company_dataset import store
from company_dataset.identity import careers_branded_domain, cluster_companies, domain_compatible, geo_qualifiers
from company_dataset.normalize import clean_website
from company_dataset.pilot import official_landing, website_supported
from company_dataset.store_export import board_rows


def _row(name, site, ats="greenhouse", code=None, linkedin="", provider_id=""):
    return {"name": name, "website_url": site, "website_verified": True, "linkedin_url": linkedin, "ats_system": ats,
            "ats_code": code or name.lower().replace(" ", ""), "provider_identifier": provider_id}


def _groups(rows):
    return sorted(sorted(rows[i]["name"] for i in g) for g in cluster_companies(rows))


# 1. Geo-qualified identities ---------------------------------------------------------------

@pytest.mark.parametrize("name,geo", [
    ("KPMG Australia", {"au"}), ("KPMG", set()), ("Deloitte United Kingdom", {"uk"}), ("Deloitte UK LLP", {"uk"}),
    ("Ogilvy Health Canada", {"ca"}), ("Lennox International", set()), ("Bank of America", {"us"}), ("Acme Österreich GmbH", {"at"}),
])
def test_geo_qualifiers(name, geo):
    assert geo_qualifiers(name) == geo


@pytest.mark.parametrize("a,b,site", [
    ("KPMG Australia", "KPMG", "https://kpmg.com"),                 # pilot 3: smartrecruiters KPMGAustralia1 + pinpoint kpmg
    ("Deloitte UK", "Deloitte US", "https://www.deloitte.com"),
    ("Ogilvy Health Canada", "Ogilvy", "https://www.ogilvy.com"),
    ("Grant Thornton Ireland", "Grant Thornton", "https://www.grantthornton.com"),
])
def test_differently_qualified_names_do_not_merge_on_a_shared_domain(a, b, site):
    assert _groups([_row(a, site, "smartrecruiters"), _row(b, site, "pinpoint")]) == sorted([[a], [b]])


def test_differently_qualified_names_do_not_merge_on_a_shared_linkedin_either():
    li = "https://www.linkedin.com/company/kpmg"
    assert len(_groups([_row("KPMG Australia", "", "smartrecruiters", linkedin=li), _row("KPMG", "", "pinpoint", linkedin=li)])) == 2


@pytest.mark.parametrize("a,b", [
    ("Acme UK", "Acme UK Ltd"), ("KPMG Australia", "KPMG Australia"), ("Acme", "Acme Inc"),
    ("Lennox", "Lennox International"), ("Bank of America", "Bank of America Corp"), ("Deloitte UK", "Deloitte UK LLP"),
])
def test_same_company_duplicates_still_merge(a, b):
    assert _groups([_row(a, "https://acme.example", "greenhouse"), _row(b, "https://acme.example", "lever")]) == [sorted([a, b])]


def test_the_same_provider_account_is_explicit_evidence_across_qualifiers():
    rows = [_row("Acme", "", "smartrecruiters", "acme1", provider_id="ACME"), _row("Acme UK", "", "smartrecruiters", "acme2", provider_id="acme")]
    assert _groups(rows) == [["Acme", "Acme UK"]]


def test_names_alone_still_never_merge():
    assert len(_groups([_row("Acme UK", ""), _row("Acme UK", "")])) == 2


# 2. Websites found through board ownership -----------------------------------------------

def _page(title, site_name="", refs=()):
    return {"status": "ok", "title": title, "site_name": site_name, "description": "", "board_refs": list(refs)}


# The five ownership websites from the pilot 3 review (stored page titles).
@pytest.mark.parametrize("site,title,site_name,name", [
    ("https://schluesselposition.de", "Du bist der Schlüssel! - Karriereseite der Stadt Dorsten", "Du bist der Schlüssel!", "Stadtverwaltung Dorsten"),
    ("https://montessori-lauf.de", "Montessori Campus Lauf und Altdorf – Vom Kinderhaus bis zum Abitur", "Montessori Lauf", "Montessori-Vereinigung Nürnberger Land e.V."),
    ("https://www.dunigroup.com", "Duni Group I Paper + Design DE I dunigroup.com", "Duni Group I Paper + Design DE I dunigroup.com", "Paper + Design GmbH Tabletop"),
    ("https://www.bn-biscuits.com", "Biscuits BN - Le goûter sourire à partager", "Biscuits BN", "pladis France"),
    ("https://www.vistrycareers.co.uk", "Jobs at Vistry - Vistry Careers", "Vistry Careers", "Vistry Group"),
])
def test_pilot3_ownership_websites_are_not_verified(site, title, site_name, name):
    assert website_supported(site, _page(title, site_name), [name]) is None


@pytest.mark.parametrize("site,title,name", [
    ("https://excellentair.de", "", "Excellent Air GmbH"),
    ("https://ssi.inc", "", "SSI"),
    ("https://www.fpc-global.com", "FPC Global | End-to-End Digital Building Solutions", "Facility Performance Consulting Limited"),
    ("https://www.vian.ai", "Home Page", "Vianai Systems"),
    ("https://kisotechnology.com", "", "Kiso Technology"),
    ("https://www.herrs.com", "Snacks - Herr's Forever Good | Herr Foods Inc.", "Herr Foods Inc."),  # the page names itself
])
def test_ownership_websites_that_name_the_company_are_kept(site, title, name):
    assert website_supported(site, _page(title), [name])


def test_root_redirecting_to_its_own_careers_host_is_kept():
    site, on_careers = official_landing("https://silverspin.com", "https://careers.silverspin.com")
    assert (site, on_careers) == ("https://silverspin.com", True)
    assert website_supported(site, _page("Careers | Silverspin"), ["Silverspin"])


@pytest.mark.parametrize("url", ["https://moncler.jibeapply.com", "https://acme.careerplug.com", "https://jobs.zohorecruit.com"])
def test_careers_platforms_are_not_company_websites(url):
    assert clean_website(url) is None


@pytest.mark.parametrize("url,names,branded", [
    ("https://www.vistrycareers.co.uk", ["Vistry Group"], True),
    ("https://werkenbijedco.nl", ["EDCO"], True),
    ("https://www.jobsatpeligoni.com", ["Peligoni"], True),
    ("https://www.invitejobs.nl", ["Invite"], True),
    ("https://www.careerbuilder.com", ["CareerBuilder"], False),       # the company's own name carries the word
    ("https://www.joinhoney.com", ["Honey"], False),
    ("https://careers.acme.com", ["Acme"], False),                      # a careers host, resolved to acme.com elsewhere
    ("https://www.hiringthing.com", ["HiringThing"], False),
])
def test_careers_branded_domains(url, names, branded):
    assert careers_branded_domain(url, names) is branded


@pytest.mark.parametrize("site,name,ok", [
    ("https://fcs.wfs.aero", "FCS Frankfurt Cargo Services GmbH", False),   # the parent's domain
    ("https://www.americansafetycouncil.com", "Certus", False),
    ("https://www.oldcreeklodgegatlinburg.com", "Oaktenn", False),
    ("https://nomic.bio", "nomic", True),
    ("https://whetstone.cc", "Whetstone Research", True),
])
def test_domain_compatible(site, name, ok):
    assert domain_compatible(site, name) is ok


# Offline re-check of stored evidence --------------------------------------------------------

def test_export_drops_an_ownership_website_and_what_came_from_it_but_keeps_identity(tmp_path):
    conn = store.connect(tmp_path / "s.db")
    bid = store.board_id(conn, "recruitee", "pladisfrance")
    conn.execute("INSERT INTO verifications(board_id, checked_at, origin, endpoint, http_status, outcome, jobs_count) VALUES (?,?,?,?,?,?,?)",
                 (bid, "2026-11-01T00:00:00Z", "r1", "https://api", 200, "verified_live", 3))
    conn.execute("INSERT INTO identities(board_id, run, status, name, basis, decided_at) VALUES (?,?,?,?,?,?)",
                 (bid, "r1", "identity_confirmed", "pladis France", "vendor+board_ownership", "t"))

    def ev(field, value, method, url=None, text=None):
        conn.execute("INSERT INTO field_evidence(board_id, field, value, method, evidence_url, evidence_text, status, observed_at, run)"
                     " VALUES (?,?,?,?,?,?,?,?,?)", (bid, field, value, method, url, text, "verified", "t", "r1"))

    ev("name", "pladis France", "identity:vendor+board_ownership")
    ev("careersite_url", "https://pladisfrance.recruitee.com", "hosted_page_fetch", "https://pladisfrance.recruitee.com")
    ev("website_url", "https://www.bn-biscuits.com", "board_link+homepage_names_company", "https://www.bn-biscuits.com", "links_to_board:recruitee:pladisfrance")
    ev("linkedin_url", "https://www.linkedin.com/company/bn-biscuits", "homepage_link")
    ev("description", "Le goûter.", "homepage_meta")
    ev("country", "FR", "bigpicture_by_verified_domain")
    store.put_page(conn, "https://www.bn-biscuits.com", _page("Biscuits BN - Le goûter sourire à partager", "Biscuits BN", ["recruitee:pladisfrance"]))
    conn.commit()
    (row,) = board_rows(conn, "r1")
    assert row["identity_status"] == "identity_confirmed" and row["company_name"] == "pladis France"
    assert (row["website_url"], row["linkedin_url"], row["description"], row["country"]) == ("", "", "", "")
    assert row["careersite_evidence"].startswith("verified")
    assert row["_website_rule"].startswith("board_link_only")


# Phase 1d: last refinements before the methodology freeze ----------------------------------

@pytest.mark.parametrize("basis,declared,site,ok", [
    ("ashby_public_website", "https://fomo.family", "https://fomo.family", True),
    ("lever_home_page_link", "https://sia.tech", "https://sia.tech", True),
    ("ashby_public_website", "https://fomo.family", "https://www.bn-biscuits.com", False),   # landed on another domain
    ("board_link", "https://www.bn-biscuits.com", "https://www.bn-biscuits.com", False),     # not a vendor settings field
    ("ashby_public_website", "https://acmecareers.com", "https://acmecareers.com", False),   # careers-branded stays rejected
    ("lever_home_page_link", "https://moncler.jibeapply.com", "https://moncler.jibeapply.com", False),
])
def test_website_declared_in_the_companys_own_ats_settings(basis, declared, site, ok):
    names = ["fomo Labs"] if "fomo" in declared else ["The Sia Foundation"]
    got = website_supported(site, _page("Home"), names, basis, declared)
    assert bool(got) is ok
    if ok:
        assert got.startswith(f"vendor_declared_website:{basis}=")


@pytest.mark.parametrize("site,name,ok", [
    ("https://my-headhunter.at", "Agentur Hablesreiter e.U. - my-headhunter.at", True),   # domain written in the name
    ("https://www.beledad.com", "Grupo Bel Edad", True),                                  # group word
    ("https://utec.edu.pe", "Universidad de Ingeniería y Tecnología - UTEC", True),       # set-off acronym
    ("https://www.bvg.de", "Berliner Verkehrsbetriebe (BVG)", True),
    ("https://blacknova.vc", "Black Nova Venture Capital Pty Ltd", True),                 # leading words joined
    ("https://www.blantonsair.com", "Blanton’s Air, Plumbing & Electric", True),
    # still rejected
    ("https://www.ibm.com", "Acme Consulting - an IBM partner", False),
    ("https://www.newyork.com", "York Partners", False),
    ("https://www.blackrock.com", "Black Nova Venture Capital", False),
    ("https://schluesselposition.de", "Stadtverwaltung Dorsten", False),
    ("https://www.sverigesskonhetscenter.se", "Skönhetsgruppen.", False),
])
def test_phase1d_domain_rules(site, name, ok):
    assert domain_compatible(site, name) is ok


@pytest.mark.parametrize("site,reg", [
    ("https://utec.edu.pe", "utec.edu.pe"), ("https://shop.acme.com.eg", "acme.com.eg"), ("https://ihub.co.ke", "ihub.co.ke"),
    ("https://www.acme.co.uk", "acme.co.uk"), ("https://careers.acme.de", "acme.de"), ("https://team.blue", "team.blue"),
])
def test_registrable_domain_under_country_second_levels(site, reg):
    from company_dataset.identity import registrable_domain
    assert registrable_domain(site) == reg
