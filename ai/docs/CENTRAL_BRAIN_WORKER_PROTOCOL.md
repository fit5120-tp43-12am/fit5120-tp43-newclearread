# Central Brain And Worker Chat Protocol

Last updated: 2026-04-28

## Purpose

This training project is managed by a central-brain chat and executed through separate worker chats.

The central-brain chat is responsible for planning, decision-making, task boundaries, reviewing worker results, and deciding whether the project can move to the next phase.

Worker chats are responsible for executing one clearly bounded work order at a time.

## Central-Brain Responsibilities

- Read `TRAINING_MEMORY.md` at the start of each turn.
- Keep `TRAINING_MEMORY.md` updated at the end of each turn when decisions, files, results, or next steps change.
- Decide the next meaningful work unit.
- Write a complete worker task file under `training/work_orders/`.
- Define clear scope, read-only paths, writable paths, expected outputs, validation commands, and acceptance criteria.
- Review each worker chat's returned summary, changed files, logs, and verification results.
- Treat worker-written memory updates as provisional until central-brain review is complete.
- Promote only central-verified facts into the approved memory narrative.
- Decide one of:
  - pass and move to the next worker task,
  - request fixes in the same worker task,
  - reject and create a revised worker task.

## Worker Chat Responsibilities

- Read `TRAINING_MEMORY.md` first.
- Read its assigned work order file.
- Execute only the assigned task.
- Do not modify read-only datasets or unrelated files.
- Do not go beyond the work order's scope without asking.
- Create or modify only the files listed in the work order, unless a small supporting file is explicitly justified.
- Run the validation steps requested in the work order.
- If a work order asks the worker to update `TRAINING_MEMORY.md`, the worker must write only a clearly labeled provisional section, such as `Worker XXX reported, pending central-brain review`.
- A worker must not rewrite, delete, or reinterpret central-brain decisions, historical approved facts, pass/fail judgments, or future-worker approval status.
- Worker conclusions are evidence, not authority. The central-brain chat makes the final pass/fail decision after independent review.
- Return a concise final report with:
  - files created or changed,
  - commands run,
  - verification results,
  - blockers or deviations,
  - suggested next step.

## Memory Quarantine Rules

To prevent worker output from polluting central-brain judgment:

- `TRAINING_MEMORY.md` is the project memory, but not every line has equal authority.
- Sections explicitly marked `central-brain review`, `central-brain verification`, `passed`, or `approved` are authoritative after the central-brain chat writes them.
- Sections written by workers before review are provisional and must be treated as unverified reports.
- The central-brain chat should independently verify important worker claims using local files, hashes, counts, Git status, and logs before passing the worker.
- If a worker's memory update conflicts with local evidence or central-brain judgment, local evidence and central-brain review win.
- Future work orders should prefer worker logs and reports for detailed claims, with `TRAINING_MEMORY.md` receiving concise provisional summaries only.

## Task Granularity

Do not split work into tiny tasks when they are naturally part of the same step.

Good worker tasks are meaningful chunks, such as:

- create and validate stratified train/val/test splits,
- set up and verify the clean WSL training environment,
- implement smoke-test training scripts and configs,
- run smoke test and produce the smoke-test log,
- implement evaluation scripts,
- run final evaluation and produce the report.

A worker task may contain several small substeps when they belong to the same larger phase.

## Work Order File Convention

Worker task files should live under:

```text
C:\Users\Aufb\Desktop\fit5120\iteration1\training\work_orders
```

Use names like:

```text
001_create_data_splits.md
002_setup_wsl_environment.md
003_llama_smoke_test.md
```

Each work order should include:

- task title and purpose,
- required files to read,
- read-only paths,
- writable paths,
- exact steps,
- expected outputs,
- validation commands,
- acceptance criteria,
- final report template.
