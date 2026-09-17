# Runbook — case intake triage

Written for whoever is on intake, not for whoever built this. If any step here
needs someone technical standing behind you, the step is wrong — say so and it
gets fixed.

## Before you start

You need the day's cases in a CSV with these columns, in any order:

```
case_id, received, channel, client_ref, claimant_name, handler_name,
subject, body, attachments
```

Export it from the case system as UTF-8. If a column is missing the tool stops
and tells you which one — it will not guess.

## Running it

Offline, against the sample set (no credentials, no cost, always works):

```bash
python cli.py run case-intake
```

Against today's real export:

```bash
python cli.py run case-intake --provider claude --input data/2026-09-16.csv
```

It prints one line per case. `REVIEW` means it has come to you. `auto` means it
has been routed and you do not need to open it.

## Reading the output

```
  REVIEW  CASE-0005    Claimant bereaved and distressed; asking whether the...
           - vulnerability_indicated
           - irreversible_request
```

The indented lines are the reasons. There is always at least one on a `REVIEW`
row — a case never arrives in your queue without saying why.

The full output is in `runs/<run id>/output.jsonl`, one JSON object per case.

## What to do with each reason

| Reason | What it means | Your next step |
|---|---|---|
| `vulnerability_indicated` | distress, bereavement, ill health | do not route; follow the vulnerable customer process |
| `irreversible_request` | withdrawal or closure | confirm with the claimant directly before anything is actioned |
| `complaint_detected` | dissatisfaction with handling | log it as a complaint today — the clock has already started |
| `client_reference_missing` | cannot be attached to a file | find the file or request the reference |
| `contradictory_dates` | two dates disagree | establish which is the real deadline before replying |
| `non_english_content` | not written in English | route to translation, do not act on a guess |
| `ambiguous_person_reference` | a first name matches two people on file | check which one is meant |
| `schema_violation` | the tool produced output that broke its own contract | do not use the row; report it (see below) |
| `model_refusal` | the model declined to process this case | handle manually; report it |
| `provider_error` | the run did not complete for this case | re-run that one case; if it fails again, report it |

## When it goes wrong

**It flagged everything.** Normal on a bad export — usually one column is empty
for every row. Check the CSV before assuming the tool is broken.

**It cleared something it should not have.** This is the one that matters. Send
the `case_id`, the run id, and what should have happened. That is a prompt
change, a new version, and a new fixture — not a one-off correction.

**`schema_violation` on more than one case in a run.** Stop using the run and
escalate. It usually means the model, the prompt or the schema has moved and the
three no longer agree.

## What is recorded

Every case run appends a line to `runs/audit.jsonl`: when, who ran it, which
prompt version, which model, what was decided, and how many identifiers were
redacted. The case text itself is **not** in the log — only a checksum of it.

You can read the log back at any time:

```bash
python cli.py audit --tail 20
```

## Who owns this

Operations. Changes to the prompt, the vocabulary or the escalation rules go
through whoever owns the tool — they are versioned, not edited in place.
