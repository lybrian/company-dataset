"""Workable boards beyond those already stored: GitHub files that list them, and {code}.workable.com hosts.

    subfinder -d workable.com -all -silent -o data/raw/workable_discovery/subfinder.txt
    python -m company_dataset.sources.workable_discovery --raw data/raw

Workable is delivered separately from the five target ATS, so this keeps to its own source and file.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

from company_dataset.http import HttpClient, RequestError
from company_dataset.models import SourceMeta
from company_dataset.normalize import parse_board_url
from company_dataset.platforms import WORKABLE
from company_dataset.sources._harvest import boards_in_text, parse_tokens, plausible_slug, write_tokens
from company_dataset.sources.github_lists import MAX_FILE_BYTES, _gh
from company_dataset.sources.slug_files import VENDOR_WORDS, discover, slugs_in_file

QUERIES = ["filename:workable_slugs", "filename:workable_boards", "filename:companies_workable", "filename:slugs.json workable", "filename:workable.txt", "filename:workable.json",
           '"apply.workable.com" extension:md', '"apply.workable.com" extension:json', '"apply.workable.com" extension:csv', '"apply.workable.com" extension:txt', '"apply.workable.com" extension:yaml']
ALLOWED = (WORKABLE,)

META = SourceMeta(
    name="workable_discovery",
    description="Workable boards from public GitHub files and passive DNS",
    download_url="https://github.com/search",
    filename="tokens.csv",
    license="Public repository data and DNS records; only identifiers are read",
    license_url="",
    license_note="Only board identifiers are read; every board is verified against Workable before use.",
    attribution="Public GitHub repositories and subfinder's passive sources",
    downloadable=False,
)


def board_from_host(host: str) -> str | None:
    host = host.strip().lower().rstrip(".").removeprefix("*.")
    if not host.endswith(".workable.com") or host.count(".") != 2 or host.split(".")[0] in VENDOR_WORDS:
        return None
    parsed = parse_board_url(f"https://{host}/")
    return parsed.code if parsed and parsed.ats == WORKABLE and plausible_slug(parsed.code) else None


def harvest(raw_dir: Path, client: HttpClient, search=_gh, sleep=time.sleep) -> dict:
    out = Path(raw_dir) / META.name
    out.mkdir(parents=True, exist_ok=True)
    tokens: dict = {}
    passive = out / "subfinder.txt"
    if passive.exists():
        for line in passive.read_text(errors="ignore").splitlines():
            code = board_from_host(line)
            if code:
                tokens.setdefault((WORKABLE, code.casefold()), (code, "", f"subfinder:{line.strip()}"))
    files = 0
    for url in discover(search, sleep, queries=QUERIES, pages=2):
        try:
            resp = client.get(url)
        except (RequestError, subprocess.SubprocessError):
            continue
        if resp.status != 200 or len(resp.text) > MAX_FILE_BYTES:
            continue
        files += 1
        for ats, code in slugs_in_file(url, resp.text):
            if ats == WORKABLE:
                tokens.setdefault((WORKABLE, code.casefold()), (code, "", url))
        for key, value in boards_in_text(resp.text, url, allowed=ALLOWED).items():
            tokens.setdefault(key, value)
    write_tokens(out / META.filename, tokens)
    return {"files_read": files, "boards": len(tokens)}


def parse(path: Path):
    return parse_tokens(path, META.name, allowed=ALLOWED)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="company_dataset.sources.workable_discovery")
    p.add_argument("--raw", default="data/raw")
    a = p.parse_args(argv)
    print(json.dumps(harvest(Path(a.raw), HttpClient(timeout=60, per_host_interval=0.1, max_attempts=2)), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
