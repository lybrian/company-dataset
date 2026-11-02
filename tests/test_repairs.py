import json

import pytest

from conftest import FakeResponse, FakeSession

from company_dataset import repairs, store
from company_dataset.http import HttpClient
from company_dataset.identity import CONFIRMED, UNRESOLVED


@pytest.fixture
def conn(tmp_path):
    c = store.connect(tmp_path / "s.db")
    c.execute("INSERT INTO sources(id, name, imported_at) VALUES (1, 'lastroundai', 't'), (2, 'kaleb', 't')")
    yield c
    c.close()


def board(c, ats, code, *, outcome="verified_live", jobs=3, provider=None, website=None, description=None, identity=None, basis="vendor_only", name=None, run="fullrun", lists=()):
    bid = store.board_id(c, ats, code)
    c.execute("INSERT INTO verifications(board_id, checked_at, origin, outcome, legacy_status, jobs_count, code_validated, provider_name, provider_website, provider_description)"
              " VALUES (?,?,?,?,?,?,?,?,?,?)", (bid, "2026-11-01T00:00:00Z", run, outcome, "valid", jobs, code, provider, website, description))
    if identity:
        c.execute("INSERT INTO identities(board_id, run, status, name, basis, conflicts, decided_at) VALUES (?,?,?,?,?,'','2026-11-01T00:00:00Z')", (bid, run, identity, name, basis))
    for i, (source, listed) in enumerate(lists):
        seq = c.execute("SELECT COUNT(*) FROM source_rows WHERE source_id=?", (source,)).fetchone()[0]
        c.execute("INSERT INTO source_rows(source_id, seq, row_ref, board_id, ats, code, name) VALUES (?,?,?,?,?,?,?)", (source, seq, f"r{i}", bid, ats, code, listed))
    return bid


def page(c, url, final=None, title="", status="ok", **extra):
    store.put_page(c, url, {"status": status, "final_url": final or url, "fetched_at": "2026-11-01T00:00:00Z", "title": title, **extra})


def identity_of(c, bid, run):
    return c.execute("SELECT status, name, basis FROM identities WHERE board_id=? AND run=?", (bid, run)).fetchone()


def test_backfill_marks_generic_redirect_boards_invalid_and_keeps_history(conn):
    gone = board(conn, "smartrecruiters", "1000mercis", outcome="verified_live_zero_jobs", jobs=0, identity=CONFIRMED, name="1000mercis")
    real = board(conn, "smartrecruiters", "10pearls", outcome="verified_live_zero_jobs", jobs=0, identity=CONFIRMED, name="10Pearls")
    jobs = board(conn, "smartrecruiters", "busy", identity=CONFIRMED, name="Busy")
    page(conn, "https://careers.smartrecruiters.com/1000mercis", "https://jobs.smartrecruiters.com", "SmartRecruiters Job Search")
    page(conn, "https://careers.smartrecruiters.com/10pearls", title="Careers at 10Pearls")
    page(conn, "https://careers.smartrecruiters.com/busy", "https://jobs.smartrecruiters.com")

    assert repairs.backfill_smartrecruiters_existence(conn, "fix", "2026-11-03T00:00:00Z") == {"invalidated": 1}

    assert store.latest_verifications(conn)[gone]["outcome"] == "invalid_identifier"
    assert conn.execute("SELECT COUNT(*) FROM verifications WHERE board_id=?", (gone,)).fetchone()[0] == 2
    assert identity_of(conn, gone, "fix")["status"] == "not_live"
    assert store.latest_verifications(conn)[real]["outcome"] == "verified_live_zero_jobs"
    assert store.latest_verifications(conn)[jobs]["outcome"] == "verified_live"
    # Re-running finds nothing new.
    assert repairs.backfill_smartrecruiters_existence(conn, "fix2", "2026-11-03T00:00:01Z") == {"invalidated": 0}


