"""Non-English descriptions, ownership evidence and the separate Workable file."""
import csv
import json

import pytest

from conftest import FakeResponse, FakeSession

from company_dataset import export, repairs, store
from company_dataset.http import HttpClient
from company_dataset.identity import CONFIRMED, UNRESOLVED
from company_dataset.sources import SOURCES, workable_discovery as wd

GERMAN = "Deloitte Österreich ist der führende Anbieter von Professional Services und unterstützt Unternehmen in ganz Österreich."
ENGLISH = "Acme builds warehouse robots for regional distribution centers across the whole of Europe."


@pytest.fixture
def conn(tmp_path):
    c = store.connect(tmp_path / "s.db")
    c.execute("INSERT INTO sources(id, name, imported_at) VALUES (1, 'kalil', 't')")
    yield c
    c.close()


def client(script=None):
    return HttpClient(session=FakeSession(script or {}), sleep=lambda s: None, per_host_interval=0, max_attempts=1)


def seed(c, ats, code, name, *, status=CONFIRMED, outcome="verified_live", jobs=2, description=ENGLISH, website=None, method="homepage_meta", provider=None, basis="vendor+homepage"):
    bid = store.board_id(c, ats, code)
    c.execute("INSERT INTO identities(board_id, run, status, name, basis, decided_at) VALUES (?,?,?,?,?,'2026-11-01T00:00:00Z')", (bid, "r", status, name, basis))
    c.execute("INSERT INTO verifications(board_id, checked_at, origin, endpoint, outcome, legacy_status, jobs_count, provider_name) VALUES (?,?,?,?,?,?,?,?)", (bid, "2026-11-01T00:00:00Z", "r", "e", outcome, "valid", jobs, provider))
    def ev(field, value, m="m"):
        c.execute("INSERT INTO field_evidence(board_id, field, value, method, status, observed_at, run) VALUES (?,?,?,?,'verified','t','r')", (bid, field, value, m))
    if status == CONFIRMED:
        ev("name", name)
        ev("ats_system", ats)
        ev("ats_code", code)
        if description:
            ev("description", description, method)
        if website:
            ev("website_url", website, "board_link+homepage_names_company")
    c.commit()
    return bid


