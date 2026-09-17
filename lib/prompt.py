"""Prompt loading, rendering and versioning.

A prompt is an artefact with a version you can point at in an audit log, not a
string someone pasted into a chat window. Every run records the sha256 of the
exact prompt text that produced it, so "which prompt wrote this?" is answerable
six months later, after the prompt has moved on.
"""

from __future__ import annotations

import hashlib
import re

_PLACEHOLDER = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def placeholders(template: str) -> set[str]:
    return set(_PLACEHOLDER.findall(template))


def render(template: str, values: dict) -> str:
    """Substitute {{name}}. Every placeholder must be supplied -- a silently
    empty field is how a prompt quietly stops doing its job."""
    missing = placeholders(template) - set(values)
    if missing:
        raise KeyError(f"prompt placeholders not supplied: {sorted(missing)}")

    def sub(m: re.Match) -> str:
        return str(values[m.group(1)])

    return _PLACEHOLDER.sub(sub, template)