def test_reresolve_confirms_only_with_a_new_corroboration(conn):
    hubspot = board(conn, "greenhouse", "hubspotjobs", provider="HubSpot", identity=UNRESOLVED, name="HubSpot", lists=[(1, "HubSpot"), (2, "hubspotjobs")])
    echo = board(conn, "greenhouse", "attendi", provider="Attendi", identity=UNRESOLVED, name="Attendi", lists=[(2, "Attendi")])
    alone = board(conn, "greenhouse", "soloco", provider="Solo Co", identity=UNRESOLVED, name="Solo Co")
    dead = board(conn, "greenhouse", "goneco", outcome="dead_removed", jobs=None, provider="Gone Co", identity=UNRESOLVED, name="Gone Co", lists=[(1, "Gone Co")])
    other_ats = board(conn, "workable", "acmeco", provider="Acme Co", identity=UNRESOLVED, name="Acme Co", lists=[(1, "Acme Co")])

    stats = repairs.reresolve_identities(conn, "fix", ["fullrun"], "2026-11-03T00:00:00Z")

    assert stats["confirmed"] == 1
    assert stats["by_ats"] == {"greenhouse": 1}
    row = identity_of(conn, hubspot, "fix")
    assert (row["status"], row["name"]) == (CONFIRMED, "HubSpot")
    assert "list" in row["basis"]
    name = conn.execute("SELECT value, status, run FROM field_evidence WHERE board_id=? AND field='name'", (hubspot,)).fetchone()
    assert tuple(name) == ("HubSpot", "verified", "fix")
    for bid in (echo, alone, dead, other_ats):
        assert identity_of(conn, bid, "fix") is None


def test_reresolve_never_touches_confirmed_boards(conn):
    bid = board(conn, "greenhouse", "stripe", provider="Stripe", identity=CONFIRMED, name="Stripe", basis="vendor+homepage", lists=[(1, "Stripe")])
    assert repairs.reresolve_identities(conn, "fix", ["fullrun"], "2026-11-03T00:00:00Z")["confirmed"] == 0
    assert identity_of(conn, bid, "fix") is None


def test_reresolve_uses_the_stored_vendor_name_when_the_check_has_none(conn):
    # The hosted-page name was only kept on the identity row: raw pages are not stored.
    bid = board(conn, "smartrecruiters", "SSENSE1", outcome="verified_live_zero_jobs", jobs=0, identity=UNRESOLVED, name="SSENSE", lists=[(1, "SSENSE")])
    assert repairs.reresolve_identities(conn, "fix", ["fullrun"], "2026-11-03T00:00:00Z")["confirmed"] == 1
    assert identity_of(conn, bid, "fix")["name"] == "SSENSE"


def test_reresolve_does_not_treat_a_list_chosen_name_as_the_vendor(conn):
    bid = board(conn, "lever", "acmeworks", identity=UNRESOLVED, name="Acme Works", basis="insufficient_independent_evidence", lists=[(1, "Acme Works")])
    assert repairs.reresolve_identities(conn, "fix", ["fullrun"], "2026-11-03T00:00:00Z")["confirmed"] == 0
    assert identity_of(conn, bid, "fix") is None


def recovery(c, ats, code, website, *, method="reference", linkedin=None, **kw):
    bid = board(c, ats, code, identity=UNRESOLVED, **kw)
    c.execute("INSERT INTO identities(board_id, run, status, name, basis, conflicts, decided_at) VALUES (?,'recovery1',?,?,?,'','2026-11-01T01:00:00Z')",
              (bid, CONFIRMED, kw.get("name"), "provider_name+reference"))
    c.execute("INSERT INTO field_evidence(board_id, field, value, method, status, observed_at, run) VALUES (?,'website_url',?,?,'verified','t','recovery1')", (bid, website, method))
    if linkedin:
        c.execute("INSERT INTO field_evidence(board_id, field, value, method, status, observed_at, run) VALUES (?,'linkedin_url',?,'reference_linkedin','verified','t','recovery1')", (bid, linkedin))
    return bid


