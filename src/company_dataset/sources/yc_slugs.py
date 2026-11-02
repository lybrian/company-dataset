"""Board identifiers guessed from the Y Combinator company directory, confirmed against each vendor.

    python -m company_dataset.sources.yc_slugs --raw data/raw --db data/store.db --limit-per-vendor 5000

Startups in this directory use these ATS far more often than companies at large, so a guess here is
worth more than one from a general list. Same limits and rules as sources/slug_prober.py.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from company_dataset.http import HttpClient
from company_dataset.models import SourceMeta
from company_dataset.sources import slug_prober
from company_dataset.sources._harvest import parse_tokens

DIRECTORY = "https://yc-oss.github.io/api/companies/all.json"

META = SourceMeta(
    name="yc_slugs_2026_11_03",
    description="Board identifiers guessed from Y Combinator company names and domains, confirmed against each vendor's public endpoint",
    download_url=DIRECTORY,
    filename="tokens.csv",
    license="Community mirror of a public directory; used for guesses only",
    license_url="https://github.com/yc-oss/api",
    license_note="Only identifiers a vendor answered for are kept; every board is verified against its provider before use.",
    attribution="yc-oss/api mirror of the Y Combinator company directory",
    downloadable=False,
)


def companies(payload: list[dict]) -> list[tuple[str, str]]:
    return [(c["name"], c["website"]) for c in payload if c.get("name") and c.get("website")]


def parse(path: Path):
    return parse_tokens(path, META.name)


def main(argv=None) -> int:
    from company_dataset import store

    p = argparse.ArgumentParser(prog="company_dataset.sources.yc_slugs")
    p.add_argument("--raw", default="data/raw")
    p.add_argument("--db", required=True)
    p.add_argument("--limit-per-vendor", type=int, required=True)
    p.add_argument("--seed", type=int, default=20261103)
    a = p.parse_args(argv)
    resp = HttpClient(timeout=120, max_attempts=3).get(DIRECTORY)
    conn = store.connect(a.db)
    known = {(r["ats"], r["code_key"]) for r in conn.execute("SELECT ats, code_key FROM boards")}
    conn.close()
    plan = slug_prober.plan_slugs(companies(json.loads(resp.text)), known, a.limit_per_vendor, a.seed)
    print(json.dumps(slug_prober.run(Path(a.raw), plan, meta=META), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
