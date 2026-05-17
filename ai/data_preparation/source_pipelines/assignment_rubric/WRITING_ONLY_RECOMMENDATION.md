# Writing-Only Recommended Baseline

This file documents the cleaner fallback baseline built from the `RuRL/rurbichub_v1_Writing.parquet` subset only.

## Why this exists

The original 150-row `assignment_rubric` sample file contained many rows that were:

- not fully English,
- outside the target scope of student assignment requirements plus grading rubrics,
- or mixed with translation / coding / SEO / editing / prompt-engineering style tasks.

A mixed-source repair was attempted, but the non-Writing subsets still introduced many pseudo-academic question-answer and instruction-following artifacts.

## Recommended fallback

Use the following file as the safer base dataset candidate:

- `assignment_rubric_150_samples_writing_only.jsonl`

Its advantages:

- all samples come from the same RubricHub Writing subset,
- structural validation passes,
- English purity and task coherence are materially better than the mixed-source repair,
- it avoids most of the obvious translation / coding / medical-advice / prompt-injection noise.

## Important tradeoff

The length distribution is much more long-heavy than the original target:

- short: 1
- medium: 23
- long: 126

This happened because the stricter English-only / assignment-rubric coherence filters removed many short and medium rows that were low quality.

## Recommendation

If quality is the top priority before SFT generation, prefer the writing-only file over the mixed-source repaired file.
