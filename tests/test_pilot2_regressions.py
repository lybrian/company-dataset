"""Phase 1b: one test per defect from the pilot 2 review (data/pilots/pilot2/PHASE1_REPORT.md), plus
tests that the fixes do not introduce false matches."""
import csv
from pathlib import Path

import pytest

from company_dataset.enrichment import clean_name, is_auxiliary_board
from company_dataset.identity import (
    CONFIRMED, HOMEPAGE, MISMATCH, SOURCE_LIST, STRUCTURED, UNRESOLVED, VENDOR_API,
    NameClaim, linkedin_compatible, resolve_identity, strip_entity_code,
)
from company_dataset.pilot import board_ownership, official_landing

FIXTURE = Path(__file__).parent / "fixtures" / "linkedin_rejected_pilot2_labelled.csv"


# 1. Homepage segments support but never contradict; ownership counts --------------------

@pytest.mark.parametrize("vendor,segments", [
    ("Allen Motor Group", ["New and Used Car Dealer", "S England & The Midlands"]),
    ("DoveLewis Veterinary Emergency & Specialty Hospital", ["Exceptional Veterinary Care", "24/7 Animal Hospital"]),
    ("TA Realty LLC", ["Homepage"]),
    ("Highsoft", ["JavaScript charting library for web apps"]),
])
def test_homepage_taglines_never_make_a_mismatch(vendor, segments):
    claims = [NameClaim(vendor, VENDOR_API)] + [NameClaim(s, HOMEPAGE) for s in segments]
    assert resolve_identity(claims, code="x").status == UNRESOLVED


def test_wikidata_label_alone_cannot_contradict_the_vendor():
    r = resolve_identity([NameClaim("Highsoft", VENDOR_API), NameClaim("Highcharts", STRUCTURED, "wikidata")], code="highsoft")
    assert r.status == UNRESOLVED


def test_board_ownership_confirms_the_vendor_name():
    claims = [NameClaim("Allen Motor Group", VENDOR_API), NameClaim("New and Used Car Dealer", HOMEPAGE)]
    r = resolve_identity(claims, code="allenmotorgroup", board_ownership=True)
    assert (r.status, r.name, r.basis) == (CONFIRMED, "Allen Motor Group", ["vendor", "board_ownership"])


def test_a_discovery_list_naming_another_company_is_still_a_mismatch():
    # htccareers-touro: vendor "Hebrew Theological College", list "Touro University".
    r = resolve_identity([NameClaim("Hebrew Theological College", VENDOR_API), NameClaim("Touro University", SOURCE_LIST, "kalil")], code="htccareers-touro")
    assert r.status == MISMATCH
    # ...and ownership does not override a contradiction it can't explain? It does corroborate the vendor:
    # the company's own site linking to the board outranks a third-party list.
    r = resolve_identity([NameClaim("Hebrew Theological College", VENDOR_API), NameClaim("Touro University", SOURCE_LIST, "kalil")],
                         code="htccareers-touro", board_ownership=True)
    assert r.status == CONFIRMED and r.name == "Hebrew Theological College"


def test_ownership_never_names_a_board_without_a_vendor_name():
    r = resolve_identity([NameClaim("Some Company", SOURCE_LIST, "kalil")], code="xyz", board_ownership=True)
    assert r.status == UNRESOLVED


@pytest.mark.parametrize("evidence,basis,refs,ok", [
    ("links_to_board:teamtailor:allenmotorgroup", "board_link", ["teamtailor:allenmotorgroup"], True),
    ("links_to_board:teamtailor:allenmotorgroup", "careersite_redirect_domain", ["teamtailor:allenmotorgroup"], True),
    # only one direction: the site was found by name lookup, not from the board
    ("links_to_board:teamtailor:allenmotorgroup", "reference_name_slug_domain", ["teamtailor:allenmotorgroup"], False),
    # a group / agency page linking many boards
    ("links_to_board:teamtailor:a", "board_link", ["teamtailor:a", "teamtailor:b", "lever:c", "greenhouse:d"], False),
    # verified by name, not by a link to the board
    ("site names itself 'Acme'", "board_link", [], False),
])
def test_board_ownership_requires_a_two_way_link_and_a_specific_page(evidence, basis, refs, ok):
    assert board_ownership(evidence, basis, {"board_refs": refs}) is ok


# 2. Workday entity codes ----------------------------------------------------------------

@pytest.mark.parametrize("raw,clean", [
    ("B8115 Bob's Discount Furniture", "Bob's Discount Furniture"),
    ("LE0002 U.S. Urology Partners", "U.S. Urology Partners"),
    ("8974 DuPont Specialty Products", "DuPont Specialty Products"),
    ("84 Lumber", "84 Lumber"),
    ("3M Company", "3M Company"),
    ("NKW ImmunityBio Inc", "NKW ImmunityBio Inc"),
])
def test_strip_entity_code(raw, clean):
    assert strip_entity_code(raw) == clean


