#!/usr/bin/env python3
"""
Fill the reviewed public-service dataset with manually authored targets for the
replaced rows, then write final raw outputs + SFT JSONL.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SFT_SYSTEM_PROMPT = """You are a reading support assistant for students with dyslexia.
Your task is to produce a quick summary of dense academic or public-information text.
Return only valid JSON with this schema:
{
  "main_idea": "2 to 3 short sentences",
  "key_points": ["short point 1", "short point 2", "..."]
}
Keep the language clear, simple, and short.
Use a short list of key points.
Do not add information that is not supported by the source text."""


MANUAL_TARGETS: dict[int, dict[str, Any]] = {
    1: {
        "main_idea": "The text explains how to file a complaint about a realtor in Michigan. It shows what information to include, where to send the form, and what the state may do next.",
        "key_points": [
            "Gather clear supporting documents and remove sensitive personal details.",
            "Complete the LARA complaint form with the realtor's information, your losses, and the outcome you want.",
            "Mail the complaint to the state and wait for notice about mediation or investigation.",
        ],
    },
    2: {
        "main_idea": "The text explains how to check a federal tax refund by phone or mobile app. It also lists the details you need before asking for your refund status.",
        "key_points": [
            "Use the IRS refund hotline, the TeleTax system, or the IRS2Go app.",
            "Keep your SSN or ITIN, filing status, and exact refund amount ready.",
            "The automated service shows the latest refund status in the IRS system.",
        ],
    },
    8: {
        "main_idea": "The text explains how to complain about an employer in the United States. It says to document the problem, compare state and federal options, and file with the right agency.",
        "key_points": [
            "Try internal or union steps first and keep written records.",
            "Check whether state law gives stronger protection than federal law.",
            "Follow the complaint process used by the labor agency in your state.",
        ],
    },
    10: {
        "main_idea": "The text explains how Medicare enrollment fits into Social Security and retirement planning. It covers when to apply, who may qualify automatically, and what each part of Medicare covers.",
        "key_points": [
            "Apply around age 65 and watch the initial and general enrollment periods.",
            "Some people with disability or end-stage renal disease qualify automatically.",
            "Learn the difference between Parts A, B, C, D, and Medigap coverage.",
        ],
    },
    26: {
        "main_idea": "The text explains how to qualify for a plumbing license in Florida. It covers experience, insurance, the right license type, and the exam process.",
        "key_points": [
            "Meet age, experience, background check, bond, and insurance requirements.",
            "Choose between a local registered license and a statewide certified license.",
            "Submit the DBPR application, pay the fees, and pass the required exams.",
        ],
    },
    36: {
        "main_idea": "The text explains how to become a notary in Michigan. It covers eligibility, the required bond, the application steps, and filing with the county and state.",
        "key_points": [
            "Check age, residency, language, and criminal record requirements.",
            "Get the required surety bond and complete the notary application.",
            "Take the form to the county clerk, swear the oath, and mail it to the state.",
        ],
    },
    40: {
        "main_idea": "The text explains how a qualified family member or legal representative can request a death certificate in Puerto Rico. It covers the application, identification, payment, and mailing options.",
        "key_points": [
            "Show that you are direct kin or another person allowed to request the record.",
            "Send the application, ID, birth or marriage proof, and a money order.",
            "Mail the packet to the registry or use VitalChek if you need another payment method.",
        ],
    },
    43: {
        "main_idea": "The text explains how to get a death certificate by finding the correct place of death and checking who is allowed to order the record. It also outlines common ordering methods and proof you may need.",
        "key_points": [
            "Find the state, county, or city office that keeps the death record.",
            "Check whether your state limits access to family or other approved people.",
            "Order online, by mail, or in person and include ID and any required proof.",
        ],
    },
    48: {
        "main_idea": "The text explains how to apply for a disabled parking permit in New York. It covers medical certification, the correct form, and where to submit the application.",
        "key_points": [
            "Ask a qualified doctor to certify a temporary or permanent disability.",
            "Complete form MV-664.1 and gather any required ID or residence proof.",
            "Submit the form through the proper county or motor vehicle office.",
        ],
    },
    50: {
        "main_idea": "The text explains how to register to vote in Arizona. It covers eligibility, proof of citizenship, form completion, and what happens after you apply.",
        "key_points": [
            "Make sure you meet the age, citizenship, residency, and rights-restoration rules.",
            "Attach the right citizenship document if your Arizona ID is not enough.",
            "Send the form to the county recorder and wait for confirmation of registration.",
        ],
    },
    57: {
        "main_idea": "The text explains how to apply for a marriage license in Michigan. It covers documents, fees, waiting time, who must appear, and what to do after the ceremony.",
        "key_points": [
            "Bring ID and any documents for divorce, hardship waivers, or prior marriages.",
            "Apply in person or online if the county allows it, then wait for the license to be issued.",
            "Use the license within the valid period and return the signed original to the clerk.",
        ],
    },
    58: {
        "main_idea": "The text explains ways to find a company's federal tax ID number. It starts with ordinary business records and public sources before suggesting outside help.",
        "key_points": [
            "Check invoices, receipts, letters, and the organization's website first.",
            "Use public company and nonprofit databases when they apply.",
            "Contact the IRS or, if necessary, hire a professional as a last resort.",
        ],
    },
    68: {
        "main_idea": "The text explains how to contact immigration authorities for tips, detention help, or detainee searches. It gives official phone numbers and an online locator.",
        "key_points": [
            "Use the ICE tip line or online form to report crimes such as trafficking.",
            "Call the detention information line for help with someone in ICE custody.",
            "Use the detainee locator system to search for adults in recent detention.",
        ],
    },
    72: {
        "main_idea": "The text explains how some people can receive Social Security through a spouse, former spouse, or parent. It focuses on eligibility rules rather than a single application form.",
        "key_points": [
            "A spouse may qualify based on the other spouse's work record.",
            "A divorced spouse may qualify if the marriage lasted long enough and other rules are met.",
            "A child may qualify when a parent receives Social Security and the child meets age or disability rules.",
        ],
    },
    75: {
        "main_idea": "The text explains how to find government help with child care costs. It points families to state contacts, eligibility checks, and local support channels.",
        "key_points": [
            "Use the federal child care contact list to find your state program.",
            "Check income-based eligibility before submitting a full application.",
            "Ask local offices or 211 which providers meet the funding rules.",
        ],
    },
    80: {
        "main_idea": "The text explains how to get a marriage license in Colorado. It covers age rules, ID and Social Security requirements, county filing, and how the signed license is returned after the ceremony.",
        "key_points": [
            "Bring accepted identification and any needed parental or court consent forms.",
            "Apply at a county clerk office, pay the fee, and use an absentee affidavit if needed.",
            "Have the officiant sign the license and return it to the county after the wedding.",
        ],
    },
    82: {
        "main_idea": "The text explains how to apply for a marriage license in Tennessee. It covers documents, county clerk procedures, course discounts, and license validity.",
        "key_points": [
            "Bring proof of age, Social Security information, and any divorce or death records.",
            "Check the county clerk's rules on fees, appointments, and accepted payment methods.",
            "Both applicants must sign, and the license is valid for 30 days.",
        ],
    },
    83: {
        "main_idea": "The text explains how to check immigration status through official USCIS resources. It also warns readers to use translators or attorneys carefully and to avoid people who claim special access.",
        "key_points": [
            "Use USCIS online tools, phone help, or a field office appointment for status information.",
            "The same status details are available online and through the customer service line.",
            "Be careful with paid help and use only licensed attorneys or approved representatives.",
        ],
    },
    86: {
        "main_idea": "The text explains how to file a Cal-OSHA complaint about workplace health or safety hazards. It lists the information to gather, where to report, and how complaints are prioritized.",
        "key_points": [
            "Check that your worksite is covered and describe the hazard in detail.",
            "Gather the employer's information, worksite details, and evidence of the problem.",
            "File by phone, email, or local office and wait for the state to assess inspection priority.",
        ],
    },
    88: {
        "main_idea": "The text explains how to file a consumer complaint in Nevada. It focuses on using the attorney general's complaint forms and choosing the right office or agency.",
        "key_points": [
            "Use the attorney general's complaint form online, on paper, or through electronic submission.",
            "Provide clear details about the business problem and any evidence you have.",
            "Contact the correct regional office or another state agency when the issue is more specific.",
        ],
    },
    89: {
        "main_idea": "The text explains how to track a Social Security claim and what to do after a denial. It outlines the main appeal stages and when legal help may be useful.",
        "key_points": [
            "Read the decision notice to understand the claim outcome and payment timing.",
            "Use reconsideration, an administrative hearing, and later appeals if needed.",
            "A federal court case is possible only after the earlier appeal stages are finished.",
        ],
    },
    94: {
        "main_idea": "The text explains what to do if a passport is lost or stolen while traveling. It covers retracing your steps, filing a police report, and getting help from your embassy.",
        "key_points": [
            "Check the places you visited and ask local lost-property offices first.",
            "File a police report and keep a copy for replacement or insurance purposes.",
            "Contact your embassy for an emergency passport and keep document copies for future travel.",
        ],
    },
    96: {
        "main_idea": "The text explains how to apply for a contractor's license in Nevada. It covers getting the application, proving experience, paying the fee, and handling a rejection.",
        "key_points": [
            "Get the application from the board in person, by phone, or online.",
            "Submit reference certificates, a work history, and any education records.",
            "File in person and use the board's appeal or resubmission options if needed.",
        ],
    },
    97: {
        "main_idea": "The text explains how to request a Rhode Island birth certificate by mail. It covers eligibility, the needed documents, fees, and regular or rush mailing.",
        "key_points": [
            "Make sure you are one of the people allowed to request the certificate.",
            "Send an application or letter, photo ID, and proof of relationship if required.",
            "Include the correct fee and mark the envelope for rush service if you paid for it.",
        ],
    },
    102: {
        "main_idea": "The text explains how to register to vote in Arkansas. It lists where to get the form, what ID or supporting documents may be needed, and how to check your status later.",
        "key_points": [
            "Get the registration form from election offices, the DMV, libraries, or approved agencies.",
            "Provide your personal details and attach ID or address proof when required.",
            "Submit the application and use the state's search tool or county clerk to check status.",
        ],
    },
    109: {
        "main_idea": "The text explains how to apply for a marriage license in Pennsylvania. It covers eligibility, documents, translators, waiting time, fees, and license validity.",
        "key_points": [
            "Bring photo ID, Social Security information, and records from any earlier marriage.",
            "Both applicants must appear, and some cases need a translator or extra approval.",
            "The license usually has a 72-hour wait and stays valid for 60 days.",
        ],
    },
    110: {
        "main_idea": "The text explains how to apply for a marriage license in Missouri. It describes county-specific rules, required ID, payment, and the short life of the license after issue.",
        "key_points": [
            "Check the local recorder's office for fees, hours, and county rules.",
            "Both applicants must appear with valid ID and any documents for prior marriages.",
            "Missouri can issue the license quickly, but it must be used within 30 days.",
        ],
    },
    121: {
        "main_idea": "The text explains how to register to vote in California. It covers online or paper registration, the identification details needed, and what to do after submission.",
        "key_points": [
            "Use your California ID or the last four digits of your Social Security number when available.",
            "If you do not have a state ID, sign and return the mailed registration form.",
            "Wait for the elections office to confirm that your registration was accepted.",
        ],
    },
    123: {
        "main_idea": "The text explains how Social Security disability claims are evaluated and appealed. It focuses on the disability rules, medical-vocational review, and the stages after a denial.",
        "key_points": [
            "The agency looks at the severity of the condition, listings, and work limits.",
            "A medical-vocational allowance may apply even when no listing matches exactly.",
            "Denied claims can move through reconsideration, hearings, council review, and federal court.",
        ],
    },
    129: {
        "main_idea": "The text explains how a U.S. citizen can apply for a visa for Bolivia. It covers checking consular rules, gathering documents, and mailing the application safely.",
        "key_points": [
            "Confirm the current requirements with the correct Bolivian consulate first.",
            "Prepare the yellow fever card, passport photo, travel details, and application form.",
            "Pay with the approved method and mail the packet with tracking and return postage.",
        ],
    },
    134: {
        "main_idea": "The text explains how to check visa status online through the State Department's CEAC system. It shows what case numbers and details you need for immigrant and non-immigrant visas.",
        "key_points": [
            "Find the CEAC number or case number on your visa application notice.",
            "Choose the right visa type and enter the correct interview location or case ID.",
            "Read the status message online and contact the consulate if you have questions.",
        ],
    },
    137: {
        "main_idea": "The text explains what to do when someone believes a marriage involved immigration fraud. It focuses on legal help, the difference between divorce and annulment, and the effect on a green card case.",
        "key_points": [
            "Get legal advice quickly because annulment and immigration issues can overlap.",
            "Check whether your state allows annulment for fraud and what proof is needed.",
            "An annulment may cancel a spouse's immigration application based on the marriage.",
        ],
    },
    145: {
        "main_idea": "The text explains how to renew a work permit or related work authorization. It distinguishes between work visas and employment authorization documents and outlines common renewal steps.",
        "key_points": [
            "Know whether you hold a work visa or an employment authorization document.",
            "Start renewal early and check the expiration and filing rules for your status.",
            "Your employer may handle some visa filings, but you still may need to provide records like Form I-94.",
        ],
    },
    147: {
        "main_idea": "The text explains permit and registration rules for interstate agricultural transportation. It shows how the requirements change with vehicle weight and operating status.",
        "key_points": [
            "Heavier or interstate vehicles may need a USDOT number, UCR registration, or other filings.",
            "Some carriers also need IFTA or IRP registration depending on how they operate.",
            "Federal safety rules may still apply, even when a farm vehicle has some exemptions.",
        ],
    },
    152: {
        "main_idea": "The text explains how Texas unemployment benefits are calculated and what makes someone eligible. It also shows how to estimate benefits and what conditions can block a claim.",
        "key_points": [
            "Use base-period wages to work out the weekly benefit amount and maximum benefit amount.",
            "Quitting without a valid reason or causing your own job loss can disqualify you.",
            "You must register for work, stay available, and meet the state's search requirements.",
        ],
    },
    153: {
        "main_idea": "The text explains how Alaska unemployment benefits are calculated and applied for. It covers covered employment, wage thresholds, continuing eligibility, and payment details.",
        "key_points": [
            "Check that your employer and past work were covered by Alaska unemployment rules.",
            "Review your wages to estimate the weekly amount and any child-based increase.",
            "Apply through the state's system and stay able and available for full-time work.",
        ],
    },
    156: {
        "main_idea": "The text explains how to replace a naturalization certificate. It lists valid reasons for a replacement, the main form, the supporting documents, and the filing fee.",
        "key_points": [
            "Use Form N-565 when a certificate is lost, damaged, or needs an approved legal update.",
            "Attach photos and any proof for a name change, gender change, or damaged document.",
            "Mail the packet to the correct USCIS service center and wait for follow-up if requested.",
        ],
    },
    158: {
        "main_idea": "The text explains how to report immigration fraud in Canada. It covers how to collect facts, choose the right reporting channel, and provide useful details while staying anonymous if needed.",
        "key_points": [
            "Write down names, dates, places, and other identifying details before reporting.",
            "Use the online form or the correct phone line for the type of fraud you suspect.",
            "Share new information later if you learn more after the first report.",
        ],
    },
    171: {
        "main_idea": "The text explains how to qualify for a plumbing license in New York City. It covers the experience routes, exams, affidavits, and proof needed after you pass.",
        "key_points": [
            "Meet the age and English-language requirements and prove one accepted experience path.",
            "Pass the written and practical licensing exams after filing the proper application.",
            "Submit affidavits and Social Security earnings records to document your work history.",
        ],
    },
    172: {
        "main_idea": "The text explains who can register to vote in Maryland and who cannot. It also covers how felony status and overseas residence can affect registration.",
        "key_points": [
            "Check citizenship, residency, age, and legal eligibility before registering.",
            "Some voting restrictions apply, but many people regain eligibility after leaving prison.",
            "Maryland also allows certain U.S. citizens living overseas to register.",
        ],
    },
    173: {
        "main_idea": "The text explains how sponsored guest workers can report visa-related labor violations by an employer. It focuses on gathering evidence, getting legal advice, and reporting to the U.S. Department of Labor.",
        "key_points": [
            "Identify the kind of abuse, such as illegal fees, missing wages, or unsafe housing.",
            "Collect records, photos, and other evidence that support your complaint.",
            "Report the case to the Wage and Hour Division online, by phone, or through a local office.",
        ],
    },
    177: {
        "main_idea": "The text explains how to apply for a marriage license in Washington. It covers age rules, required identification, county filing options, waiting time, and the return of the signed license.",
        "key_points": [
            "Bring accepted ID and either a Social Security number or the required declaration.",
            "Apply through the county office in person, online, or by mail if the county allows it.",
            "Wait three full days, use the license within 60 days, and return it after the ceremony.",
        ],
    },
    180: {
        "main_idea": "The text explains how to request a Delaware birth certificate. It focuses on who may apply, the documents they need, the fee, and how to contact the state offices.",
        "key_points": [
            "Make sure you are the person named on the record or another person allowed to request it.",
            "Prepare the application, photo ID, and any proof of relationship or authority.",
            "Pay the fee with the approved method and contact the correct vital statistics office if needed.",
        ],
    },
    188: {
        "main_idea": "The text explains how to apply for unemployment benefits in Texas. It covers wage requirements, job-loss rules, work-search duties, payment choices, and appeals.",
        "key_points": [
            "Check the base-period wage rules and whether your separation from work qualifies.",
            "Register for work and stay able, available, and willing to accept suitable jobs.",
            "Apply through the Texas Workforce Commission and use the appeal process if denied.",
        ],
    },
    189: {
        "main_idea": "The text explains how to get an expedited U.S. passport. It covers the right forms, supporting documents, fees, where to submit the application, and how to track it.",
        "key_points": [
            "Use the correct passport forms for a new passport or a lost or stolen one.",
            "Bring proof of citizenship, ID, passport photos, and the required payment.",
            "Start the application at an authorized acceptance facility and mail it with tracking.",
        ],
    },
    196: {
        "main_idea": "The text explains how to file a complaint against a realtor in Florida. It covers supporting documents, the complaint form, mailing instructions, and the state's follow-up process.",
        "key_points": [
            "Collect copies of contracts, correspondence, and other documents that support the complaint.",
            "Complete the uniform complaint form with your details, the agent's details, and witness information.",
            "Mail the packet to the DBPR and respond quickly if investigators request more records.",
        ],
    },
    197: {
        "main_idea": "The text explains how to get a first passport. It covers the required identity and citizenship documents, photos, forms, fees, and where to apply in person.",
        "key_points": [
            "Gather proof of citizenship, proof of identity, and a proper passport photo.",
            "Complete Form DS-11 and take it to a local passport office or acceptance facility.",
            "Pay the current fee and apply early if you may need rush service later.",
        ],
    },
    200: {
        "main_idea": "The text explains how to make a medical complaint and choose the right place to send it. It also explains what complaints can and cannot do, and when extra help may be needed.",
        "key_points": [
            "Identify whether the problem involves one provider, a hospital, billing, or a wider system issue.",
            "Complain first to the hospital, review board, or health plan that handles that kind of problem.",
            "Use a patient advocate or attorney if you need help with compensation or a complex case.",
        ],
    },
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def compact_json(obj: dict[str, Any]) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def validate_target(obj: dict[str, Any]) -> None:
    if set(obj.keys()) != {"main_idea", "key_points"}:
        raise ValueError(f"Unexpected keys: {sorted(obj.keys())}")
    if not isinstance(obj["main_idea"], str) or not obj["main_idea"].strip():
        raise ValueError("main_idea must be a non-empty string.")
    if not isinstance(obj["key_points"], list) or not obj["key_points"]:
        raise ValueError("key_points must be a non-empty list.")
    if not all(isinstance(x, str) and x.strip() for x in obj["key_points"]):
        raise ValueError("Every key point must be a non-empty string.")


def build_raw_record(sample: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
    return {
        "sample_index": sample["sample_index"],
        "bucket": sample.get("bucket"),
        "word_count": sample.get("word_count"),
        "wikihow_id": sample.get("wikihow_id", ""),
        "title": sample.get("title", ""),
        "category": sample.get("category", ""),
        "source_url": sample.get("source_url", ""),
        "generator": {"mode": "manual", "name": "manual_content_review_v1"},
        "input_text": sample["text"],
        "target": target,
    }


def build_sft_record(sample: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
    return {
        "messages": [
            {"role": "system", "content": SFT_SYSTEM_PROMPT},
            {"role": "user", "content": sample["text"]},
            {"role": "assistant", "content": compact_json(target)},
        ]
    }


def main() -> int:
    base = Path(__file__).resolve().parent
    samples_path = base / "public_service_200_samples_reviewed.jsonl"
    outputs_path = base / "public_service_200_outputs_reviewed.jsonl"
    sft_path = base / "public_service_200_sft_reviewed.jsonl"
    meta_path = base / "public_service_200_sft_reviewed.meta.json"

    samples = load_jsonl(samples_path)
    existing_outputs = load_jsonl(outputs_path)
    existing_by_idx = {int(row["sample_index"]): row for row in existing_outputs}

    missing = [int(s["sample_index"]) for s in samples if int(s["sample_index"]) not in existing_by_idx]
    manual_keys = sorted(MANUAL_TARGETS)
    if missing != manual_keys:
        raise ValueError(f"Manual target keys do not match missing sample indices.\nmissing={missing}\nmanual={manual_keys}")

    final_raw: list[dict[str, Any]] = []
    for sample in samples:
        idx = int(sample["sample_index"])
        if idx in existing_by_idx:
            final_raw.append(existing_by_idx[idx])
            continue
        target = MANUAL_TARGETS[idx]
        validate_target(target)
        final_raw.append(build_raw_record(sample, target))

    sft_rows = [build_sft_record(sample, row["target"]) for sample, row in zip(samples, final_raw, strict=True)]

    write_jsonl(outputs_path, final_raw)
    write_jsonl(sft_path, sft_rows)
    meta = {
        "input_file": str(samples_path.resolve()),
        "raw_output_file": str(outputs_path.resolve()),
        "sft_output_file": str(sft_path.resolve()),
        "mode": "manual_mixed",
        "total_samples": len(samples),
        "generated_now": len(MANUAL_TARGETS),
        "reused_existing": len(existing_outputs),
        "manual_target_indices": manual_keys,
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote raw outputs to {outputs_path}")
    print(f"Wrote SFT dataset to {sft_path}")
    print(f"Wrote metadata to {meta_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
