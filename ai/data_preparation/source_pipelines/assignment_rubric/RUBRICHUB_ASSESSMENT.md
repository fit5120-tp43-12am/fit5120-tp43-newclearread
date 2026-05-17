# RubricHub_v1 Feasibility Assessment

## Decision

`sojuL/RubricHub_v1` is partially suitable for your task.

- `Yes` for scale, accessibility, and rubric structure.
- `Yes` for building 150 complete, understandable samples after formatting each row as `Assignment Brief + Scoring Rubric`.
- `No` if you need a corpus of real classroom or university assignment rubrics.

So the honest conclusion is:

`RubricHub_v1` is acceptable as a high-volume proxy source, but not as an authentic education-rubric dataset.

## Evidence collected

From direct Hugging Face inspection and parquet metadata:

- dataset repo: `sojuL/RubricHub_v1`
- default train rows: `364,260`
- raw files:
  - `RuRL/rurbichub_v1_Chat.parquet` -> `9,812`
  - `RuRL/rurbichub_v1_Instruction_Following.parquet` -> `95,173`
  - `RuRL/rurbichub_v1_Medical.parquet` -> `29,681`
  - `RuRL/rurbichub_v1_Science.parquet` -> `29,418`
  - `RuRL/rurbichub_v1_Writing.parquet` -> `17,444`
  - `sft_RuFT/rurbichub_v1_6samples_156k_sft_data.parquet` -> `156,538`
  - `sft_RuFT/rurbichub_v1_best_of_6samples_26k_sft_data.parquet` -> `26,194`

## Important technical caveat

Although the dataset can be called from Python, a larger scan through the default `load_dataset(...)` route hit a nested-schema mismatch inside `Instruction_Following`.

For stable extraction, this pipeline reads the raw parquet file directly with `pyarrow`.

## License

The Hugging Face card and linked GitHub repo publish the dataset under:

- `Apache-2.0`

This is a clear open license and a major advantage.

## Why it is not a perfect semantic match

The dataset is designed for LLM rubric supervision, not for educational-course archiving.

A row is usually:

- one prompt / task
- one set of auto-generated rubric criteria

This is close to `assignment requirements + scoring criteria`, but not the same as:

- official course handouts
- teacher-authored grading rubrics
- real university assignment sheets

## Why the Writing subset is the best choice inside RubricHub

The Writing subset gives the best balance of:

- assignment-like prompts
- richer rubric text
- enough medium and long samples
- fewer obviously irrelevant rule-following prompts than `Instruction_Following`

## Better semantic alternative, but harder

A more authentic education source would be open educational resources such as MIT OpenCourseWare assignment pages.

That path was not chosen as the main pipeline because:

- collection cost is much higher
- grading criteria are less consistently present
- page-level extraction and cleaning are more manual