def test_entity_coded_vendor_name_matches_and_keeps_raw_value():
    claims = [NameClaim("B8115 Bob's Discount Furniture", VENDOR_API, "workday_job_hiring_organization", "B8115 Bob's Discount Furniture"),
              NameClaim("Bob's Discount Furniture", SOURCE_LIST, "kalil")]
    r = resolve_identity(claims, code="bobsdf.wd1/bobs_careers")
    assert (r.status, r.name) == (CONFIRMED, "Bob's Discount Furniture")
    assert claims[0].raw == "B8115 Bob's Discount Furniture"


def test_numeric_names_are_not_mangled_when_corroborated_as_is():
    claims = [NameClaim("1800 Contacts", VENDOR_API, "workday_job_hiring_organization"), NameClaim("1-800 Contacts", SOURCE_LIST, "kalil")]
    r = resolve_identity(claims, code="1800contacts.wd1/careers")
    # Not reduced to "Contacts"; the agreeing list spelling is shown for a per-posting legal entity.
    assert r.status == CONFIRMED and r.name in ("1800 Contacts", "1-800 Contacts")


# 3. Junk names --------------------------------------------------------------------------

@pytest.mark.parametrize("raw", ["Employer", "en", "Homepage", "Startseite", "Welcome", "Q131883236"])
def test_more_junk_names(raw):
    assert clean_name(raw, "zzz") is None


@pytest.mark.parametrize("raw", ["Home Depot", "Employers Holdings", "EN Engineering", "Welcome Homes", "Start Today", "Homepage Partners"])
def test_real_names_containing_junk_words_are_kept(raw):
    assert clean_name(raw, "zzz") == raw


def test_linkedin_suffix_removed_from_names():
    assert clean_name("VerSprite - LinkedIn", "versprite") == "VerSprite"


# 4. Referral rule -----------------------------------------------------------------------

def test_referral_inside_a_name_is_not_an_auxiliary_board():
    assert not is_auxiliary_board("Peel Addiction Assessment And Referral Centre")
    assert not is_auxiliary_board("Medical Referral Services")


@pytest.mark.parametrize("name", ["AlphaSense - for Referrals", "Sprout General Referrals", "Acme Referral Program", "Acme (Referrals)", "Employee Referrals"])
def test_referral_boards_still_excluded(name):
    assert is_auxiliary_board(name)


# 5. Root redirecting to its careers host ----------------------------------------------------

def test_root_redirecting_to_careers_host_keeps_root():
    assert official_landing("https://silverspin.com", "https://careers.silverspin.com") == ("https://silverspin.com", True)
    assert official_landing("https://acme.com", "https://www.acme.com") == ("https://www.acme.com", False)
    # a redirect to a different company's careers host is not this rule's business
    assert official_landing("https://acme.com", "https://careers.other.com") == ("https://careers.other.com", False)


# LinkedIn: recovered legitimate pages, no related entities ------------------------------

def _labelled():
    return list(csv.DictReader(open(FIXTURE, newline="", encoding="utf-8")))


def test_no_related_entity_or_vendor_page_is_accepted():
    for r in _labelled():
        if r["label"] == "exclude":
            assert not linkedin_compatible(r["slug"], r["company_name"] or None, r["website"] or None), r["slug"]


def test_recovers_a_measured_share_of_legitimate_pages():
    legit = [r for r in _labelled() if r["label"] == "legit"]
    ok = sum(linkedin_compatible(r["slug"], r["company_name"] or None, r["website"] or None) for r in legit)
    assert ok >= 39, ok


@pytest.mark.parametrize("slug,name,site,ok", [
    ("getsona", "Sona", "https://www.sona.ai", True),
    ("icp_3", "ICP", "https://www.icpnet.com", True),
    ("cfc-underwriting-ltd", "CFC", "https://www.cfc.com", True),
    ("norwegian-geotechnical-institute-ngi-", "NGI", "https://www.ngi.no", True),
    ("aer%C4%ABz", "Aeriz", "https://aeriz.com", True),
    ("high-tech-gruenderfonds", "High-Tech Gründerfonds Management", "https://www.htgf.de", True),
    # must stay rejected
    ("united-colleges-group", "City of Westminster College", "https://ucg.ac.uk", False),
    ("searchlight-cyber", "Assetnote", "https://www.slcyber.io", False),
    ("eyecare-partners.com", "EyeCare Associates", "https://www.webeca.com", False),
    ("recruitee", "Myr", "https://www.myr.gg", False),
    ("fillyourhandle", "Light", "https://light.inc", False),
    ("compound-ai", "Twenty Labs", "https://twentylabs.ai", False),
    ("getmesomething", "Something Else Ltd", "https://else.com", False),
])
def test_linkedin_examples(slug, name, site, ok):
    assert linkedin_compatible(slug, name, site) is ok
