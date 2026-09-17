"""
Append-only run log.

One line of JSON per tool run, written before the caller gets its result. What
it records is chosen so that the log itself is not a second copy of the case
data: inputs and outputs appear as sha256 digests, never as text. You can prove
which prompt version processed which input and what the decision was, without
the log becoming a thing that needs its own retention policy.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from pathlib import Path

LOG = Path(__file__).resolve().parent.parent / "runs" / "audit.jsonl"


def digest(value) -> str:
    if not isinstance(value, str):
        value = json.dumps(value, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def new_run_id() -> str:
    return time.strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:6]


def operator() -> str:
    return os.environ.get("OPSQ_OPERATOR") or os.environ.get("USERNAME") or "unknown"


def record(entry: dict) -> dict:
    entry = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "operator": operator(), **entry}
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
    return entry


def read(limit: int | None = None) -> list[dict]:
    if not LOG.exists():
        return []
    rows = [json.loads(line) for line in LOG.read_text(encoding="utf-8").splitlines() if line.strip()]
    return rows[-limit:] if limit else rows
