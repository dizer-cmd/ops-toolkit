#!/usr/bin/env python3
"""
Rebuild the synthetic datasets. Deterministic -- no randomness, no seed needed.

EVERYTHING HERE IS INVENTED. Fictional people, fictional employers, invented
reference numbers, and National Insurance numbers that deliberately use prefix
letters the real allocation rules never issue (QQ, BG, ZZ), so no value here can
collide with a real registration. The datasets exist so that this toolkit can be
demonstrated, tested and scored without any real case data ever being involved.

    python data/generate.py

The awkward cases are the point. A triage tool that only handles the tidy ones
is not a triage tool, it is a demo. Each row below that carries a problem is
listed in the README table with what it is testing.
"""

from __future__ import annotations

import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent

CASE_FIELDS = [
    "case_id", "received", "channel", "client_ref",
    "claimant_name", "handler_name", "subject", "body", "attachments",
]

CASES = [
    # --- clean, should clear automatically -----------------------------------
    (
        "CASE-0001", "2026-09-08", "portal", "NGA-44812",
        "Peter Alderton", "Ruth Mbeki",
        "New claim - workplace injury 12 August",
        "I want to start a claim about an injury at work on 12 August 2026. I slipped on an "
        "unmarked wet floor in the loading bay and hurt my lower back. I was signed off for "
        "nine days. My employer is Fenwick Logistics Ltd. You can reach me on "
        "peter.alderton@example.co.uk or 07700 900412. My NI number is QQ 12 34 56 C.",
        "medical_note.pdf;incident_report.pdf",
    ),
    (
        "CASE-0002", "2026-09-08", "email", "NGA-44655",
        "Marguerite Oyelaran", "Ruth Mbeki",
        "Further evidence for existing claim",
        "Please add the attached occupational health report to my existing file. Nothing else "
        "has changed. Marguerite Oyelaran, 14 Selby Rise, BL3 2QF.",
        "occ_health_2026_09.pdf",
    ),
    # --- classification traps ------------------------------------------------
    (
        "CASE-0004", "2026-09-09", "email", "NGA-44201",
        "Desmond Achterberg", "Tomasz Wilk",
        "Following up on my case again",
        "This is the fourth time I have written. Nobody has called me back since 4 June and "
        "the last person I spoke to promised a decision within ten working days. I am not "
        "asking for an update any more, I am telling you that the way this has been handled "
        "is not acceptable and I want it looked at by someone senior.",
        "",
    ),
    (
        "CASE-0005", "2026-09-09", "phone_note", "NGA-44903",
        "Ivy Castellanos", "Tomasz Wilk",
        "Call note - claimant distressed",
        "Claimant rang. Her husband died three weeks ago and he was the one who had been "
        "dealing with all of the correspondence. She became very distressed on the call and "
        "said she is not sleeping and cannot face the paperwork. She asked whether the claim "
        "would be closed if she did not reply by the date on the letter.",
        "",
    ),
    (
        "CASE-0006", "2026-09-09", "post", "",
        "Harold Penketh", "Ruth Mbeki",
        "Enquiry about a boiler warranty",
        "I am writing about the warranty on the boiler installed at my property in March. "
        "The installer gave me this address. I would like the thermostat replaced under the "
        "five year guarantee.",
        "",
    ),
    # --- data-quality traps --------------------------------------------------
    (
        "CASE-0003", "2026-09-10", "email", "",
        "Solveig Ramanathan", "Tomasz Wilk",
        "Starting a claim",
        "I would like to make a claim following an accident on site. I do not have a "
        "reference number yet as this is the first time I have contacted you. "
        "Contact: solveig.r@example.org",
        "photos.zip",
    ),
    (
        "CASE-0007", "2026-09-10", "email", "NGA-45010",
        "Benedict Oyelaran", "Ruth Mbeki",
        "Response deadline",
        "Your letter says I must respond by 05/03/2026 but the letter is dated 2 September "
        "2026. Which is it? I do not want to lose the claim over a typing error.",
        "letter_scan.pdf",
    ),
    (
        "CASE-0008", "2026-09-10", "portal", "NGA-44730",
        "Jane Fairweather", "Jane Okonkwo",
        "Update on my file",
        "Jane said on the phone that the assessment had already been booked, but the letter "
        "I received afterwards says it has not. I would like someone to confirm which is "
        "correct before I take a day off work for it.",
        "",
    ),
    (
        "CASE-0009", "2026-09-11", "email", "NGA-44812",
        "Peter Alderton", "Ruth Mbeki",
        "Documents as requested",
        "As requested, please find attached the wage slips for the three months before the "
        "accident, plus the letter from my GP.",
        "",
    ),
    # --- high-stakes and edge -------------------------------------------------
    (
        "CASE-0010", "2026-09-11", "email", "NGA-44655",
        "Marguerite Oyelaran", "Tomasz Wilk",
        "I want to stop the claim",
        "I have thought about it and I want to withdraw the claim completely. Please close "
        "the file and do not contact me again about it.",
        "",
    ),
    (
        "CASE-0011", "2026-09-11", "portal", "NGA-44812",
        "Peter Alderton", "Ruth Mbeki",
        "New claim - workplace injury 12 August",
        "I want to start a claim about an injury at work on 12 August 2026. I slipped on an "
        "unmarked wet floor in the loading bay and hurt my lower back. I was signed off for "
        "nine days. My employer is Fenwick Logistics Ltd.",
        "medical_note.pdf",
    ),
    (
        "CASE-0012", "2026-09-12", "email", "NGA-45102",
        "Zofia Brzezinska", "Ruth Mbeki",
        "Sprawa odszkodowania",
        "Dzien dobry, pisze w sprawie mojego wniosku o odszkodowanie. Nie rozumiem pisma, "
        "ktore otrzymalam. Czy moge prosic o kontakt po polsku? Numer sprawy NGA-45102.",
        "",
    ),
]


