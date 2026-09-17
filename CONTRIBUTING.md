# Adding a tool

The standard is short on purpose. If it were long nobody would follow it, and a
standard nobody follows is worse than none — it makes the library look governed
when it is not.

## The five files

```
tools/<your-tool-id>/
  TOOL.md              spec + front matter
  prompt.md            ## SYSTEM and ## USER, one file
  schema.output.json   the output contract
  RUNBOOK.md           for the operator, not for you
  fixtures/            the answer key, one JSON file per input id
```

Run `python cli.py verify` after each step. It will tell you what is missing
before anyone else has to.

## TOOL.md front matter

Flat `key: value` only — lists as `[a, b, c]`. If a tool needs more structure
than that it is doing too much and should be two tools.

```yaml
---
id: your-tool-id          # must match the folder name
name: Human readable name
version: 1.0.0
owner: a person, ideally  # "Operations" is a placeholder, not an owner
status: live              # live | pilot | planned
input: data/your.csv
id_field: your_id_column
name_fields: [columns holding names]      # redacted before egress
text_fields: [columns holding free text]  # redacted before egress
score_fields: [the decisions you grade]
model: claude-opus-5
effort: medium            # low | medium | high — per tool, not global
sla_seconds: 20
---
```

The body of `TOOL.md` must contain **What it does**, **What it does not do**, an
**Escalation policy** table, and **Known limits**. The limits section is not
optional and it is not a formality. A tool whose author cannot name its weak
spots has not been used enough to be in the library.

## prompt.md

Two headings, `## SYSTEM` then `## USER`. Both halves in one file because a
system prompt and the template it governs drift apart the moment they live
separately — and the version hash covers the whole file, so editing either one
produces a new version.

In the user half, `{{placeholders}}` must all be columns in the declared input.
`verify` checks this against the real file and fails if the prompt asks for
something the export does not have.

Write the system half assuming redacted input. Tokens like `[PERSON_1]` and
`[PERSON_?]` will appear; say what they mean so the model does not try to resolve
them.

## schema.output.json

Closed by default: `"additionalProperties": false`, everything in `required`,
enumerated values wherever a value is a decision rather than free text. A closed
schema is also the main defence against case text talking the model into
producing something nobody agreed to.

Two properties are mandatory and `verify` enforces them:

```json
"needs_human_review": { "type": "boolean" },
"review_reasons": { "type": "array", "items": { "type": "string" } }
```

A tool that cannot escalate does not go in the library.

Keep to the keywords the offline validator supports — `verify` will name any it
cannot check. That restriction exists so the whole thing runs with no pip
install; if you genuinely need more, install `jsonschema` and say so in the tool
spec.

## RUNBOOK.md

Written for the person who will run this, not the person who built it. The test
is simple: could they run it, read the output, and know what to do about each
flag, without you in the room? If not, it is not finished — that is the job, not
the paperwork around it.

Include what to do when it goes wrong, and specifically what to do when it
*clears something it should not have*. That is the failure that matters and it
needs a named route.

## fixtures/

The answer key: one JSON file per input id, named `<input_id>.json`, each
matching the schema. These are what `score` grades a live run against.

Author them somewhere reviewable. Both current tools have their answer key in
`data/build_fixtures.py` — one file Operations can read end to end and sign off,
which then emits the individual fixtures. Twenty loose JSON files is twenty
things nobody checks.

Build the set around the awkward cases. A fixture set of tidy inputs will give
you a high score and tell you nothing.

## Changing an existing tool

1. Edit the prompt, schema or spec.
2. Bump `version` and add a line to the change log in `TOOL.md`.
3. Add or update the fixture that covers what you changed.
4. `python cli.py verify`
5. `python -m unittest discover -s tests`
6. Re-run `score` against a live run and check the review recall has not fallen.

Never fix a bad output by correcting that one case. Fix the prompt, add the
fixture, and let the score prove it stayed fixed.

## What the harness already does for you

Do not reimplement these in a prompt — they are enforced in `lib/` precisely so
that no tool can forget them:

- redaction of names, emails, phones, NI numbers, postcodes, dates of birth
- forced escalation on schema violation, refusal, run failure, unresolved names
- the audit line, with prompt and schema versions
- output validation against the contract
