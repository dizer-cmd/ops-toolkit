#!/usr/bin/env python3
"""
The answer key for case-intake, authored in one reviewable place.

Expected outputs are a business decision, not a technical one. Twelve loose JSON
files are twelve things nobody reads. This file is one thing Operations can sit
down with, argue about, and sign off — and it emits the fixtures the harness
actually uses.

    python data/build_fixtures.py

Summaries are written with redaction tokens in them on purpose. That is how they
are stored; the harness re-hydrates them locally, so the operator reads a name
and the fixture on disk does not contain one.
"""

from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "tools" / "case-intake" / "fixtures"


def case(case_id, case_type, priority, queue, summary, *,
         ref=True, deadline=None, missing=None, review=False, reasons=None):
    return {
        "case_id": case_id,
        "case_type": case_type,
        "priority": priority,
        "client_ref_present": ref,
        "stated_deadline": deadline,
        "routing_queue": queue,
        "missing_information": missing or [],
        "needs_human_review": review,
        "review_reasons": reasons or [],
        "summary": summary,
    }


KEY = [
    case("CASE-0001", "new_claim", "P3", "intake_team",
         "New workplace injury claim from [PERSON_1], incident 12 August 2026, "
         "medical note and incident report supplied. Ready to open."),

    case("CASE-0002", "additional_evidence", "P3", "evidence_team",
         "Occupational health report from [PERSON_1] to be added to the existing "
         "file. No other change requested."),

    # v1.0.1: was P2. A missing reference blocks the work, it does not make it
    # urgent. Review is what gets it looked at, and review is already on.
    case("CASE-0003", "new_claim", "P3", "intake_team",
         "First contact from [PERSON_1] opening a claim, no client reference "
         "supplied. Needs a file creating or matching before it can be worked.",
         ref=False, missing=["client_reference"],
         review=True, reasons=["client_reference_missing"]),

    # v1.0.1: was P1, which contradicted the prompt's own P1 definition. A new
    # complaint starts a clock; on day one nothing is at risk yet. It reaches a
    # human regardless, which is the control that matters.
    case("CASE-0004", "complaint", "P2", "complaints",
         "[PERSON_1] is dissatisfied with how the matter has been handled and has "
         "asked for it to be escalated. Log as a complaint today.",
         review=True, reasons=["complaint_detected"]),

    case("CASE-0005", "chase", "P1", "safeguarding",
         "[PERSON_1] is recently bereaved and distressed, and is asking whether "
         "the claim closes if she does not reply by the date on the letter.",
         review=True, reasons=["vulnerability_indicated"]),

    case("CASE-0006", "out_of_scope", "P4", "return_to_sender",
         "Boiler warranty enquiry from [PERSON_1]. Not this organisation's "
         "business; confirm before returning the correspondence.",
         ref=False, review=True, reasons=["out_of_scope_requires_confirmation"]),

    case("CASE-0007", "chase", "P1", "intake_team",
         "[PERSON_1] reports that the response deadline on the letter contradicts "
         "the letter's own date. Establish the real deadline before replying.",
         deadline="05/03/2026",
         review=True, reasons=["contradictory_dates"]),

    case("CASE-0008", "chase", "P2", "intake_team",
         "[PERSON_1] was told by phone that an assessment was booked but the "
         "letter says otherwise, and wants it confirmed before taking leave.",
         review=True, reasons=["ambiguous_person_reference"]),

    # v1.0.2: was P2. A missing attachment blocks the work; it does not make it
    # urgent. Same principle as CASE-0003, which v1.0.1 applied there and not
    # here -- the model applied it consistently and the key had not.
    case("CASE-0009", "additional_evidence", "P3", "evidence_team",
         "[PERSON_1] refers to enclosed wage slips and a GP letter, but nothing "
         "is attached. Request the documents before routing.",
         missing=["referenced_attachment_absent"],
         review=True, reasons=["referenced_attachment_absent"]),

    case("CASE-0010", "withdrawal", "P1", "intake_team",
         "[PERSON_1] asks to withdraw the claim entirely and stop contact. "
         "Irreversible; confirm directly with the claimant before actioning.",
         review=True, reasons=["irreversible_request"]),

    # Still NOT flagged as a duplicate of CASE-0001 -- the tool sees one row at a
    # time and cannot know. See ROADMAP.md -> cross-row duplicates.
    #
    # v1.0.1 flagged this for missing contact details. v1.0.2 reverts that: it
    # was a key change made from a single run, without a matching rule in the
    # prompt -- the exact mistake the evaluation is supposed to prevent, and it
    # cost a point of review recall on the next run.
    #
    # On the merits the revert is also right. The reference is present and
    # well-formed, so the contact details are on the file. A populated
    # `missing_information` records a gap; it is not by itself a reason to take
    # a case to a person.
    case("CASE-0011", "new_claim", "P3", "intake_team",
         "New workplace injury claim from [PERSON_1], incident 12 August 2026, "
         "medical note supplied. No contact details in this submission.",
         missing=["claimant_contact_details"]),

    # v1.0.2: was P2, for the same reason as CASE-0009. Needing translation
    # blocks the reply; it does not put anything at risk this week.
    case("CASE-0012", "unclear", "P3", "intake_team",
         "Correspondence from [PERSON_1] is not in English and asks for contact "
         "in Polish. Route for translation; do not act on a guess.",
         review=True, reasons=["non_english_content"]),
]


