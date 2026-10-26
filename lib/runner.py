"""
The run loop.

Order is deliberate and identical for every tool:

    read row -> redact -> render prompt -> provider -> contract check
             -> review policy -> re-hydrate -> audit line

Two rules the harness enforces so individual tools cannot get them wrong:

  1. Nothing identifying leaves the machine. Redaction happens here, before the
     prompt is rendered, not inside a tool's prompt where it could be forgotten.
  2. The harness may only ever *escalate* to human review. A tool can raise its
     hand; nothing can lower it. A schema violation, a refusal or an unresolved
     person reference forces review regardless of what the model concluded.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

from . import audit, contract, prompt as prompt_lib
from .redact import Redactor

HARNESS_REASONS = {
    "schema_violation": "output did not match the tool's contract",
    "model_refusal": "model declined to process this case",
    "ambiguous_person_reference": "a name in the case matches more than one person on file",
    "provider_error": "the run did not complete",
    "payment_card_in_text": "a payment card number was removed from the case before egress",
}


@dataclass
class Result:
    input_id: str
    payload: dict
    needs_review: bool
    reasons: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    meta: dict = field(default_factory=dict)


def load_rows(path: str | Path) -> list[dict]:
    with Path(path).open(newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def _restore(node, redactor: Redactor):
    if isinstance(node, str):
        return redactor.restore(node)
    if isinstance(node, list):
        return [_restore(v, redactor) for v in node]
    if isinstance(node, dict):
        return {k: _restore(v, redactor) for k, v in node.items()}
    return node


def run_one(tool, row: dict, provider, run_id: str) -> Result:
    id_field = tool.meta["id_field"]
    input_id = row[id_field]

    names = [row[f] for f in tool.field_list("name_fields") if row.get(f)]
    redactor = Redactor(extra_names=names)

    # Name fields first, so each full name claims its token before the free text
    # is read. The other way round, a surname written alone in the text ("it says
    # OKONJO-B") took a token of its own, and the same person reached the model
    # as two people.
    scrubbed = dict(row)
    for f in tool.field_list("name_fields"):
        if scrubbed.get(f):
            scrubbed[f] = redactor.scrub(scrubbed[f])
    for f in tool.field_list("text_fields"):
        if isinstance(scrubbed.get(f), str):
            scrubbed[f] = redactor.scrub(scrubbed[f])

    # Harness-supplied values are not case data. The escalation policy comes
    # from TOOL.md so that the documented rules and the rules the model is given
    # are the same text.
    harness = {"escalation_policy": tool.escalation_policy}
    system_prompt = prompt_lib.render(tool.system, harness)
    user_prompt = prompt_lib.render(tool.template, {**scrubbed, **harness})

    reasons: list[str] = []
    errors: list[str] = []
    payload: dict = {}
    try:
        payload, meta = provider.complete(tool, input_id, system_prompt, user_prompt)
    except Exception as exc:
        meta = {"provider": getattr(provider, "name", "?"), "model": None,
                "latency_ms": None, "usage": None, "refused": False,
                "error": f"{type(exc).__name__}: {exc}"}
        reasons.append("provider_error")
        errors.append(str(exc))

    if meta.get("refused"):
        reasons.append("model_refusal")

    if payload:
        errors += contract.validate(payload, tool.schema)
        if errors:
            reasons.append("schema_violation")

    if redactor.ambiguous_hits:
        reasons.append("ambiguous_person_reference")

    # The card never reached the model, but it arrived in the case. Handling it
    # is a data matter for a person, whatever the model made of the rest.
    if redactor.counts().get("CARD"):
        reasons.append("payment_card_in_text")

    reasons += [r for r in payload.get("review_reasons", []) if r not in reasons]
    # Escalate-only: the model's own flag can raise this, never lower it.
    needs_review = bool(reasons) or bool(payload.get("needs_human_review"))

    restored = _restore(payload, redactor)
    if restored:
        restored["needs_human_review"] = needs_review
        restored["review_reasons"] = reasons

    audit.record({
        "run_id": run_id,
        "tool": tool.id,
        "tool_version": tool.version,
        "prompt_sha": tool.prompt_sha,
        "schema_sha": tool.schema_sha,
        "contract_backend": contract.backend(),
        "provider": meta.get("provider"),
        "model": meta.get("model"),
        "input_id": input_id,
        "input_sha": audit.digest(row),          # digest, never the case text
        "output_sha": audit.digest(payload) if payload else None,
        "redactions": redactor.counts(),
        "ambiguous_person_hits": redactor.ambiguous_hits,
        "contract_ok": not errors,
        "contract_errors": errors[:5],
        "needs_human_review": needs_review,
        "review_reasons": reasons,
        "latency_ms": meta.get("latency_ms"),
        "usage": meta.get("usage"),
        "error": meta.get("error"),
    })

    return Result(input_id, restored, needs_review, reasons, errors, meta)


def run(tool, rows: list[dict], provider, limit: int | None = None) -> tuple[str, list[Result]]:
    run_id = audit.new_run_id()
    selected = rows[:limit] if limit else rows
    return run_id, [run_one(tool, row, provider, run_id) for row in selected]
