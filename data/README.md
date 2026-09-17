# Synthetic data

**Everything in this directory is invented.** Fictional people, fictional
employers, invented reference numbers, and National Insurance numbers that
deliberately use prefix letters the real allocation rules never issue (`QQ`,
`ZZ`), so no value here can collide with a real registration. No real case, real
person or real client has been involved at any point.

The datasets exist so that the toolkit can be demonstrated, tested and scored
without real case data ever being loaded onto a machine to "show what it could
do".

```
generate.py                rebuild both datasets (deterministic, no seed needed)
build_fixtures.py          the answer key, in one reviewable file
cases.synthetic.csv        12 inbound cases      -> tools/case-intake
complaints.synthetic.csv   8 complaints/appeals  -> tools/complaint-triage
```

Rebuild:

```bash
python data/generate.py
python data/build_fixtures.py
```

## What is being tested

The tidy rows are there to give the awkward ones something to hide among. These
are the ones that matter.

### cases.synthetic.csv

| Case | Problem | What it tests |
|---|---|---|
| `CASE-0003` | no client reference | required-field handling |
| `CASE-0004` | a complaint written as a polite chase | classification by substance, not keyword |
| `CASE-0005` | bereavement and distress mentioned in passing | vulnerability outranks everything else |
| `CASE-0006` | wrong organisation entirely | out-of-scope handling without silently binning it |
| `CASE-0007` | two dates that contradict each other | flagging rather than picking one |
| `CASE-0008` | claimant and handler share a first name | unresolved person reference |
| `CASE-0009` | "please find attached", nothing attached | claim-versus-evidence mismatch |
| `CASE-0010` | withdrawal request | irreversible action never automated |
| `CASE-0011` | **exact resubmission of `CASE-0001`** | a known gap, left visible — see below |
| `CASE-0012` | written in Polish | not acting on a guessed translation |

### complaints.synthetic.csv

| Complaint | Problem | What it tests |
|---|---|---|
| `CMP-0102` | conduct allegation about the named handler | must not route to the person it is about |
| `CMP-0103` | carer writing for a disabled brother, claims power of attorney | vulnerability plus unverified third-party authority |
| `CMP-0104` | ombudsman and solicitor mentioned, 62 days elapsed | external escalation and a clock at risk together |
| `CMP-0105` | letter delivered to a neighbour, read by them | possible personal data breach |
| `CMP-0106` | a complaint about the complaints process | must not be routed back into it |
| `CMP-0107` | 71 days against a written 8-week commitment | breached deadline |
| `CMP-0108` | outcome dispute with money asked for | redress never actioned automatically |

## About CASE-0011

It is an exact resubmission of `CASE-0001`, and **the duplication is still not
detected**. Each tool sees one row at a time and genuinely cannot know. Writing a
fixture that claimed otherwise would make the score look better and the toolkit
worse, because it would be scoring a capability that does not exist. Closing the
gap needs cross-row state — the first item on `ROADMAP.md`.

It does record `claimant_contact_details` in `missing_information`, because
unlike `CASE-0001` this submission carries none. That is a gap worth noting, not
a reason to take the case to a person — the reference is present, so the contact
details are on the file.

## Answer key changes

The key is not static, and it is not adjusted to make scores look better. Ten
entries have changed across two live runs, each with the reasoning recorded in
the source beside the entry and argued in full in `docs/EVAL-2026-09-16.md`.

That document is worth reading before trusting any of these expected values. It
includes one change that was wrong — made from a single run without a matching
rule in the prompt, which cost a point of review recall on the following run and
was reverted. It is left in the record rather than tidied away, because the
discipline of not tuning the key to fit the model is easier to write down than to
keep.

## Getting a real "before" number

The datasets cannot tell you what triage costs today. Measure it: stopwatch, ten
real items, triage them by hand, divide, multiply by weekly volume. The method is
at the bottom of `ROADMAP.md`. Twenty minutes of measuring beats any estimate.
