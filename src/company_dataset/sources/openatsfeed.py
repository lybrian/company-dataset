from __future__ import annotations

import json
from pathlib import Path

from company_dataset.models import Reject, SourceMeta, SourceRecord
from company_dataset.normalize import SUPPORTED_ATS, clean_code

META = SourceMeta(
    name="openatsfeed",
    description="open-ats-feed board tokens (Greenhouse, Lever, Ashby and others, enumerated from Common Crawl and checked against the vendors' APIs)",
    download_url="https://raw.githubusercontent.com/veresk06/open-ats-feed/main/data/tokens.json",
    filename="tokens.json",
    license="MIT",
    license_url="https://github.com/veresk06/open-ats-feed/blob/main/LICENSE",
    license_note="Board tokens are factual identifiers; each is re-validated against the vendor API before export.",
    attribution="veresk06/open-ats-feed on GitHub",
)


def parse(path: Path):
    records: list[SourceRecord] = []
    rejects: list[Reject] = []
    if not Path(path).exists():
        return records, rejects
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    for provider, tokens in data.items():
        ats = provider.strip().lower()
        if ats not in SUPPORTED_ATS:
            continue  # other ATS vendors in the file are out of scope, not bad rows
        for i, token in enumerate(tokens or []):
            ref = f"{ats}[{i}]"
            code = clean_code(ats, token.strip() if isinstance(token, str) else "")
            if code is None:
                rejects.append(Reject(source=META.name, reason="invalid_slug", detail=str(token), row_ref=ref, ats=ats))
                continue
            records.append(SourceRecord(source=META.name, ats=ats, code=code, row_ref=ref))
    return records, rejects
