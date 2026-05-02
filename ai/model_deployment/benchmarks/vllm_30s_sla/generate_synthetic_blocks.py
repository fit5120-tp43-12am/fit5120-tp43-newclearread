from __future__ import annotations

import json
from pathlib import Path


BENCH_DIR = Path(__file__).resolve().parent
OUT_PATH = BENCH_DIR / "synthetic_500_word_blocks.json"


TOPICS = [
    (
        "heatwave-readiness",
        [
            "The council heatwave plan explains how residents can prepare for several days of extreme heat.",
            "It asks households to check weather alerts, keep water available, and identify cool indoor spaces before the hottest part of the day.",
            "Older people, babies, outdoor workers, and people with chronic health conditions are described as higher-risk groups.",
            "Community centres may extend their opening hours when the heat index reaches a severe threshold.",
            "The plan says neighbours should check on vulnerable people by phone or in person if it is safe to do so.",
            "It also warns that confusion, fainting, and a very high body temperature can be emergency signs.",
        ],
    ),
    (
        "school-library-program",
        [
            "The school library program describes a weekly reading circle for students who want more confidence with complex texts.",
            "Teachers choose short articles, explain unfamiliar vocabulary, and ask students to connect the article to prior knowledge.",
            "Students then write a brief reflection that states the topic, the purpose, and one important supporting detail.",
            "The program is not a replacement for classroom instruction, but it gives learners a quieter space to practise.",
            "Attendance records are used to identify whether the same students need additional literacy support later in the term.",
            "The coordinator says the main goal is to help students feel prepared before they meet longer assessment readings.",
        ],
    ),
    (
        "wetland-restoration",
        [
            "The wetland restoration update describes work to improve water quality and habitat near a suburban creek.",
            "Volunteers removed invasive weeds, planted native grasses, and recorded bird sightings during monthly surveys.",
            "Engineers also repaired a small drain so stormwater would spread across a filter bed before entering the creek.",
            "The report notes that early results are promising, but several seasons of monitoring are needed before drawing firm conclusions.",
            "Residents are asked to stay on marked paths because young plants can be damaged by foot traffic.",
            "The project is funded for two years and will be reviewed against water clarity, species diversity, and community participation measures.",
        ],
    ),
    (
        "clinic-appointment-policy",
        [
            "The clinic appointment policy explains how patients should book, cancel, and prepare for routine visits.",
            "Patients are asked to bring identification, a current medication list, and any referral letter from another health professional.",
            "Same-day appointments are reserved for urgent but non-emergency concerns, while life-threatening symptoms should go to emergency services.",
            "The policy says late cancellations make it harder for other patients to receive care on time.",
            "Reception staff may offer telehealth appointments when the doctor decides a physical examination is not required.",
            "The document also explains that test results are discussed by a clinician rather than sent through informal messages.",
        ],
    ),
    (
        "public-transport-upgrade",
        [
            "The public transport upgrade notice describes changes to bus routes during construction near the central station.",
            "Several stops will move temporarily, and passengers are advised to allow extra travel time during morning peak periods.",
            "The authority says the work will improve accessibility by adding lifts, wider footpaths, clearer signs, and safer crossings.",
            "Local businesses will remain open, but delivery vehicles must use a different loading area until the roadworks finish.",
            "Customer service staff will be stationed near the station entrance during the first week of the changed timetable.",
            "The notice says the temporary inconvenience is expected to reduce once the new interchange layout opens.",
        ],
    ),
    (
        "science-fair-rubric",
        [
            "The science fair rubric explains how student projects will be judged by teachers and visiting scientists.",
            "Marks are awarded for a clear question, a fair testing method, accurate observations, and a conclusion supported by evidence.",
            "Students are reminded that colourful displays are helpful only when they make the experiment easier to understand.",
            "The rubric gives extra credit for identifying limitations, such as small sample sizes or measurement uncertainty.",
            "It also says students must not copy internet explanations without citing the source in their bibliography.",
            "The main purpose is to reward careful thinking rather than expensive equipment or dramatic results.",
        ],
    ),
    (
        "cyber-safety-briefing",
        [
            "The cyber safety briefing explains basic steps staff should follow when handling school account information.",
            "It asks staff to use unique passwords, approve multi-factor prompts only when they initiated a login, and report suspicious emails.",
            "The briefing warns that attackers may imitate familiar colleagues, suppliers, or school platforms to request urgent action.",
            "Staff should not paste student information into unapproved online tools, even when the tool looks helpful.",
            "The technology team will never ask for a password through email or chat.",
            "The document says quick reporting is more useful than hiding a mistake because early action can limit harm.",
        ],
    ),
    (
        "community-garden-guide",
        [
            "The community garden guide explains how members share plots, tools, compost, and watering duties.",
            "New members attend an induction so they understand safety rules, organic gardening expectations, and the booking calendar.",
            "The guide says gardeners may harvest produce only from their allocated plot unless another member has given clear permission.",
            "Working bees are scheduled each month to maintain shared paths, repair beds, and remove weeds from common areas.",
            "Children are welcome when supervised, but sharp tools must be returned to the locked shed after use.",
            "The committee reviews membership each season to ensure unused plots can be offered to people on the waiting list.",
        ],
    ),
]


def word_count(text: str) -> int:
    return len(text.split())


def make_block(index: int) -> dict[str, object]:
    topic_id, sentences = TOPICS[index % len(TOPICS)]
    parts: list[str] = []
    cycle = 0
    while word_count(" ".join(parts)) < 505:
        for sentence in sentences:
            parts.append(sentence)
        cycle += 1
        parts.append(
            f"Benchmark paragraph {cycle} keeps the passage synthetic while preserving a document-like structure for latency testing."
        )
    words_list = " ".join(parts).split()[:505]
    text = " ".join(words_list)
    if text and text[-1] not in ".!?":
        text += "."
    words = word_count(text)
    return {
        "id": f"block-{index + 1:02d}",
        "topic": topic_id,
        "word_count": words,
        "character_count": len(text),
        "text": text,
    }


def main() -> int:
    BENCH_DIR.mkdir(parents=True, exist_ok=True)
    blocks = [make_block(i) for i in range(32)]
    payload = {
        "created_for": "vLLM 30-second SLA benchmark",
        "data_classification": "synthetic_non_private",
        "held_out_data_used": False,
        "blocks": blocks,
    }
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"path": str(OUT_PATH), "blocks": len(blocks), "min_words": min(b["word_count"] for b in blocks), "max_words": max(b["word_count"] for b in blocks)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
