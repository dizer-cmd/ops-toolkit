# Governance

Written so that a sign-off conversation is a review of this document rather than
a discovery exercise. Everything here is either enforced in code or listed as a
residual risk. Nothing is described as handled because someone intends to handle
it.

This covers the toolkit as built, against synthetic data. The section at the end
lists what must be done before it touches a real case.

---

## 1. What leaves the machine

Nothing leaves in offline mode (`--provider replay`): no network call is made.

In live mode (`--provider claude`), one request per case goes to the Anthropic
API containing:

- the tool's system prompt and rendered user prompt
- the case fields listed in that tool's `text_fields` and `name_fields`, **after
  redaction**
- the output schema

It does **not** contain: the raw name, email address, telephone number, National
Insurance number, postcode or date of birth of any person in the case. Those are
replaced in `lib/redact.py` before the prompt is assembled, and re-hydrated
locally from a map that is held in memory for the duration of one case and never
written to disk.

Redaction runs in the harness, not in the tools. A tool author cannot forget it.

| Identifier | Handling |
|---|---|
| Person name | tokenised — `[PERSON_n]`, stable within a case |
| Name matching two people on file | masked as `[PERSON_?]`, case flagged for a human |
| Email address | tokenised, before names, so addresses are not shredded |
| Telephone number | tokenised |
| National Insurance number | tokenised, deliberately permissive — a mistyped number is still personal data |
| Postcode | tokenised |
| Date of birth | tokenised |

Enforced by `tests/test_harness.py::TestRedaction`.

---

## 2. What is recorded, and what is not

Every case run appends one line to `runs/audit.jsonl`:

```
timestamp, operator, run id, tool id, tool version, prompt sha, schema sha,
contract validator, provider, model, input id, input checksum, output checksum,
redaction counts, contract result, review decision, review reasons, latency,
token usage
```

The case text is **not** in the log — only a sha256 checksum of the input row.
The log is therefore an integrity and attribution record, not a second data
store, and does not need its own retention schedule beyond normal log retention.

Enforced by `tests/test_harness.py::TestAuditLog::test_log_holds_no_case_text`,
which runs the real dataset through the pipeline and asserts no fragment of any
case body appears in the log.

**What you can answer from the log alone:** which prompt version decided this
case, which model, who ran it, when, whether the output met its contract, whether
it went to a human and why.

**What you cannot answer from the log alone:** what the case said. That is
deliberate.

---

## 3. Human in the loop

No tool in this library decides anything. Each one routes and states reasons.
Closure, rejection, redress and any outward communication remain with a person.

The harness escalates to human review, and can never de-escalate, on:

| Trigger | Enforced in |
|---|---|
| output failed its schema | `lib/runner.py` |
| the model declined the request | `lib/runner.py` |
| the run did not complete | `lib/runner.py` |
| a person reference could not be resolved | `lib/redact.py` → `lib/runner.py` |

Tool-level triggers are listed in each `TOOL.md` under *Escalation policy*.
Vulnerability, irreversible requests, complaints, possible data breaches and
external escalation always reach a person.

Enforced by `tests/test_harness.py::TestEscalateOnly`.

---

## 4. A deliberate decision about model refusals

The API offers server-side fallbacks: if a model declines a request on policy
grounds, the request can be re-run automatically on a different model inside the
same call. **This toolkit does not use that.**

In a regulated case-handling context, a refused case is a signal. Complaints and
appeals contain exactly the material — distress, allegations, medical detail —
that a safety classifier may decline, and those are the cases most likely to need
a person. Silently rerouting them to a fallback model would bury the signal.

So a refusal returns `refused`, the case is flagged `model_refusal`, and a human
picks it up. This costs throughput and is the right trade. It is recorded here
rather than left as an omission someone later reads as an oversight.

See `lib/provider.py::ClaudeProvider`.

---

## 5. Change control

- Prompts are versioned by the sha256 of `prompt.md` — both halves. Editing one
  word produces a new hash, and the audit trail cannot attribute new decisions to
  the old version.
- Schemas are hashed the same way.
- Tool versions are declared in `TOOL.md` front matter with a change log.
- `python cli.py verify` is the gate. It fails if a fixture no longer validates
  against its schema, if the prompt asks for a field the input does not have, if
  a tool cannot escalate, or if any of the five required files is missing. It is
  intended to run in CI on every commit.

**A miss becomes a fixture.** When a tool clears something it should not have,
the fix is a prompt change, a version bump, and a new entry in the answer key —
so the same miss shows up as a score regression if it ever returns. Corrections
are not made case by case.

---

## 6. Residual risks

Stated, not solved.

| Risk | Current position |
|---|---|
| **Re-identification from free text.** Redaction removes direct identifiers. It cannot remove "the lady who rang about the Tuesday delivery in the Bolton office". | Accepted. Volume of such detail is low and the receiving processor does not hold the data needed to resolve it. Revisit if free-text volume grows. |
| **Prompt injection from case content.** A case is untrusted text. Someone could write instructions into a complaint. | Partially mitigated: the output schema is closed (`additionalProperties: false`, enumerated values), so an injected instruction cannot produce a field or a value nobody agreed to. It could still influence a classification. Every high-consequence category escalates to a human anyway. Not yet tested adversarially — see ROADMAP. |
| **Severity judged from tone.** A calm account of a serious failure may be under-rated. | Documented in each `TOOL.md`. Severity never routes anything on its own. |
| **`days_since_first_contact` taken on trust.** Clock flags are only as good as the export. | Flagged in the runbook. A validation rule against the case system is on the roadmap. |
| **No duplicate detection.** Each tool sees one row. | Deliberate and visible: `CASE-0011` is an unflagged duplicate in the sample set rather than a faked catch. First roadmap item. |
| **Operator identity is environment-derived.** `OPSQ_OPERATOR` or the OS username. Not authenticated. | Adequate for attribution in a trusted internal environment; not evidence of identity. Needs SSO before anything contested rests on it. |

---

## 7. Before this touches a real case

None of the following is done. All of it is known.

1. **A data processing agreement** covering the model provider, and a decision
   recorded on whether the processing is within the existing DPA or needs a new
   one.
2. **A DPIA**, or a documented decision that one is not required. The redaction
   design above is the input to it, not a substitute for it.
3. **Retention**: `runs/` currently grows without limit. A retention rule and a
   deletion job are needed before live use, even though the log holds no case
   text.
4. **Zero data retention** confirmed with the provider, or the absence of it
   recorded as an accepted risk.
5. **Access control**: who may run a tool, who may change a prompt. Currently
   filesystem permissions and code review; that is the answer for a pilot, not
   for production.
6. **A named owner per tool** with authority to approve prompt changes. `TOOL.md`
   has an `owner` field; it currently says "Operations", which is not a person.
7. **An adversarial pass** on prompt injection using real complaint text shapes.
8. **A rollback plan**: which prompt version to revert to, and who decides.
