# Runbook — complaint and appeal triage

For complaint handlers. Same shape as the intake runbook; the differences are in
what the flags mean and how fast you have to move on them.

## Running it

```bash
python cli.py run complaint-triage                      # offline sample set
python cli.py run complaint-triage --provider claude --input data/2026-09-16.csv
```

Input columns:

```
complaint_id, received, channel, client_ref, complainant_name,
handler_name, text, prior_contacts, days_since_first_contact
```

`days_since_first_contact` is taken on trust. If it is wrong in the export, the
clock flags will be wrong — check it before you rely on them.

## The flags, in the order they matter

| Flag | Do this |
|---|---|
| `vulnerability_indicated` | **before anything else.** Vulnerable customer process. Do not route it onward first. |
| `possible_data_breach` | start the incident process today. The clock on a reportable breach is short and it has already started. |
| `clock_may_be_breached` | establish the real deadline today and tell someone who can own a breach. |
| `external_escalation_threatened` | ombudsman, regulator, solicitor or court. Legal sees it before you reply. |
| `staff_conduct_allegation` | does not go to the person it is about, or to their team. Senior only. |
| `complaint_about_complaints_process` | do not put it back through the process being complained about. |
| `redress_sought` | money is being asked for. Never actioned from this output. |
| `third_party_authority_unverified` | somebody is writing on another person's behalf. Verify authority before you send them anything. |

## The one that is not on the list

If a case comes back `auto` and you think it should not have, that is the
finding worth reporting. Send the `complaint_id`, the run id, and what should
have happened. It becomes a prompt change, a version bump and a new fixture, so
the same miss cannot happen twice without the score showing it.

## Severity is judged from the account, not the event

A calmly written serious failure can come back `medium`. An angrily written
trivial one can come back `high`. This is a known weakness, written down in
`TOOL.md`, and it is why severity alone never routes anything on its own.

## What is recorded

One line per complaint in `runs/audit.jsonl`: prompt version, model, decision,
redaction counts, who ran it. The complaint text is not in the log — only a
checksum of it.

```bash
python cli.py audit --tail 20
```
