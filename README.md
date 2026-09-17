# ops-toolkit

A small, versioned library of AI workflow tools for a case-handling operation —
built so that what works once works identically next Tuesday, in somebody else's
hands, with an audit trail a governance team will accept.

Two tools are live: **case intake triage** and **complaint and appeal triage**.
The interesting part is not either prompt. It is the harness around them, and the
standard both of them have to meet.

---

## Run it in thirty seconds

No API key. No pip install. No network. Python 3.10+.

```bash
python cli.py verify
python cli.py run case-intake
python cli.py audit --tail 5
```

`verify` checks every tool still meets the standard. `run` triages twelve
synthetic cases and routes nine of them to a human, each with a stated reason.
`audit` shows what was run, by whom, and with which version of which prompt.

If anything does not work, `python cli.py doctor` says why — Python version, SDK,
whether a credential is present and whether it is the right shape, and whether
the tools still meet the standard. It never prints the credential itself. An
operator should be able to diagnose a bad setup without the person who built it.

The offline mode serves committed reference outputs rather than calling a model,
so anybody can see the whole pipeline work before deciding whether to give it
credentials. To run it for real:

```bash
pip install anthropic
export ANTHROPIC_API_KEY=...
python cli.py run case-intake --provider claude
python cli.py score case-intake
```

---

## The idea

Most "AI in operations" work dies at the same point. Somebody proves a prompt
works, everyone is impressed, and then it lives in a chat window. Six months
later nobody can say which version of it produced last quarter's decisions, the
person who wrote it has changed jobs, and compliance has never seen it.

So the unit here is not a prompt. It is a **tool**: a directory that must contain
five things before the harness will run it.

```
tools/case-intake/
  TOOL.md              what it does, who owns it, when it must escalate
  prompt.md            the prompt — system and user halves, one file, one hash
  schema.output.json   the output contract
  RUNBOOK.md           how a non-technical operator runs it without you
  fixtures/            the answer key: what the right output looks like
```

`python cli.py verify` fails if any of that is missing, if the schema drifts from
the prompt, if a fixture no longer validates, or if a tool has no way to escalate
to a human. That command is the whole point. It is what stops the library
decaying back into a folder of prompts that used to work.

---

## What the harness guarantees

Four properties, enforced in `lib/` rather than asked of each prompt — because
anything asked of each prompt is eventually forgotten by one of them.

**Identifiers do not leave.** Names, emails, phone numbers, NI numbers,
postcodes and dates of birth are replaced with stable tokens before the prompt is
built. The model reasons about `[PERSON_1]`; the operator reads the name. A name
that could mean two different people on file becomes `[PERSON_?]` and the case is
flagged — the system never guesses which one was meant.

**The harness can only escalate.** A tool can raise its hand. Nothing can lower
one. A schema violation, a model refusal, a failed run or an unresolved name
forces human review regardless of how confident the output was. This is one of
the tested invariants, not a convention.

**The audit log is not a second copy of the case data.** Each run appends one
line: timestamp, operator, tool version, prompt hash, schema hash, model,
decision, redaction counts, and a checksum of the input. Not the input. You can
prove which prompt decided what, without the log becoming a thing that needs its
own retention policy.

**The same input produces the same output.** Prompts are versioned by content
hash. Change a word and the hash changes, so the audit trail can never quietly
attribute today's decisions to yesterday's prompt.

---

## Two numbers, not one

```bash
python cli.py score case-intake
```

Field accuracy is the number people quote. The one that decides whether this is
allowed near real work is **review recall**: of the cases that should have
reached a human, how many did. A tool that is 95% accurate and silently swallows
the other 5% is worse than no tool, because it has replaced a slow process with a
confident one.

Both tools currently score **100% review recall and 100% precision** against the
answer key, with `complaint-triage` at 100% on every measured field and
`case-intake` at 91.7% on two of three. That took four live runs and $1.96, and
the interesting part is what the runs found: three of the four surfaced a defect
in the *specification* rather than in the model, including an escalation policy
that was published in the tool spec and never actually shown to the model.

The whole process — every disagreement, who was right, what changed, and one
change that was wrong and had to be reverted — is in
[`docs/EVAL-2026-09-16.md`](docs/EVAL-2026-09-16.md). It is the most useful
document here.

That is why the sample sets are built the way they are. Twelve intake cases, nine
of which must reach a human; eight complaints, all eight of which must. The awkward
ones are the point — a complaint worded as a polite chase, a bereavement
mentioned in passing, a letter delivered to the wrong address, two dates that
contradict each other, a first name that matches two people.

---

## What it does not do

Worth saying plainly, because a demo that hides its edges is not much use.

- **No duplicate detection.** Each tool sees one row at a time. `CASE-0011` in
  the sample set is a resubmission of `CASE-0001` and is deliberately allowed
  through unflagged rather than faked. First item on `ROADMAP.md`.
- **No memory between runs.** No sense of a case's history.
- **Severity is judged from the account, not the event.** A calmly written
  serious failure can come back rated lower than an angry trivial one. Written
  down in the tool spec, and why severity alone never routes anything.
- **The offline mode measures the harness, not the model.** Reference outputs are
  hand-authored — the answer key, not recordings. `score` against a live run is
  the only number that says anything about model quality.
- **The data is invented.** Every person, employer and reference number here is
  fictional, and the NI numbers use prefixes the real rules never issue. See
  `data/README.md`.

---

## Layout

```
cli.py                 one entry point: list, verify, run, score, audit
lib/                   the harness — redaction, contracts, audit, run loop
tools/                 the library; one directory per tool
data/                  synthetic inputs and the reviewable answer key
tests/                 the claims above, enforced (python -m unittest discover -s tests)
runs/                  run outputs and the append-only audit log
CONTRIBUTING.md        how a new tool gets added, and what it must satisfy
GOVERNANCE.md          the evidence pack: data flows, retention, residual risks
ROADMAP.md             what is built, what is next, and what each is worth
```

---

## Adding a tool

`CONTRIBUTING.md`. Short version: copy the five files, run `verify`, and it will
tell you what you have not done yet.