COMPLAINT_FIELDS = [
    "complaint_id", "received", "channel", "client_ref",
    "complainant_name", "handler_name", "text",
    "prior_contacts", "days_since_first_contact",
]

COMPLAINTS = [
    (
        "CMP-0101", "2026-09-14", "email", "NGA-44112",
        "Gordon Speight", "Ruth Mbeki",
        "I first wrote to you on 20 August and I still have not had a proper answer about "
        "when my assessment will be booked. I understand these things take time but a month "
        "with no update is not good enough. Please tell me where it has got to.",
        "1", "25",
    ),
    (
        "CMP-0102", "2026-09-14", "phone_note", "NGA-44380",
        "Annette Delacroix", "Tomasz Wilk",
        "Complainant states that when she rang on 9 September the handler she spoke to "
        "talked over her, told her she was wasting his time, and put the phone down while "
        "she was still speaking. She says she has never been spoken to like that and wants "
        "it dealt with by somebody above him.",
        "3", "18",
    ),
    (
        "CMP-0103", "2026-09-15", "post", "NGA-44507",
        "Colin Ashworth", "Ruth Mbeki",
        "I am writing on behalf of my brother, who has a learning disability and cannot deal "
        "with this himself. He has become very anxious about the letters and has stopped "
        "opening the post. I have power of attorney. Please send everything to me at "
        "22 Ferndale Close, WN1 3PL from now on.",
        "0", "9",
    ),
    (
        "CMP-0104", "2026-09-15", "email", "NGA-44290",
        "Priya Ramasubramanian", "Tomasz Wilk",
        "I have taken advice from my solicitor and unless I hear back within fourteen days "
        "I will be referring this to the ombudsman. I have kept copies of all the "
        "correspondence since March.",
        "5", "62",
    ),
    (
        "CMP-0105", "2026-09-15", "email", "NGA-44631",
        "Wendell Achebe", "Ruth Mbeki",
        "My neighbour has just handed me a letter from you about my claim. It was addressed "
        "to me but delivered to number 47. It has my date of birth and my National Insurance "
        "number on it. She has read it. How did this happen?",
        "1", "4",
    ),
    (
        "CMP-0106", "2026-09-16", "portal", "NGA-44380",
        "Annette Delacroix", "Tomasz Wilk",
        "I made a complaint three weeks ago and nobody has acknowledged it. Now I am being "
        "asked to fill in the same form again. The complaints process is worse than the "
        "problem I was complaining about.",
        "4", "21",
    ),
    (
        "CMP-0107", "2026-09-16", "email", "NGA-44018",
        "Estelle Kowalczyk", "Ruth Mbeki",
        "This is now the sixth time I have written since July. I was told in writing that I "
        "would have a final response within eight weeks. That was well over two months ago.",
        "6", "71",
    ),
    (
        "CMP-0108", "2026-09-16", "email", "NGA-44744",
        "Raymond Ogunbiyi", "Tomasz Wilk",
        "I disagree with the decision on my claim. I do not think the assessor read the "
        "report from my consultant properly. I also had to take two unpaid days off work for "
        "appointments that were cancelled at short notice, and I want that money back.",
        "2", "33",
    ),
]


# Member contact for a loyalty programme. The programme, its airlines, hotels,
# card and supermarket partners are all invented ("Lodestar Rewards", "Calder
# Airways", "Northwind Air", "Harbourline Hotels", "Brightcard", "Fieldmart").
# The one card number used is the published test number 4111 1111 1111 1111,
# which passes the Luhn check and belongs to nobody.
MEMBER_FIELDS = [
    "contact_id", "received", "channel", "member_ref",
    "member_name", "contact_name", "message", "prior_contacts",
]

