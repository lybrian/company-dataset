import csv
import gzip

from company_dataset.reference import Reference, build


def _write_bp(path, rows):
    with gzip.open(path, "wt", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["handle", "name", "website", "industry", "size", "type", "founded", "city", "state", "country_code"])
        w.writerows(rows)


def test_build_filters_to_wanted_domains_and_names(tmp_path):
    path = tmp_path / "bp.csv.gz"
    _write_bp(path, [
        ["company/acme", "Acme Inc", "acme.com", "", "", "", "", "", "", "US"],
        ["company/other", "Other", "other.com", "", "", "", "", "", "", "GB"],
        ["company/zen", "Zenith", "zenith.io", "", "", "", "", "", "", "CA"],
    ])
    ref = build(path, domains={"acme.com"}, names={"zenith"})
    assert set(ref.by_domain) == {"acme.com", "zenith.io"}
    assert ref.linkedin_slug("https://www.acme.com", "Acme") == "acme"
    assert ref.country("https://about.acme.com", None) == "US"


def test_ambiguous_domain_needs_matching_name():
    ref = Reference(by_domain={"pp.org": [
        {"name": "Planned A", "website": "pp.org", "handle": "company/a", "country": "US"},
        {"name": "Planned B", "website": "pp.org", "handle": "company/b", "country": "US"},
    ]})
    assert ref.linkedin_slug("https://pp.org", None) is None
    assert ref.linkedin_slug("https://pp.org", "Planned B") == "b"


def test_name_candidates_require_slug_agreement_and_uniqueness():
    ref = Reference(by_name={"atlas": [
        {"name": "Atlas", "website": "atlas.com", "handle": "", "country": "US"},
        {"name": "Atlas", "website": "atlasmoving.com", "handle": "", "country": "US"},
    ]})
    assert ref.name_candidates("Atlas", "atlas") == ["https://atlas.com"]
    assert ref.name_candidates("Atlas", "zzz") == []
    ref.by_name["atlas"].append({"name": "Atlas", "website": "atlas.co.uk", "handle": "", "country": "GB"})
    assert ref.name_candidates("Atlas", "atlas") == []