COMPLAINTS_OUT = OUT.parent.parent / "complaint-triage" / "fixtures"


def complaint(cid, category, severity, action, summary, *,
              vulnerable=False, clock=True, redress=False, review=True, reasons=None):
    return {
        "complaint_id": cid,
        "category": category,
        "severity": severity,
        "vulnerability_indicated": vulnerable,
        "regulated_clock_started": clock,
        "redress_sought": redress,
        "next_action": action,
        "needs_human_review": review,
        "review_reasons": reasons or [],
        "summary": summary,
    }


COMPLAINT_KEY = [
    # v1.0.1: was the one auto-cleared complaint. The first live run pointed out
    # that "I first wrote on 20 August" does not establish whether that letter
    # was a formal complaint -- and the answer decides when the regulated clock
    # started. That is a real question and it belongs to a person.
    # v1.0.2: severity was medium. v1.0.1 added the rule that an unacknowledged
    # complaint is a clock at risk and therefore high -- and then failed to
    # apply that rule to the key. The model applied it; the key had not caught
    # up with its own prompt.
    complaint("CMP-0101", "service_delay", "high", "acknowledge_and_investigate",
              "[PERSON_1] has had no update on booking an assessment since first writing on "
              "20 August. Establish whether that letter started the clock, then acknowledge.",
              reasons=["clock_start_date_ambiguous"]),

    complaint("CMP-0102", "staff_conduct", "high", "escalate_senior",
              "[PERSON_1] alleges the handler on her file talked over her, told her she was "
              "wasting his time and ended the call. Conduct allegation, not a service issue.",
              reasons=["staff_conduct_allegation"]),

    # v1.0.1: was service_quality. Re-reading it, no service failure is alleged
    # anywhere -- it is an access request made on someone's behalf. The key had
    # asserted a category the document does not support. The vocabulary has no
    # slot for a reasonable-adjustment request; logged to ROADMAP rather than
    # invented mid-evaluation.
    complaint("CMP-0103", "unclear", "high", "safeguarding_referral",
              "[PERSON_1] writes for his brother, who has a learning disability, is anxious "
              "and has stopped opening post. Power of attorney asserted; verify before "
              "redirecting correspondence.",
              vulnerable=True, clock=False,
              reasons=["vulnerability_indicated", "third_party_authority_unverified"]),

    # v1.0.1: was outcome_dispute. The letter threatens the ombudsman but never
    # says what the complaint is about. The key inferred a category from the file
    # reference; the text does not support one.
    complaint("CMP-0104", "unclear", "high", "escalate_legal",
              "[PERSON_1] has taken legal advice and will refer to the ombudsman in fourteen "
              "days. 62 days since first contact — check the response clock today.",
              reasons=["external_escalation_threatened", "clock_may_be_breached"]),

    complaint("CMP-0105", "data_or_privacy", "critical", "data_incident_process",
              "A letter containing [PERSON_1]'s date of birth and National Insurance number "
              "was delivered to the wrong address and read by a third party. Possible "
              "personal data breach — start the incident process today.",
              reasons=["possible_data_breach"]),

    complaint("CMP-0106", "process_complaint", "high", "escalate_senior",
              "[PERSON_1]'s earlier complaint was never acknowledged and she is being asked "
              "to resubmit. Do not route this back into the same process.",
              reasons=["complaint_about_complaints_process"]),

    # v1.0.1: was service_delay + acknowledge_and_investigate. What is late is
    # the *final response to a complaint* -- that is the complaints process, by
    # the prompt's own definition, and process complaints route to a senior
    # owner. The key read the surface topic and was internally inconsistent with
    # the next_action vocabulary it shipped with.
    complaint("CMP-0107", "process_complaint", "critical", "escalate_senior",
              "Sixth letter from [PERSON_1] since July; a written eight-week final response "
              "commitment is 71 days old. Treat the deadline as breached until proven "
              "otherwise.",
              reasons=["clock_may_be_breached"]),

    complaint("CMP-0108", "outcome_dispute", "high", "acknowledge_and_investigate",
              "[PERSON_1] disputes the decision, says the consultant's report was not read "
              "properly, and is asking for two unpaid days off work to be reimbursed.",
              redress=True, reasons=["redress_sought"]),
]