def read(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_a_non_english_homepage_description_counts(conn, tmp_path):
    seed(conn, "greenhouse", "deloitteat", "Deloitte Österreich", description=GERMAN)
    export.build_export(conn, ["r"], tmp_path / "o")
    assert read(tmp_path / "o" / "companies_verified.csv")[0]["description"] == GERMAN


def test_cached_recovery_takes_a_non_english_homepage_description(conn):
    bid = seed(conn, "greenhouse", "at", "Firma GmbH", description=None, website="https://firma.at")
    store.put_page(conn, "https://firma.at", {"status": "ok", "final_url": "https://firma.at", "description": GERMAN})
    assert repairs.recover_descriptions_cached(conn, "d", ["r"], "2026-11-03T00:00:00Z")["recovered"] == {"homepage_meta": 1}
    assert conn.execute("SELECT value FROM field_evidence WHERE board_id=? AND run='d'", (bid,)).fetchone()[0] == GERMAN


def test_non_english_job_copy_from_a_board_page_is_still_not_used(conn):
    assert repairs.usable_page_description("Descubre nuestros vacantes disponibles en Centro America para ti y para todos") is None


def link_page(c, url, refs, title="Home"):
    store.put_page(c, url, {"status": "ok", "final_url": url, "title": title, "board_refs": refs})


def harvested(raw, name, tokens):
    (raw / name).mkdir(parents=True, exist_ok=True)
    (raw / name / "batches.jsonl").write_text(json.dumps({"sites": [], "domains": [], "aliases": 1, "tokens": tokens}) + "\n")


def apply(conn, raw, script=None):
    return repairs.apply_ownership_evidence(conn, "own", ["r"], raw, client(script), "2026-11-03T00:00:00Z")


def test_dns_alias_to_the_board_confirms_the_vendor_name(conn, tmp_path):
    bid = seed(conn, "breezy", "marlabs", "Marlabs", status=UNRESOLVED, provider="Marlabs", basis="vendor_only")
    harvested(tmp_path, "dns_cname", [["breezy", "marlabs", "", "cname:careers.marlabs.com->marlabs.breezy.hr"]])
    stats = apply(conn, tmp_path)
    assert stats["confirmed"] == {"dns_cname": 1}
    row = conn.execute("SELECT status, name, basis FROM identities WHERE board_id=? AND run='own'", (bid,)).fetchone()
    assert (row["status"], row["name"]) == (CONFIRMED, "Marlabs") and "board_ownership" in row["basis"]
    assert conn.execute("SELECT value FROM field_evidence WHERE board_id=? AND run='own' AND field='website_url'", (bid,)).fetchone()[0] == "https://marlabs.com"


def test_company_site_link_confirms_when_the_domain_names_the_company(conn, tmp_path):
    bid = seed(conn, "lever", "acmerobots", "Acme Robots", status=UNRESOLVED, provider="Acme Robots", basis="vendor_only")
    harvested(tmp_path, "company_sites", [["lever", "acmerobots", "", "https://acmerobots.com/careers"]])
    assert apply(conn, tmp_path)["confirmed"] == {"company_sites": 1}
    assert conn.execute("SELECT status FROM identities WHERE board_id=? AND run='own'", (bid,)).fetchone()[0] == CONFIRMED


def test_company_site_link_needs_the_site_to_be_that_company(conn, tmp_path):
    # A portfolio or partner site can link to someone else's board.
    bid = seed(conn, "lever", "acmerobots", "Acme Robots", status=UNRESOLVED, provider="Acme Robots", basis="vendor_only")
    harvested(tmp_path, "company_sites", [["lever", "acmerobots", "", "https://bigfund.example/careers"]])
    script = {"https://bigfund.example": FakeResponse(200, "<title>Big Fund | Investing</title>", "https://bigfund.example")}
    assert apply(conn, tmp_path, script)["confirmed"] == {}
    assert conn.execute("SELECT COUNT(*) FROM identities WHERE board_id=? AND run='own'", (bid,)).fetchone()[0] == 0


def test_company_site_with_a_different_domain_counts_when_the_site_names_itself(conn, tmp_path):
    seed(conn, "lever", "acmerobots", "Acme Robots", status=UNRESOLVED, provider="Acme Robots", basis="vendor_only")
    harvested(tmp_path, "company_sites", [["lever", "acmerobots", "", "https://arobots.example/careers"]])
    script = {"https://arobots.example": FakeResponse(200, "<title>Acme Robots | Home</title>", "https://arobots.example")}
    assert apply(conn, tmp_path, script)["confirmed"] == {"company_sites": 1}


def test_site_linking_to_many_boards_proves_nothing(conn, tmp_path):
    for i in range(4):
        seed(conn, "lever", f"acme{i}", f"Acme {i}", status=UNRESOLVED, provider=f"Acme {i}", basis="vendor_only")
    harvested(tmp_path, "company_sites", [["lever", f"acme{i}", "", "https://acme.com/careers"] for i in range(4)])
    assert apply(conn, tmp_path)["confirmed"] == {}


def test_stored_page_link_counts_only_on_a_domain_naming_the_company(conn, tmp_path):
    good = seed(conn, "ashby", "stay22", "Stay22", status=UNRESOLVED, provider="Stay22", basis="vendor_only")
    seed(conn, "ashby", "otherco", "Other Co", status=UNRESOLVED, provider="Other Co", basis="vendor_only")
    link_page(conn, "https://stay22.com", ["ashby:stay22"])
    link_page(conn, "https://news.example/article", ["ashby:otherco"])
    assert apply(conn, tmp_path)["confirmed"] == {"stored_pages": 1}
    assert conn.execute("SELECT board_id FROM identities WHERE run='own'").fetchone()[0] == good


def test_ownership_needs_a_vendor_name_and_a_live_open_board(conn, tmp_path):
    seed(conn, "breezy", "noname", None, status=UNRESOLVED, basis="insufficient_independent_evidence")
    seed(conn, "breezy", "deadco", "Dead Co", status=UNRESOLVED, outcome="dead_removed", provider="Dead Co", basis="vendor_only")
    seed(conn, "breezy", "doneco", "Done Co", provider="Done Co")
    harvested(tmp_path, "dns_cname", [["breezy", c, "", f"cname:careers.{c}.com->{c}.breezy.hr"] for c in ("noname", "deadco", "doneco")])
    assert apply(conn, tmp_path)["confirmed"] == {}


def test_primary_export_stays_on_five_ats_and_workable_gets_its_own_file(conn, tmp_path):
    seed(conn, "greenhouse", "acme", "Acme")
    seed(conn, "workable", "workco", "Work Co", website="https://workco.com")
    seed(conn, "workable", "nodesc", "No Desc", description=None)
    seed(conn, "workable", "dead", "Dead Co", outcome="dead_removed")
    report = export.build_export(conn, ["r"], tmp_path / "o", extra_ats=("workable",))
    assert [r["ats_code"] for r in read(tmp_path / "o" / "companies_verified.csv")] == ["acme"]
    assert [r["ats_code"] for r in read(tmp_path / "o" / "workable_companies.csv")] == ["workco"]
    assert list(read(tmp_path / "o" / "workable_companies.csv")[0]) == export.VERIFIED_COLUMNS
    assert not any(r["ats_system"] == "workable" for r in read(tmp_path / "o" / "companies_incomplete.csv"))
    assert report["boards_decided"] == 1
    assert report["extra_ats"]["workable"]["companies_verified"] == 1
    assert report["extra_ats"]["workable"]["companies_incomplete"] == 1
    sums = (tmp_path / "o" / "SHA256SUMS").read_text()
    assert "workable_companies.csv" in sums


def test_without_extra_ats_the_seven_files_are_unchanged(conn, tmp_path):
    seed(conn, "greenhouse", "acme", "Acme")
    export.build_export(conn, ["r"], tmp_path / "o")
    assert not (tmp_path / "o" / "workable_companies.csv").exists()


def test_report_says_when_fresh_checks_were_skipped_and_how_old_checks_are(conn, tmp_path):
    seed(conn, "greenhouse", "acme", "Acme")
    report = export.build_export(conn, ["r"], tmp_path / "o")
    assert report["fresh_checks"]["run"] is False
    assert report["fresh_checks"]["last_checked_by_date"] == {"2026-11-01": 1}


@pytest.mark.parametrize("host,code", [("acme.workable.com", "acme"), ("www.workable.com", None), ("resources.workable.com", None), ("a.b.workable.com", None), ("acme.notworkable.com", None)])
def test_workable_host(host, code):
    assert wd.board_from_host(host) == code


def test_workable_discovery_keeps_only_workable(tmp_path):
    out = tmp_path / wd.META.name
    out.mkdir()
    (out / "subfinder.txt").write_text("acme.workable.com\nwww.workable.com\n")

    def search(path, **params):
        if params["q"] == wd.QUERIES[0] and params["page"] == 1:
            return {"items": [{"html_url": "https://github.com/o/r/blob/main/workable_slugs.json", "file_size": 5}]}
        return {"items": []}

    c = client({"https://raw.githubusercontent.com/o/r/main/workable_slugs.json": FakeResponse(200, json.dumps(["betaco", "https://apply.workable.com/gammaco/", "https://jobs.lever.co/notthis"]))})
    assert wd.harvest(tmp_path, c, search=search, sleep=lambda s: None)["boards"] == 3
    records, rejects = wd.parse(out / "tokens.csv")
    assert sorted(r.code for r in records) == ["acme", "betaco", "gammaco"] and rejects == []
    assert all(r.ats == "workable" for r in records)


def test_workable_source_is_registered():
    assert "workable_discovery" in {m.META.name for m in SOURCES}


def test_walking_workable_jobs_finds_each_employers_board_once_and_resumes(tmp_path):
    page1 = {"totalSize": 3, "nextPageToken": "T2", "jobs": [{"id": "j1", "company": {"id": "c1", "title": "Bask", "website": "http://bask.health", "description": "<p>x</p>"}},
                                                               {"id": "j2", "company": {"id": "c1", "title": "Bask"}}]}
    page2 = {"totalSize": 3, "nextPageToken": None, "jobs": [{"id": "j3", "company": {"id": "c2", "title": "No Link"}}]}
    c = client({wd.JOBS_API: FakeResponse(200, json.dumps(page1)), wd.JOBS_API + "?pageToken=T2": FakeResponse(200, json.dumps(page2)),
                wd.JOBS_API + "/j1": FakeResponse(200, json.dumps({"linkoutUrl": "https://apply.workable.com/bask-health/j/ABC/"})),
                wd.JOBS_API + "/j3": FakeResponse(200, json.dumps({"linkoutUrl": None}))})
    assert wd.walk_jobs(tmp_path, c, max_pages=1) == {"pages_this_run": 1, "employers": 1, "finished": False}
    assert wd.walk_jobs(tmp_path, c) == {"pages_this_run": 1, "employers": 2, "finished": True}
    assert wd.JOBS_API + "/j2" not in c.session.calls
    records, _ = wd.parse(tmp_path / wd.META.name / "tokens.csv")
    assert [r.code for r in records] == ["bask-health"] and records[0].name is None
    employers = [json.loads(line) for line in (tmp_path / wd.META.name / "employers.jsonl").read_text().splitlines()]
    assert [e["name"] for e in employers] == ["Bask", "No Link"]


def test_rebuild_merges_earlier_tokens_and_new_hits(tmp_path):
    out = tmp_path / wd.META.name
    out.mkdir()
    (out / "tokens.csv").write_text("ats,code,region,evidence\nworkable,acme,,u\n")
    (out / "hits.jsonl").write_text(json.dumps({"code": "ACME", "evidence": "x"}) + "\n" + json.dumps({"code": "beta", "evidence": "y"}) + "\n")
    assert wd.rebuild_tokens(tmp_path) == 2
