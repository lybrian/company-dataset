"""BigPicture free company dataset as a reference table keyed by website domain.

Used for two things only:
  * LinkedIn handle and country for a company whose website we already know
    (joined on domain, unambiguous matches only);
  * a candidate website for a board that has none, when the board's name matches
    exactly one company whose domain also agrees with the board slug. Such candidates
    are only accepted after the company's own homepage confirms the identity.
"""
from __future__ import annotations

import csv
import gzip
import json
import re
from collections import defaultdict
from pathlib import Path

from company_dataset.models import SourceMeta, utc_now
from company_dataset.normalize import clean_website, host_of

META = SourceMeta(
    name="bigpicture",
    description="BigPicture 2023 Q4 Free Company Dataset (17.1M companies: name, website domain, LinkedIn handle, country)",
    download_url="https://huggingface.co/datasets/bigpictureio/companies-2023-q4-sm/resolve/main/companies-2023-q4-sm.csv.gz",
    filename="companies-2023-q4-sm.csv.gz",
    license="ODC-By-1.0",
    license_url="https://opendatacommons.org/licenses/by/1-0/",
    license_note="Reference data only (LinkedIn handle, country, candidate website by domain/name join); never a source of boards.",
    attribution="BigPicture (bigpicture.io) Free Company Dataset 2023 Q4, via Hugging Face bigpictureio/companies-2023-q4-sm",
)

csv.field_size_limit(10**8)


def name_key(name) -> str:
    from company_dataset.enrichment import name_key as _nk

    return _nk(name)


def _label_key(domain: str) -> str:
    return re.sub(r"[^a-z0-9]", "", domain.split(".")[0])


def domain_chain(host: str) -> list[str]:
    """acme.com -> [acme.com]; about.acme.com -> [about.acme.com, acme.com]."""
    labels = host.split(".")
    chain = [host]
    if len(labels) > 2:
        chain.append(".".join(labels[1:]))
    return chain


class Reference:
    def __init__(self, by_domain: dict | None = None, by_name: dict | None = None):
        self.by_domain: dict[str, list[dict]] = by_domain or {}
        self.by_name: dict[str, list[dict]] = by_name or {}

    def _rows_for(self, website: str, name: str | None) -> list[dict]:
        host = host_of(website)
        for dom in domain_chain(host) if host else []:
            rows = self.by_domain.get(dom)
            if not rows:
                continue
            if len(rows) == 1:
                return rows
            from company_dataset.enrichment import names_match

            named = [r for r in rows if name and names_match(r["name"], name)]
            return named if len(named) == 1 else []
        return []

    def linkedin_slug(self, website: str, name: str | None) -> str | None:
        rows = self._rows_for(website, name)
        if not rows or not rows[0].get("handle"):
            return None
        handle = rows[0]["handle"]
        return handle.split("company/", 1)[1] if handle.startswith("company/") else None

    def country(self, website: str, name: str | None) -> str | None:
        rows = self._rows_for(website, name)
        return (rows[0].get("country") or None) if rows else None

    def name(self, website: str) -> str | None:
        rows = self._rows_for(website, None)
        return rows[0]["name"] if rows else None

    def name_candidates(self, name: str | None, code: str) -> list[str]:
        """A website for a board known only by name: exactly one slug-agreeing domain."""
        if not name:
            return []
        key = name_key(name)
        rows = self.by_name.get(key) or []
        slug = re.sub(r"[^a-z0-9]", "", code.lower())
        agreeing = set()
        for r in rows:
            dom = host_of(r.get("website") or "")
            if not dom:
                continue
            label = _label_key(dom)
            # The domain must agree with the board slug, which is independent evidence;
            # agreeing with the name alone would let a generic name pick any namesake.
            if label and (label == slug or (len(label) >= 4 and slug.startswith(label))):
                site = clean_website("https://" + dom)
                if site:
                    agreeing.add(site)
        return sorted(agreeing) if len(agreeing) == 1 else []

    def to_json(self) -> dict:
        return {"by_domain": self.by_domain, "by_name": self.by_name}


def build(path: Path, domains: set[str], names: set[str]) -> Reference:
    by_domain: dict[str, list[dict]] = defaultdict(list)
    by_name: dict[str, list[dict]] = defaultdict(list)
    with gzip.open(path, "rt", encoding="utf-8", errors="ignore", newline="") as fh:
        for row in csv.DictReader(fh):
            dom = host_of(row.get("website") or "")
            key = name_key(row.get("name"))
            if not (dom in domains or key in names):
                continue
            rec = {
                "name": (row.get("name") or "").strip(),
                "website": dom,
                "handle": (row.get("handle") or "").strip(),
                "country": (row.get("country_code") or "").strip().upper(),
            }
            if dom:
                by_domain[dom].append(rec)
            if key in names and dom:
                by_name[key].append(rec)
    return Reference(dict(by_domain), dict(by_name))


def load_or_build(dirs: dict, boards, pages: dict) -> Reference:
    """Build the filtered reference index for the current boards and save it."""
    from company_dataset.enrichment import board_name_for_lookup, content_website_candidates, greenhouse_content_url, vendor_websites

    path = Path(dirs["raw"]) / META.name / META.filename
    if not path.exists():
        print(f"[reference] {path} missing; run download stage. Continuing without reference data.")
        return Reference()
    domains: set[str] = set()
    names: set[str] = set()
    for board, outcome in boards:
        vendor_page = pages.get(board.careersite_url)
        vendor_sites = vendor_websites(board, outcome, vendor_page)
        sites = list(vendor_sites)
        if board.ats == "greenhouse":
            sites += content_website_candidates(board, pages.get(greenhouse_content_url(board.code)))
        for site, _ in sites:
            for dom in domain_chain(host_of(site)):
                domains.add(dom)
            page = pages.get(site)
            if page and page.get("final_url"):
                for dom in domain_chain(host_of(page["final_url"])):
                    domains.add(dom)
        if not vendor_sites:
            key = name_key(board_name_for_lookup(board, outcome, vendor_page))
            if len(key) >= 3:
                names.add(key)
    print(f"[reference] scanning {path.name} for {len(domains)} domains and {len(names)} names")
    ref = build(path, domains, names)
    out = Path(dirs["intermediate"]) / "reference_index.json"
    out.write_text(json.dumps({"generated_at": utc_now(), **ref.to_json()}), encoding="utf-8")
    print(f"[reference] matched {len(ref.by_domain)} domains, {len(ref.by_name)} names")
    return ref


def load_saved(dirs: dict) -> Reference:
    path = Path(dirs["intermediate"]) / "reference_index.json"
    if not path.exists():
        return Reference()
    data = json.loads(path.read_text(encoding="utf-8"))
    return Reference(data.get("by_domain"), data.get("by_name"))
