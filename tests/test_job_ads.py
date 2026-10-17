"""Finding a Greenhouse company's website from links in its own job ads."""
from company_dataset.enrichment import Board, content_sites, content_website_candidates, greenhouse_content_url
from company_dataset.reference import Reference
from company_dataset.resolve import resolve_board


def _job(html):
    return {"content": html}


def test_content_sites_counts_ads_not_links_and_drops_platforms():
    payload = {"jobs": [
        _job('&lt;a href="https://www.pandadoc.com/about"&gt;us&lt;/a&gt; <a href="https://www.pandadoc.com">x</a> <a href="https://www.e-verify.gov">ev</a>'),
        _job('<a href="https://www.pandadoc.com">x</a> <a href="https://www.linkedin.com/company/pandadoc">li</a>'),
    ]}
    assert content_sites(payload) == [["https://www.pandadoc.com", 2], ["https://www.e-verify.gov", 1]]


def test_candidates_replace_career_subdomains_and_skip_career_domains():
    board = Board(key="greenhouse:kick", ats="greenhouse", code="kickstarter", region=None, careersite_url="")
    page = {"content_sites": [["https://jobs.kickstarter.com", 5], ["https://careersatagoda.com", 3], ["https://www.kickstarter.com", 1]]}
    assert content_website_candidates(board, page) == [("https://kickstarter.com", 5), ("https://www.kickstarter.com", 1)]


def _gh(code):
    return Board(key=f"greenhouse:{code}", ats="greenhouse", code=code, region=None, careersite_url=f"https://job-boards.greenhouse.io/{code}")


def test_job_ad_site_accepted_when_slug_agrees_and_linked_from_two_ads():
    pages = {
        greenhouse_content_url("pandadoc"): {"status": "ok", "content_sites": [["https://www.pandadoc.com", 9]]},
        "https://www.pandadoc.com": {"status": "http_403"},
    }
    res = resolve_board(_gh("pandadoc"), {"company_name": "PandaDoc"}, pages, Reference())
    assert res.website_url == "https://www.pandadoc.com"
    assert res.sources["website_source"] == "greenhouse_job_ads_slug_match"


def test_job_ad_site_rejected_when_unrelated_and_unconfirmed():
    pages = {
        greenhouse_content_url("peakcreditunion"): {"status": "ok", "content_sites": [["https://www.e-verify.gov", 34], ["https://www.eeoc.gov", 34]]},
        "https://www.e-verify.gov": {"status": "ok", "final_url": "https://www.e-verify.gov/", "site_name": "E-Verify", "title": "E-Verify", "board_refs": []},
    }
    assert resolve_board(_gh("peakcreditunion"), {"company_name": "Peak Credit Union"}, pages, Reference()).website_url == ""


def test_job_ad_site_accepted_when_homepage_confirms_name():
    pages = {
        greenhouse_content_url("boulevard"): {"status": "ok", "content_sites": [["https://www.joinblvd.com", 1]]},
        "https://www.joinblvd.com": {"status": "ok", "final_url": "https://www.joinblvd.com/", "site_name": "Boulevard", "title": "Boulevard", "board_refs": [], "description": "Boulevard is the client experience platform for salons and spas."},
    }
    res = resolve_board(_gh("boulevard"), {"company_name": "Boulevard"}, pages, Reference())
    assert res.website_url == "https://www.joinblvd.com"
    assert res.description.startswith("Boulevard is the client")