def test_reverify_keeps_a_site_that_names_the_company_and_adds_the_scheme(conn):
    bid = recovery(conn, "greenhouse", "buildops", "buildops.com", provider="BuildOps", name="BuildOps", linkedin="https://www.linkedin.com/company/buildops/")
    page(conn, "https://buildops.com", title="BuildOps | Commercial contractor software", description="BuildOps is the leading software platform for commercial contractors everywhere in the field.")
    stats = repairs.reverify_recovery(conn, "rv", "recovery1", HttpClient(session=FakeSession()), "2026-11-03T00:00:00Z")
    assert stats["kept"] == 1
    assert identity_of(conn, bid, "rv")["status"] == CONFIRMED
    fields = {r["field"]: r["value"] for r in conn.execute("SELECT field, value FROM field_evidence WHERE board_id=? AND run='rv' AND status='verified'", (bid,))}
    assert fields["website_url"] == "https://buildops.com"
    assert fields["linkedin_url"] == "https://www.linkedin.com/company/buildops"
    assert fields["description"].startswith("BuildOps is the leading")
    assert fields["name"] == "BuildOps"


def test_reverify_drops_a_namesake_domain_that_does_not_name_the_company(conn):
    # BigPicture's name join gave B-Stock a site that does not identify as B-Stock.
    bid = recovery(conn, "greenhouse", "bstocksolutions", "bstock.lk", provider="B-Stock", name="B-Stock")
    page(conn, "https://bstock.lk", title="Stock Management Lanka")
    stats = repairs.reverify_recovery(conn, "rv", "recovery1", HttpClient(session=FakeSession()), "2026-11-03T00:00:00Z")
    assert stats["kept"] == 0
    assert stats["dropped"]["homepage_does_not_name_company"] == 1
    assert identity_of(conn, bid, "rv") is None


def test_reverify_rejects_a_self_naming_site_with_nothing_tying_it_to_the_board(conn):
    # The page says "Apollo" and so does the vendor, but neither domain nor slug agree: a namesake.
    bid = recovery(conn, "greenhouse", "xyz123", "greekgods.example", provider="Apollo", name="Apollo")
    page(conn, "https://greekgods.example", title="Apollo")
    stats = repairs.reverify_recovery(conn, "rv", "recovery1", HttpClient(session=FakeSession()), "2026-11-03T00:00:00Z")
    assert stats["dropped"]["possible_namesake"] == 1
    assert identity_of(conn, bid, "rv") is None


def test_reverify_fetches_sites_never_checked_and_stores_the_page(conn):
    bid = recovery(conn, "lever", "fetchco", "fetchco.com", provider="FetchCo", name="FetchCo")
    html = "<html><head><title>FetchCo</title><meta name='description' content='FetchCo builds logistics software for regional freight carriers across the world.'></head></html>"
    session = FakeSession({"https://fetchco.com": FakeResponse(200, html, "https://fetchco.com")})
    stats = repairs.reverify_recovery(conn, "rv", "recovery1", HttpClient(session=session, sleep=lambda s: None, per_host_interval=0), "2026-11-03T00:00:00Z")
    assert session.calls == ["https://fetchco.com"]
    assert stats["fetched"] == 1
    assert json.loads(conn.execute("SELECT summary FROM pages WHERE url='https://fetchco.com'").fetchone()[0])["title"] == "FetchCo"
    assert identity_of(conn, bid, "rv") is not None


GOOD = "Acme builds warehouse robots for regional distribution centers across the whole of Europe."


