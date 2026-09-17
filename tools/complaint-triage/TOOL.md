---
id: complaint-triage
name: Complaint and appeal triage
version: 1.0.3
owner: Operations
status: live
input: data/complaints.synthetic.csv
id_field: complaint_id
name_fields: [complainant_name, handler_name]
text_fields: [text]
score_fields: [category, severity, next_action]
model: claude-opus-5
effort: high
sla_seconds: 25
---

# Complaint and appeal triage

## What it does

Reads a complaint or appeal and establishes the four things that decide what
happens in the next 24 hours: what it is actually about, how serious it is,
whether the complainant shows signs of vulnerability, and whether a regulated
response clock has already started.

## What it does not do

It does not uphold, reject, offer redress, or write to anybody. A complaint
handler does all of that. This tool exists so that the handler opens the file
already knowing what they are dealing with.

## Why `effort: high`

Intake triage is mostly recognition. This is judgement: the difference between
a complaint about an outcome and a complaint about conduct changes who handles
it and under which policy, and the distinction is often one sentence buried in
a long account. The extra cost per case is worth it here and is not worth it on
intake — which is why it is set per tool, not globally.

## Escalation policy

Beyond the harness rules (schema violation, refusal, unresolved names):

| Trigger | Why |
|---|---|
| any vulnerability indicator | a vulnerable complainant is never routed automatically |
| allegation about a named individual's conduct | HR and legal exposure, not a service complaint |
| the complainant references the ombudsman, a regulator, a solicitor or court | the matter is no longer purely internal |
| response clock already breached | the failure has happened; someone must own it today |
| redress, compensation or a refund is being asked for | money leaving the business is never an automatic decision |
| a complaint about the complaints process itself | escalating it into the same process is the wrong answer |

## Known limits

- Severity is judged from the account given, not from what actually happened.
  A calmly written serious failure and an angrily written trivial one are a
  known weakness; both are flagged rather than graded confidently.
- It cannot tell whether a clock has already been paused or extended. It reports
  what the case says and flags the case for confirmation.
- `days_since_first_contact` is taken on trust from the input.

## Change log

| Version | Change |
|---|---|
| 1.0.3 | Escalation policy now injected into the prompt verbatim from this file rather than restated, so the published rules and the rules the model receives cannot drift. `review_reasons` length limit raised to 100 after a recurring contract breach on informative reasons. |
| 1.0.2 | Applied v1.0.1's own unacknowledged-complaint rule to the key, which had been left behind. Separated a deadline that has demonstrably gone (`critical`) from time having merely passed (`high`). Added a tie-break for mixed complaints: classify by what the complainant asks to have changed. |
| 1.0.1 | First live evaluation. Added two explicit severity floors the prompt had left to inference (conduct allegations, unsent acknowledgements) and separated financial *loss claimed* from financial *hardship disclosed*, which was producing safeguarding referrals for reimbursement requests. Answer key corrected on four complaints. See `docs/EVAL-2026-09-16.md`. |
| 1.0.0 | First cut. 8 synthetic complaints, 7 of which must reach a human. |
