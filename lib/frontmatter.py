"""
Minimal front-matter parser.

Deliberately not PyYAML: the offline demo must run on a clean Python install with
no pip step. TOOL.md front matter is restricted to flat `key: value` pairs and
`[a, b, c]` lists -- if a tool needs more structure than that, it is doing too
much and should be split. `opsq verify` enforces the restriction.
"""

from __future__ import annotations


def _coerce(raw: str):
    v = raw.strip()
    if v.startswith("[") and v.endswith("]"):
        inner = v[1:-1].strip()
        if not inner:
            return []
        return [_coerce(p) for p in inner.split(",")]
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    low = v.lower()
    if low in ("true", "yes"):
        return True
    if low in ("false", "no"):
        return False
    if low in ("null", "none", "~", ""):
        return None
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        pass
    return v


def split(text: str) -> tuple[dict, str]:
    """Return (front_matter_dict, body). No front matter -> ({}, text)."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    meta: dict = {}
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return meta, "\n".join(lines[i + 1:]).lstrip("\n")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(f"front matter line {i} is not `key: value`: {line!r}")
        key, _, raw = line.partition(":")
        meta[key.strip()] = _coerce(raw)
    raise ValueError("front matter opened with --- but never closed")