def confirmed(c, ats, code, name, *, website=None, provider_description=None):
    bid = board(c, ats, code, provider=name, description=provider_description, identity=CONFIRMED, name=name, basis="vendor+list")
    c.execute("INSERT INTO field_evidence(board_id, field, value, method, status, observed_at, run) VALUES (?,'name',?,'m','verified','t','fullrun')", (bid, name))
    c.execute("INSERT INTO field_evidence(board_id, field, value, method, status, observed_at, run) VALUES (?,'ats_system',?,'m','verified','t','fullrun')", (bid, ats))
    c.execute("INSERT INTO field_evidence(board_id, field, value, method, status, observed_at, run) VALUES (?,'ats_code',?,'m','verified','t','fullrun')", (bid, code))
    if website:
        c.execute("INSERT INTO field_evidence(board_id, field, value, method, status, observed_at, run) VALUES (?,'website_url',?,'board_link+homepage_names_company','verified','t','fullrun')", (bid, website))
    return bid


def description_of(c, bid, run):
    return c.execute("SELECT value, method FROM field_evidence WHERE board_id=? AND run=? AND field='description'", (bid, run)).fetchone()


@pytest.mark.parametrize("text,accepted", [
    (GOOD, True),
    ("An Innovative and Tech-Powered Cross-Border Logistics Solutions company", True),
    ("Job openings at Planned Parenthood of Southern New England, Inc.", False),
    ("Grow your career in a supportive atmosphere and unlock your earning potential", False),
    ("Descubre nuestros vacantes disponibles en Centro America para ti", False),
    ("See all open roles at Acme Robotics and apply for the position today", False),
    ("Browse current vacancies and talent opportunities across our many sites", False),
])
def test_job_copy_is_rejected_from_board_and_careers_pages(text, accepted):
    assert repairs.usable_page_description(text) == (text if accepted else None)


def test_cached_recovery_prefers_vendor_text_then_homepage_then_board_page(conn):
    vendor = confirmed(conn, "greenhouse", "vendorco", "Vendor Co", provider_description=GOOD)
    home = confirmed(conn, "ashby", "homeco", "Home Co", website="https://homeco.com")
    page(conn, "https://homeco.com", title="Home Co", description=GOOD)
    meta = confirmed(conn, "breezy", "metaco", "Meta Co")
    page(conn, "https://metaco.breezy.hr", title="Meta Co", description=GOOD)
    filler = confirmed(conn, "lever", "fillerco", "Filler Co")
    page(conn, "https://jobs.lever.co/fillerco", title="Filler Co", description="Job openings at Filler Co, a company with many offices worldwide")
    nothing = confirmed(conn, "lever", "emptyco", "Empty Co")

    stats = repairs.recover_descriptions_cached(conn, "desc", ["fullrun"], "2026-11-03T00:00:00Z")

    assert stats["missing"] == 5
    assert stats["recovered"] == {"board_page_meta": 1, "homepage_meta": 1, "provider_description": 1}
    assert description_of(conn, vendor, "desc")["method"] == "provider_description"
    assert description_of(conn, home, "desc")["method"] == "homepage_meta"
    assert description_of(conn, meta, "desc")["method"] == "board_page_meta"
    assert description_of(conn, filler, "desc") is None
    assert description_of(conn, nothing, "desc") is None


def test_cached_recovery_leaves_boards_with_a_description_and_open_boards(conn):
    has = confirmed(conn, "greenhouse", "hasco", "Has Co", provider_description="Different text about this company and all of the things that it does.")
    conn.execute("INSERT INTO field_evidence(board_id, field, value, method, status, observed_at, run) VALUES (?,'description',?,'m','verified','t','fullrun')", (has, GOOD))
    unresolved = board(conn, "greenhouse", "openco", provider="Open Co", description=GOOD, identity=UNRESOLVED, name="Open Co")
    stats = repairs.recover_descriptions_cached(conn, "desc", ["fullrun"], "2026-11-03T00:00:00Z")
    assert stats["missing"] == 0
    assert description_of(conn, has, "desc") is None
    assert description_of(conn, unresolved, "desc") is None