MEMBERS = [
    # --- routine: should clear to a queue or a standard answer ---------------
    (
        "MBR-0201", "2026-10-20", "chat", "LS-48213077", "Owen Blakemore", "",
        "Hi, I flew Calder Airways CA412 Manchester to Lisbon on 2 October and the points "
        "still haven't shown up. Booking reference QX7P2L. Can you add them please?",
        "0",
    ),
    (
        "MBR-0202", "2026-10-20", "webform", "LS-51190462", "Hannah Ferreira", "",
        "Stayed at Harbourline Hotels Leeds from 16 to 18 October and the points aren't on "
        "my account yet. Is something wrong?",
        "0",
    ),
    (
        "MBR-0203", "2026-10-21", "email", "LS-30027715", "Rupert Achebe", "",
        "Can I pool my points with my partner so we can book one reward flight together? "
        "We live at the same address.",
        "0",
    ),
    (
        "MBR-0204", "2026-10-21", "chat", "LS-62248103", "Katarzyna Bell", "",
        "The password reset email never arrives. I've checked spam. No trips booked, I just "
        "want to check my balance.",
        "1",
    ),
    (
        "MBR-0205", "2026-10-21", "email", "LS-27753390", "Imogen Tarrant", "",
        "My statement says 2,400 points will expire on 31 December. What can I do to keep "
        "them?",
        "0",
    ),
    (
        "MBR-0206", "2026-10-22", "webform", "LS-70031846", "Callum Mistry", "",
        "We've booked a Lodestar Holidays package to Tenerife for 14 March. Can we add "
        "airport transfers to the booking?",
        "0",
    ),
    # --- must reach a person ---------------------------------------------------
    (
        "MBR-0207", "2026-10-20", "chat", "LS-44409218", "Beatrice Okonjo", "",
        "My surname is spelled wrong on our reward flight booking, it says OKONJO-B. We fly "
        "Northwind Air to Malaga on Thursday 22 October. Please fix it, I'm worried we "
        "won't be let on.",
        "0",
    ),
    (
        "MBR-0208", "2026-10-20", "email", "LS-13358820", "Deepak Sorensen", "",
        "There's a redemption on my account for a hotel in Dubai that I never booked and "
        "40,000 points have gone. I've changed my password but I don't know who did this.",
        "0",
    ),
    (
        "MBR-0209", "2026-10-21", "email", "LS-08821654", "Graham Pettifer", "Linda Pettifer",
        "My husband died last month. He had around 90,000 points and we had a holiday "
        "planned for next year. Can the points be moved to my account? I'm sorry if this is "
        "the wrong place, I don't really know what I'm doing with all this. Linda Pettifer",
        "0",
    ),
    (
        "MBR-0210", "2026-10-21", "email", "LS-55620934", "Tobias Wren", "",
        "I cancelled my reward flight last week and was told the taxes would be refunded. "
        "Please put the £186.40 back on my card 4111 1111 1111 1111, expiry 09/28.",
        "1",
    ),
    (
        "MBR-0211", "2026-10-22", "email", "LS-39904417", "Shirin Calloway", "",
        "Third time asking. My Brightcard points for July and August still haven't arrived "
        "and every time I'm told it'll be on the next statement. This is unacceptable and I "
        "want compensation for the time I've wasted chasing it.",
        "2",
    ),
    (
        "MBR-0212", "2026-10-22", "webform", "LS-61175508", "Marcus Delgado-Reyes", "",
        "Under data protection law I am requesting a copy of all the personal data you hold "
        "about me, including recordings of my calls.",
        "0",
    ),
    (
        "MBR-0213", "2026-10-22", "email", "LS-24486731", "Margaret Hollis", "Joanne Hollis",
        "I'm writing for my mum, Mrs Hollis, who is 84 and doesn't use email. She would like "
        "to use her points to book a flight for my sister in December. Can you do that over "
        "email with me?",
        "0",
    ),
    (
        "MBR-0214", "2026-10-23", "chat", "LS-77310259", "Lucía Navarro", "",
        "Hola, no puedo entrar en mi cuenta desde ayer. Tengo un vuelo con puntos el mes que "
        "viene y necesito ver la reserva. ¿Me pueden ayudar?",
        "0",
    ),
    (
        "MBR-0215", "2026-10-23", "email", "LS-19962240", "Gareth Lomax", "",
        "Please close my account and delete everything you hold about me. I don't want to "
        "be a member any more.",
        "0",
    ),
    (
        "MBR-0216", "2026-10-23", "webform", "LS-83357016", "Abigail Nwosu", "",
        "I lost my job in August and money is really tight. I was going to use my points to "
        "fly to see my dad, who's in hospital, but the taxes are £300 and I just can't "
        "afford that. Is there any way to bring them down?",
        "0",
    ),
    (
        "MBR-0217", "2026-10-23", "chat", "LS-46672093", "Fraser Quaye", "",
        "Can you move 20,000 of my points to my brother's account? His membership number is "
        "LS-46672108. He needs them for a flight next month.",
        "0",
    ),
]


def write(path: Path, fields: list[str], rows: list[tuple]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(fields)
        writer.writerows(rows)
    print(f"wrote {path.relative_to(HERE.parent)}  ({len(rows)} rows)")


if __name__ == "__main__":
    write(HERE / "cases.synthetic.csv", CASE_FIELDS, sorted(CASES, key=lambda r: r[0]))
    write(HERE / "complaints.synthetic.csv", COMPLAINT_FIELDS, sorted(COMPLAINTS, key=lambda r: r[0]))
    write(HERE / "member_contacts.synthetic.csv", MEMBER_FIELDS, sorted(MEMBERS, key=lambda r: r[0]))
