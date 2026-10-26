---
id: member-contact
name: Member contact triage
version: 1.0.0
owner: Operations
status: pilot
input: data/member_contacts.synthetic.csv
id_field: contact_id
name_fields: [member_name, contact_name]
text_fields: [message]
score_fields: [contact_type, priority, route]
model: claude-opus-5
effort: medium
sla_seconds: 20
---

# Member contact triage

## What it does

Reads one inbound message to a loyalty programme's customer contact team (chat,
email, web form or social DM) and decides three things before an agent opens it:
what the member is asking for, how fast it has to move, and which team owns it.
It also writes one line for the agent: the first thing to do or ask.

Most contact in a points programme is routine: missing points, expiry
questions, a password that will not reset. Those clear straight to the right
queue or to a standard answer. The value is in the rest: the reward flight that
leaves on Thursday, the redemption the member never made, the widow asking what
happens to her husband's points. Those must never sit in the ordinary queue.

## What it does not do

It does not reply to anybody, credit or move points, change a booking, issue a
refund or close an account. An agent does all of that. `agent_next_step` is a
suggestion for the agent, never text sent to a member.

It does not see the member's account. It cannot check a balance, a booking or a
transaction history, so everything it says is based on the message alone.

## Programme rules it applies

These are the (fictional) programme's own rules, written into the prompt:

- Points from flights and partners normally appear within 7 days of travel or
  purchase. Before 7 days, the standard answer is to wait; after 7 days it is a
  missing points claim for the points team.
- Points expire after 36 months with no earning or spending. Any activity resets
  the clock.
- Members at the same address can pool points online; no agent is needed.

## Escalation policy

Beyond the harness rules (schema violation, refusal, unresolved names, a payment
card number in the message):

| Trigger | Why |
|---|---|
| travel within the next 72 hours | a slow reply can mean a missed flight; a person owns it today |
| suspected account takeover, or activity the member does not recognise | points are money; security sees it before anything else happens |
| any vulnerability indicator: bereavement, illness, financial hardship, distress, difficulty coping | specialist support, never a standard answer |
| the account holder has died | bereavement process, whatever the message asks for |
| a complaint, or compensation, a refund or goodwill points asked for | money leaving the business is never an automatic decision |
| a data protection request: access, correction or erasure | a statutory one-month clock starts on receipt |
| an irreversible request: closing the account, moving points to someone else, cancelling a booking | cannot be undone; confirm with the member directly |
| someone other than the account holder is writing | authority unverified; nothing is disclosed or changed until it is checked |
| message not in English | do not act on a guessed translation |

## Known limits

- **Travel dates come from the message.** If a member does not say when they
  fly, the 72-hour rule cannot fire. The booking system is the real source of
  truth and this tool does not see it.
- **The member's word is taken on trust.** "My points are missing" is not checked
  against the account.
- **Membership numbers are passed through, not redacted.** Like client references
  in the other tools, they identify an account only to someone holding the member
  database. Recorded in `GOVERNANCE.md` as a residual risk.
- **Age alone is not treated as vulnerability** (`MBR-0213`, an 84-year-old member
  whose daughter writes for her). That is a policy choice for the tool's owner to
  confirm, not a settled fact.
- **Pilot.** No live evaluation yet. Replay proves the harness, not the model.

## Change log

| Version | Change |
|---|---|
| 1.0.0 | First cut. 17 synthetic contacts: 6 that should clear and 11 that must reach a human, so that precision is measurable from the first run (the complaint set taught that a set of only awkward cases cannot measure it). Adding this tool exposed a harness gap: members paste card numbers into messages. The redactor now removes Luhn-valid card numbers before egress, never re-hydrates them, and forces review. |
