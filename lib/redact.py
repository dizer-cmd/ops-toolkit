"""
Pre-egress redaction.

Nothing that identifies a person needs to leave the building for a triage
decision to be made. Direct identifiers are replaced with stable tokens before
the text is sent anywhere, and re-hydrated locally from a map that never leaves
the machine. The model reasons about [PERSON_1]; the operator reads the name.

This is the cheapest part of the system to build and the part a governance
review asks about first, so it is enforced in the harness rather than left to
each tool to remember.

Scope, stated plainly: this handles *direct* identifiers -- name, email, phone,
NI number, postcode, date of birth -- plus payment card numbers, which customers
paste into messages whatever the form tells them. It does not attempt to defeat
re-identification from free text ("the lady who rang about the Tuesday
delivery"). That residual risk is recorded in GOVERNANCE.md rather than hidden
behind a regex.
"""

from __future__ import annotations

import re

EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
# Deliberately permissive: a *badly typed* NI number is still personal data, so
# the redactor accepts prefix letters the real validation rules would reject.
# Validating the number is a different job from not leaking it.
NINO = re.compile(r"\b[A-Z]{2}\s?\d{2}\s?\d{2}\s?\d{2}\s?[A-D]\b", re.IGNORECASE)
PHONE = re.compile(r"(?<!\d)(?:\+44\s?|0)(?:\d\s?){9,10}(?!\d)")
POSTCODE = re.compile(r"\b[A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2}\b", re.IGNORECASE)
DOB = re.compile(r"\b(?:0?[1-9]|[12]\d|3[01])[/.-](?:0?[1-9]|1[0-2])[/.-](?:19|20)\d{2}\b")
# 13 to 19 digits, optionally grouped by spaces or hyphens. Only runs that pass
# the Luhn check are treated as cards, so a long reference number is left alone.
CARD = re.compile(r"(?<!\d)\d(?:[ -]?\d){12,18}(?!\d)")


def luhn_ok(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2:
            d = d * 2 - 9 if d > 4 else d * 2
        total += d
    return total % 10 == 0

# Order matters. Email goes first: an address contains a name, and redacting the
# name first would shred the address into fragments that no longer look like one.
PATTERNS = [
    ("EMAIL", EMAIL),
    ("NINO", NINO),
    ("PHONE", PHONE),
    ("DOB", DOB),
    ("POSTCODE", POSTCODE),
]


class Redactor:
    """Stable per-case tokenisation: the same value gets the same token within a
    case, so the model can still tell two mentions of one person apart from two
    people."""

    def __init__(self, extra_names: list[str] | None = None):
        self.map: dict[str, str] = {}      # token -> first original seen
        self._seen: dict[str, str] = {}    # casefolded original -> token
        self._counts: dict[str, int] = {}
        self.extra_names = sorted(
            {n.strip() for n in (extra_names or []) if len(n.strip()) > 2},
            key=len,
            reverse=True,
        )
        self._alias_targets, self._ambiguous = self._components()
        self.ambiguous_hits = 0

    def _components(self) -> tuple[dict[str, str], set[str]]:
        """Split name components into those that identify exactly one person and
        those shared by several. Two different Janes must not collapse into one
        token -- but a bare "Jane" must not be left in the clear either."""
        owners: dict[str, set[str]] = {}
        for full in self.extra_names:
            for part in full.split():
                if len(part) > 2:
                    owners.setdefault(part.casefold(), set()).add(full)
        unambiguous = {p: next(iter(n)) for p, n in owners.items() if len(n) == 1}
        ambiguous = {p for p, n in owners.items() if len(n) > 1}
        return unambiguous, ambiguous

    def _token(self, kind: str, value: str) -> str:
        key = value.casefold()
        if key in self._seen:
            return self._seen[key]
        self._counts[kind] = self._counts.get(kind, 0) + 1
        token = f"[{kind}_{self._counts[kind]}]"
        self._seen[key] = token
        self.map[token] = value
        if kind == "PERSON":
            # "Jane" and "Fairweather" resolve to the same token as
            # "Jane Fairweather" -- one person, one token.
            for part in value.split():
                part_key = part.casefold()
                if len(part) > 2 and part_key not in self._seen:
                    if self._alias_targets.get(part_key, value).casefold() == key:
                        self._seen[part_key] = token
        return token

    def _terms(self) -> list[str]:
        """Full names plus their unambiguous components, longest first. The full
        name is substituted before the bare surname, so "Jane Fairweather" claims
        the token and the later "Jane" resolves to the same one."""
        terms = set(self.extra_names)
        lowered = {n.casefold() for n in self.extra_names}
        for part, full in self._alias_targets.items():
            for word in full.split():
                if word.casefold() == part and part not in lowered:
                    terms.add(word)
        return sorted(terms, key=len, reverse=True)

    def _card(self, m: re.Match) -> str:
        digits = re.sub(r"\D", "", m.group(0))
        return self._token("CARD", m.group(0)) if luhn_ok(digits) else m.group(0)

    def scrub(self, text: str) -> str:
        out = EMAIL.sub(lambda m: self._token("EMAIL", m.group(0)), text)
        # Before the phone pattern, so a card is never half-claimed as a number.
        out = CARD.sub(self._card, out)
        for name in self._terms():
            out = re.sub(
                rf"\b{re.escape(name)}\b",
                lambda m: self._token("PERSON", m.group(0)),
                out,
                flags=re.IGNORECASE,
            )
        # A component shared by two people cannot be resolved to either. It is
        # still personal data, so it is masked with a token that carries no
        # identity, and the run is flagged so a human decides who was meant.
        for part in self._ambiguous:
            out, n = re.subn(rf"\b{re.escape(part)}\b", "[PERSON_?]", out, flags=re.IGNORECASE)
            self.ambiguous_hits += n
        for kind, pattern in PATTERNS:
            if kind == "EMAIL":
                continue
            out = pattern.sub(lambda m, k=kind: self._token(k, m.group(0)), out)
        return out

    def restore(self, text: str) -> str:
        out = text
        for token, original in self.map.items():
            # A card number is never re-hydrated. Nobody downstream of triage
            # needs it, and putting it back would write it into the run output.
            if token.startswith("[CARD_"):
                continue
            out = out.replace(token, original)
        return out

    def counts(self) -> dict[str, int]:
        return dict(self._counts)
