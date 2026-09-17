---
id: case-intake
name: Case intake triage
version: 1.0.3
owner: Operations
status: live
input: data/cases.synthetic.csv
id_field: case_id
name_fields: [claimant_name, handler_name]
text_fields: [subject, body]
score_fields: [case_type, priority, routing_queue]
model: claude-opus-5
effort: medium
sla_seconds: 20
---

# Case intake triage

## What it does

Reads an inbound case — email, portal submission, post, or a handler's phone
note — and decides four things: what kind of contact it is, how urgent it is,
which queue it belongs in, and what is missing before anyone can work it.

## What it does not do

It does not decide anything. It routes, and it says why. Every output lands in
one of two places: a queue, or a human. Nothing is closed, rejected, or actioned
by this tool.

## Why it exists

Intake is read twice today — once to work out where it goes, and again by the
person it goes to. The first read is the one that can be done in advance. The
prize is not the classification; it is that the case arrives at the right desk
with the missing items already listed.

## Escalation policy

The harness forces human review on schema violation, model refusal, and
unresolved person references. On top of that, this tool must raise its hand for:

| Trigger | Why |
|---|---|
| any sign of vulnerability, bereavement, distress, mental or physical ill health | never a routing decision; a person decides what happens next |
| withdrawal, closure, or "stop contacting me" | irreversible from the claimant's side |
| a complaint, however it is worded | starts a clock the business is held to |
| missing or unmatched client reference | the case cannot be attached to a file |
| a stated date that contradicts another date | one of them is a deadline someone will miss |
| content not in English | routing it on a guess is worse than queuing it |
| anything out of scope, before it is returned to sender | returning correspondence is outward-facing and hard to undo |
| a referenced attachment that is not present | the case cannot be worked on what was actually sent |

`P1` exists for exactly one reason: somebody needs to look at this today.

## Inputs

`data/cases.synthetic.csv` — synthetic throughout. See `data/README.md`.

| Column | Notes |
|---|---|
| `case_id` | identifier, echoed back |
| `received` | ISO date |
| `channel` | `portal`, `email`, `post`, `phone_note` |
| `client_ref` | may be blank — that is one of the things being tested |
| `claimant_name`, `handler_name` | redacted before egress, never sent |
| `subject`, `body` | redacted before egress |
| `attachments` | `;`-separated filenames, may be blank |

## Output

`schema.output.json`. Enforced twice: as `output_config.format` at generation
time, and again locally on the way back.

## Known limits

- It reads what the case says, not the file behind it, so it cannot confirm a
  reference number actually exists. `client_ref_present` means *present and
  well-formed*, not *valid*.
- It sees one row at a time, so it **cannot** detect duplicates. `CASE-0011` in
  the sample set is a resubmission of `CASE-0001` and is deliberately allowed
  through unflagged, because pretending otherwise would hide a real gap. Closing
  it needs cross-row state — see `ROADMAP.md`.
- It has no memory of previous contacts on the same file.

## Open questions for the owner

Two rules this tool applies without the business having decided them. Both
surfaced in evaluation as persistent, reasonable disagreements rather than
errors, and both are left visible instead of being settled by whoever happened to
write the answer key.

| Question | Current key | What the model does | Why it matters |
|---|---|---|---|
| What priority is out-of-scope correspondence? | `P4` — nothing to do but file it | `P3` — normal queue | Returning correspondence to sender is an action, so `P4` may be the wrong reading of our own ladder |
| Where does a withdrawal request route? | `intake_team` | `legal` | Whether closing a claim is an intake task or a legal one is a question about how the business is organised |

Until they are answered, both cases reach a human regardless, so neither can
cause harm — but the answer key should not be mistaken for a decision.

## Change log

| Version | Change |
|---|---|
| 1.0.3 | Structural fix. The escalation policy published in this file is now injected into the prompt verbatim at `{{escalation_policy}}` instead of being restated there -- run 3 lost three escalations to rules the model was never shown. Added `out_of_scope` and `referenced_attachment_absent` as published triggers, raised the `review_reasons` length limit to 100, and `verify` now fails a tool whose policy does not reach its prompt. |
| 1.0.2 | Recall regression fix. Reverted the v1.0.1 key change on `CASE-0011`, which had been made from a single run without a matching prompt rule and cost a point of review recall. Applied the priority principle consistently to `CASE-0009` and `CASE-0012`. Added: a deadline that may already have passed is P1, and a populated `missing_information` is not itself an escalation trigger. |
| 1.0.1 | First live evaluation. Separated priority (time pressure) from review (consequence) after the key was found contradicting the prompt's own P1 definition; ruled that the injury being claimed is not a vulnerability disclosure. Answer key corrected on three cases. See `docs/EVAL-2026-09-16.md`. |
| 1.0.0 | First cut. 12 synthetic cases, 9 of which must reach a human. |
