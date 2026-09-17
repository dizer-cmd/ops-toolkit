"""
Grade a live run against the committed reference outputs.

Two numbers matter and they are not the same number:

  * field accuracy  -- did it classify the case the way the answer key does
  * review recall   -- of the cases that should reach a human, how many did

Accuracy is the one people quote. Recall on the review queue is the one that
decides whether this is allowed near real work: a tool that is 95% accurate and
silently swallows the 5% is worse than useless in a regulated operation.
"""

from __future__ import annotations

import json


def load_reference(tool, input_id: str) -> dict | None:
    path = tool.fixture(input_id)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def grade(tool, results) -> dict:
    fields = tool.field_list("score_fields")
    per_field = {f: {"right": 0, "total": 0} for f in fields}
    mismatches = []
    tp = fp = fn = tn = 0
    scored = skipped = 0

    for r in results:
        ref = load_reference(tool, r.input_id)
        if ref is None:
            skipped += 1
            continue
        scored += 1
        for f in fields:
            if f not in ref:
                continue
            per_field[f]["total"] += 1
            got, want = r.payload.get(f), ref.get(f)
            if got == want:
                per_field[f]["right"] += 1
            else:
                mismatches.append((r.input_id, f, want, got))

        should = bool(ref.get("needs_human_review"))
        did = bool(r.needs_review)
        if should and did:
            tp += 1
        elif should and not did:
            fn += 1
        elif did and not should:
            fp += 1
        else:
            tn += 1

    def pct(n, d):
        return None if not d else round(100.0 * n / d, 1)

    return {
        "scored": scored,
        "skipped_no_reference": skipped,
        "fields": {f: pct(v["right"], v["total"]) for f, v in per_field.items()},
        "review": {
            "caught": tp, "missed": fn, "over_flagged": fp, "correctly_cleared": tn,
            "recall_pct": pct(tp, tp + fn),
            "precision_pct": pct(tp, tp + fp),
        },
        "mismatches": mismatches,
    }