MEMBERS_OUT = OUT.parent.parent / "member-contact" / "fixtures"


def member(cid, contact_type, priority, route, next_step, summary, *,
           travel=False, vulnerable=False, review=False, reasons=None):
    return {
        "contact_id": cid,
        "contact_type": contact_type,
        "priority": priority,
        "route": route,
        "travel_within_72h": travel,
        "vulnerability_indicated": vulnerable,
        "needs_human_review": review,
        "review_reasons": reasons or [],
        "agent_next_step": next_step,
        "summary": summary,
    }


MEMBER_KEY = [
    # Six that should clear. Without them precision cannot be measured: the
    # complaint set is all awkward cases, so "flag everything" scores 100% there.
    member("MBR-0201", "missing_points", "P3", "points_team",
           "Travel was 18 days ago, past the 7-day window: open a missing points claim "
           "against booking QX7P2L.",
           "[PERSON_1] flew Calder Airways CA412 on 2 October and the points have not "
           "posted."),

    member("MBR-0202", "missing_points", "P4", "self_service_reply",
           "Stay ended 2 days ago, inside the 7-day posting window: send the standard "
           "'please allow 7 days' answer.",
           "[PERSON_1] stayed at Harbourline Hotels Leeds 16 to 18 October and is asking "
           "why the points have not appeared yet."),

    member("MBR-0203", "general_enquiry", "P4", "self_service_reply",
           "Send the standard household pooling answer; members at the same address can "
           "set it up online.",
           "[PERSON_1] asks whether points can be pooled with a partner at the same "
           "address."),

    member("MBR-0204", "account_access", "P3", "account_support",
           "Check the email address on the account and resend the reset link; no travel "
           "booked.",
           "[PERSON_1] is not receiving password reset emails and wants to check the "
           "balance."),

    member("MBR-0205", "points_expiry", "P4", "self_service_reply",
           "Send the standard expiry answer: any earning or spending before 31 December "
           "keeps the points.",
           "[PERSON_1] has 2,400 points due to expire on 31 December and asks how to keep "
           "them."),

    member("MBR-0206", "holiday_booking", "P3", "holidays_team",
           "Add airport transfers to the Tenerife package departing 14 March and confirm "
           "the price before charging.",
           "[PERSON_1] wants airport transfers added to a Lodestar Holidays package in "
           "March."),

    # Eleven that must reach a person.
    member("MBR-0207", "reward_booking", "P1", "reward_bookings",
           "Correct the surname on the reward booking today; the flight to Malaga leaves "
           "Thursday 22 October.",
           "[PERSON_1]'s surname is misspelt on a Northwind Air reward booking departing "
           "in two days.",
           travel=True, review=True, reasons=["travel_within_72h"]),

    member("MBR-0208", "account_security", "P1", "security_team",
           "Lock the account and pass to security now; do not discuss the redemption until "
           "security has.",
           "[PERSON_1] reports a 40,000-point hotel redemption in Dubai they did not make.",
           review=True, reasons=["suspected_account_takeover"]),

    member("MBR-0209", "deceased_member", "P2", "specialist_support",
           "Bereavement process: offer condolences and explain the transfer to next of "
           "kin; do not ask for logins.",
           "[PERSON_2] reports that her husband [PERSON_1], the account holder, died last "
           "month and asks whether his 90,000 points can move to her.",
           vulnerable=True, review=True,
           reasons=["deceased_member_account", "vulnerability_indicated"]),

    # The card number never reaches the model, and never comes back in the
    # output either. The harness adds payment_card_in_text on its own.
    member("MBR-0210", "reward_booking", "P3", "reward_bookings",
           "Check the cancellation and refund the taxes to the original payment method; "
           "never use card details sent by message.",
           "[PERSON_1] cancelled a reward flight and asks for £186.40 in taxes back, "
           "quoting a card number in the message.",
           review=True, reasons=["payment_card_in_text", "refund_or_compensation_requested"]),

    member("MBR-0211", "complaint", "P2", "complaints",
           "Log as a complaint today and investigate the Brightcard points for July and "
           "August.",
           "[PERSON_1] is chasing Brightcard points for the third time and asks for "
           "compensation.",
           review=True, reasons=["complaint_detected", "refund_or_compensation_requested"]),

    member("MBR-0212", "data_request", "P2", "data_protection",
           "Log the subject access request today; the one-month clock started on 22 "
           "October.",
           "[PERSON_1] requests a copy of all personal data held, including call "
           "recordings.",
           review=True, reasons=["data_protection_request"]),

    # Age alone is not a vulnerability indicator: a policy choice, recorded as an
    # open question in TOOL.md. "Mrs Hollis" matches both people on the file,
    # which the harness flags as an unresolved name.
    member("MBR-0213", "reward_booking", "P3", "reward_bookings",
           "Verify the daughter's authority to act for the account holder before "
           "discussing or booking anything.",
           "[PERSON_2] writes for her mother [PERSON_1], who wants to book a reward flight "
           "for another family member in December.",
           review=True,
           reasons=["third_party_authority_unverified", "ambiguous_person_reference"]),

    member("MBR-0214", "account_access", "P3", "account_support",
           "Route for a Spanish-speaking agent or translation; member is locked out and "
           "has a reward flight next month.",
           "[PERSON_1] writes in Spanish: locked out since yesterday, reward flight next "
           "month.",
           review=True, reasons=["non_english_content"]),

    member("MBR-0215", "data_request", "P2", "data_protection",
           "Confirm with the member directly before closing the account and starting "
           "erasure; log the request today.",
           "[PERSON_1] asks to close the account and have all personal data deleted.",
           review=True, reasons=["irreversible_request", "data_protection_request"]),

    member("MBR-0216", "reward_booking", "P2", "specialist_support",
           "Specialist support first: the member cannot afford the taxes and a parent is "
           "in hospital.",
           "[PERSON_1] lost her job, cannot afford £300 in taxes on a reward flight to see "
           "her father in hospital, and asks for help.",
           vulnerable=True, review=True, reasons=["vulnerability_indicated"]),

    member("MBR-0217", "points_transfer", "P3", "points_team",
           "Confirm the transfer with the member directly and check both accounts before "
           "moving any points.",
           "[PERSON_1] asks to move 20,000 points to his brother's account LS-46672108.",
           review=True, reasons=["irreversible_request"]),
]


def emit(entries, out_dir, id_key):
    out_dir.mkdir(parents=True, exist_ok=True)
    for entry in entries:
        path = out_dir / f"{entry[id_key]}.json"
        path.write_text(json.dumps(entry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    flagged = sum(1 for e in entries if e["needs_human_review"])
    print(f"{out_dir.parent.name}: {len(entries)} fixtures, "
          f"{flagged} of {len(entries)} must reach a human")


if __name__ == "__main__":
    emit(KEY, OUT, "case_id")
    emit(COMPLAINT_KEY, COMPLAINTS_OUT, "complaint_id")
    emit(MEMBER_KEY, MEMBERS_OUT, "contact_id")
