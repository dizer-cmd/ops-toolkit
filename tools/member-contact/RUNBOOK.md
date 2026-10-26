# Runbook: member contact triage

For contact centre agents and team leaders. It is a pilot: run it alongside the
normal queue, not instead of it, until a live evaluation has been signed off.

## Running it

```bash
python cli.py run member-contact                       # offline sample set
python cli.py run member-contact --provider claude --input data/2026-10-23.csv
```

Input columns:

```
contact_id, received, channel, member_ref, member_name,
contact_name, message, prior_contacts
```

Leave `contact_name` blank when the account holder wrote the message. Fill it in
when somebody else did: that is what lets the tool notice a third party.

## What comes back

Every message gets a `contact_type`, a `priority`, a `route` and an
`agent_next_step`. Messages marked `auto` go straight to their route. Messages
marked `REVIEW` go to the review queue first, with the reasons listed.

`agent_next_step` is a suggestion for you. It is never sent to a member, and it
does not know the account: check the booking or the balance before you act on it.

## The flags, in the order they matter

| Flag | Do this |
|---|---|
| `vulnerability_indicated` | **before anything else.** Specialist support. Do not send a standard reply first. |
| `deceased_member_account` | bereavement process. Do not ask the family to log in or to answer security questions. |
| `suspected_account_takeover` | lock the account and pass to security now. Do not discuss the account in the same channel until security has. |
| `travel_within_72h` | someone owns it today. Check the booking system for the real departure time. |
| `payment_card_in_text` | the member sent a card number. It was removed before the tool saw it and it is not in the output. Do not copy it anywhere; tell the member never to send card details by message, and follow the card-data process. |
| `data_protection_request` | log it today. The one-month statutory clock started when the message arrived. |
| `irreversible_request` | confirm with the member directly before closing, transferring or cancelling anything. |
| `third_party_authority_unverified` | somebody is writing for the account holder. Disclose nothing and change nothing until authority is checked. |
| `refund_or_compensation_requested` | money or goodwill points are being asked for. Never actioned from this output. |
| `complaint_detected` | log as a complaint today. |
| `non_english_content` | route for translation. Do not act on a guessed reading. |
| `ambiguous_person_reference` | a name in the message could be either of two people on the file. Establish who is meant. |

## The one that is not on the list

If a message comes back `auto` and you think it should not have, that is the
finding worth reporting. Send the `contact_id`, the run id and what should have
happened. It becomes a prompt change, a version bump and a new fixture, so the
same miss cannot happen twice without the score showing it.

## What is recorded

One line per message in `runs/audit.jsonl`: prompt version, model, decision,
redaction counts, who ran it. The message text is not in the log, only a
checksum of it.

```bash
python cli.py audit --tail 20
```
