# Roadmap

What is built, what is next, and what each one is worth. Kept in the repo rather
than a deck, so it is updated by the person doing the work on the day they do it.

Hours are stated as "per week, at current volume" and every one of them is a
**placeholder until measured**. The method for measuring is at the bottom; it
takes about twenty minutes per workflow and it is worth more than any estimate on
this page.

---

## Built

| Tool | Version | Status | What it replaces |
|---|---|---|---|
| `case-intake` | 1.0.2 | live | the first read of an inbound case — deciding where it goes and what is missing |
| `complaint-triage` | 1.0.2 | live | the first read of a complaint — what it is about, how serious, whose desk |

Both are triage. Neither decides anything. That is the deliberate starting point:
the first read of a case is high volume, low judgement per unit, and currently
done twice — once to route it and again by whoever it was routed to.

---

## Next

Ordered by value over effort, not by interest.

### 1. Cross-row duplicate detection — `intake-dedupe`

**Problem.** Each tool sees one row at a time, so a resubmission is processed
twice and lands on two desks. `CASE-0011` in the sample set is exactly this, left
deliberately unflagged so the gap is visible rather than implied.

**Approach.** Not a model problem. A content hash over normalised
`client_ref + incident date + body`, plus near-duplicate detection on the body,
run across the batch before triage. Cheap, deterministic, testable, no API call.

**Worth.** Two handlers opening the same case is the most annoying failure in the
list and the easiest to remove. **Effort: a day.** Do this first.

---

### 2. Reference validation against the case system — `ref-check`

**Problem.** `client_ref_present` means present and well-formed. It does not mean
the file exists. A tidy-looking reference that matches nothing still reaches a
desk before anyone notices.

**Approach.** A lookup against the case system, as a harness step rather than a
tool — same category as redaction, something no prompt should be trusted to do.
Turns `client_reference_missing` into three distinct outcomes: missing,
present-but-unmatched, matched.

**Worth.** Also fixes the `days_since_first_contact` trust problem in
`complaint-triage`, because the real date comes from the system rather than the
export. **Effort: depends entirely on whether a read API exists.** Establish that
before estimating anything.

---

### 3. Client performance narrative — `narrative-draft`

**Problem.** Somebody writes the commentary that goes on top of a client's
performance report every month. The numbers are already produced; the writing is
the slow part, and it varies by who wrote it.

**Approach.** Structured figures in, draft commentary out, against a house
template. Every claim in the draft must cite the figure it came from — a
narrative tool that can assert a number it was not given is not usable, so the
output contract ties each statement to a source field.

**Worth.** This is the one with an external reader. A client's experience of a
report matters as much as its accuracy, so it also carries the most reputational
risk and needs the tightest review step. **Effort: two to three days**, most of
it on the contract, not the prompt.

---

### 4. Ordinary complaints in the evaluation set

**Problem.** The complaint set is eight awkward cases, and after the first live
evaluation all eight correctly reach a human. That is useful for recall and
useless for precision: a set where everything should be flagged cannot measure
over-flagging. The 87.5% precision reported on 16 September means nothing.

**Approach.** Add six to eight routine complaints — well-evidenced, unambiguous,
inside the clock, no vulnerability — that *should* clear automatically. Author
them in `data/build_fixtures.py` like the rest.

**Worth.** Without this there is no honest answer to "how often will it flag
something it should not have", which is the second question anybody asks.
**Effort: half a day.** Cheap, and it gates the value of every future
evaluation.

---

### 5. A category for access and adjustment requests

**Problem.** `CMP-0103` — a carer writing on behalf of a brother with a learning
disability, asking that correspondence be redirected — has no category. It is not
a service failure, so the honest answer is `unclear`. The vocabulary has no slot
for a reasonable-adjustment or access request, and those are neither rare nor
trivial in a regulated operation.

**Approach.** Do not guess at it from one example. Count how often `unclear` comes
back across a real week, read them, and add the category the data asks for rather
than the one that seems tidy.

**Worth.** Moderate on volume, high on getting adjustments handled as adjustments
rather than as complaints. **Effort: a day, after the counting.**

---

### 6. Adversarial pass on prompt injection

**Problem.** Case text is untrusted input. The closed output schema means an
injected instruction cannot invent a field or a value, but it could still push a
classification.

**Approach.** A fixture set of complaints with injection attempts written into
them, scored the same way as everything else. Failures become permanent test
cases.

**Worth.** Not a productivity item. It is what makes the answer to "what if
someone writes instructions into a complaint" a number instead of a shrug.
**Effort: a day**, and it should happen before item 3 goes near a client.

---

### 7. Internal dataset interpretation — `dataset-explain`

**Problem.** Questions about internal datasets get answered by whoever knows
where the data is.

**Approach.** Deliberately last. This is the workflow where a confident wrong
answer is hardest to notice, because there is no claimant to contradict it. It
needs the review and scoring machinery to be trusted first, on workflows where
mistakes surface quickly.

**Worth.** High if it works, and the easiest of all of these to deploy badly.

---

## Not doing, and why

| Idea | Why not |
|---|---|
| Letting a tool close, reject or action a case | The value here is the first read. Automating the decision multiplies the cost of every error and changes the governance conversation entirely. |
| One general assistant instead of narrow tools | It cannot be versioned, scored, or signed off. "Which prompt decided this?" has no answer. |
| A web front end | Operators live in the case system. Another tab is a tool nobody opens. Output goes back where the work already is. |
| Fine-tuning | There is no volume of graded examples yet. Fixtures first; revisit when the answer key is in the hundreds. |

---

## How to get the hours number honestly

Do not estimate it. Measure it, once, per workflow:

1. Stopwatch, blank spreadsheet.
2. Triage **ten** real items by hand — where does it go, what is missing, does it
   need escalating. Include the awkward ones; do not cherry-pick the tidy ones.
3. Stop the clock. Divide by ten, multiply by weekly volume.

Then run the same ten through the tool, time that, and count how many came back
`REVIEW` that did not need to. The line you can then say is:

> *N* cases a week. **X minutes** by hand, **Y minutes** reviewing flagged ones,
> and *Z* that used to be read twice are now read once.

Whatever your number is, it is the one to quote — and you can say you timed it,
which is unusual.