def page_html(description):
    return f"<html><head><title>Net Co</title><meta name='description' content='{description}'></head></html>"


def network_client(script):
    return HttpClient(session=FakeSession(script), sleep=lambda s: None, per_host_interval=0, max_attempts=1)


def test_network_recovery_uses_the_homepage_first(conn):
    bid = confirmed(conn, "greenhouse", "netco", "Net Co", website="https://netco.com")
    client = network_client({"https://netco.com": FakeResponse(200, page_html(GOOD), "https://netco.com")})
    stats = repairs.recover_descriptions_network(conn, "desc", ["fullrun"], client, "2026-11-03T00:00:00Z")
    assert stats["recovered"] == {"homepage_meta": 1}
    assert description_of(conn, bid, "desc")["value"].startswith("Acme builds")
    assert client.session.calls == ["https://netco.com"]


def test_network_recovery_falls_back_to_about_and_careers_with_the_job_filter(conn):
    about = confirmed(conn, "greenhouse", "aboutco", "About Co", website="https://aboutco.com")
    careers = confirmed(conn, "greenhouse", "careersco", "Careers Co", website="https://careersco.com")
    jobs = confirmed(conn, "greenhouse", "jobsco", "Jobs Co", website="https://jobsco.com")
    client = network_client({
        "https://aboutco.com": FakeResponse(200, "<title>About Co</title>", "https://aboutco.com"),
        "https://aboutco.com/about": FakeResponse(200, page_html(GOOD), "https://aboutco.com/about"),
        "https://careersco.com": FakeResponse(200, "<title>Careers Co</title>", "https://careersco.com"),
        "https://careersco.com/careers": FakeResponse(200, page_html(GOOD), "https://careersco.com/careers"),
        "https://jobsco.com": FakeResponse(200, "<title>Jobs Co</title>", "https://jobsco.com"),
        "https://jobsco.com/careers": FakeResponse(200, page_html("Browse all current job openings at Jobs Co in our offices across the world"), "https://jobsco.com/careers"),
    })
    stats = repairs.recover_descriptions_network(conn, "desc", ["fullrun"], client, "2026-11-03T00:00:00Z")
    assert stats["recovered"] == {"about_page_meta": 1, "careers_page_meta": 1}
    assert description_of(conn, about, "desc")["method"] == "about_page_meta"
    assert description_of(conn, careers, "desc")["method"] == "careers_page_meta"
    assert description_of(conn, jobs, "desc") is None


def test_network_recovery_rejects_a_page_that_redirects_to_another_site(conn):
    bid = confirmed(conn, "greenhouse", "movedco", "Moved Co", website="https://movedco.com")
    client = network_client({"https://movedco.com": FakeResponse(200, page_html(GOOD), "https://otherbrand.example")})
    assert repairs.recover_descriptions_network(conn, "desc", ["fullrun"], client, "2026-11-03T00:00:00Z")["recovered"] == {}
    assert description_of(conn, bid, "desc") is None


def test_select_open_boards_covers_unresolved_and_confirmed_without_website_or_description(conn):
    from company_dataset.repairs import open_board_ids

    unresolved = board(conn, "lever", "openco", provider="Open Co", identity=UNRESOLVED, name="Open Co")
    bare = confirmed(conn, "lever", "bareco", "Bare Co")
    with_site = confirmed(conn, "lever", "siteco", "Site Co", website="https://siteco.com")
    dead = board(conn, "lever", "goneco", outcome="dead_removed", jobs=None, identity=UNRESOLVED, name="Gone Co")
    other = board(conn, "workable", "workco", identity=UNRESOLVED, name="Work Co")
    assert open_board_ids(conn, ["fullrun"]) == {unresolved, bare}
    assert with_site not in open_board_ids(conn, ["fullrun"])
    assert dead not in open_board_ids(conn, ["fullrun"]) and other not in open_board_ids(conn, ["fullrun"])
