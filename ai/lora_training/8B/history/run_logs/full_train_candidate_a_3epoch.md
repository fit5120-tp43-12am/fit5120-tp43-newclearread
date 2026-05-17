# Full Training Candidate A 3 Epoch

Date/time: 2026-04-28T16:34:13+10:00
Stage id: `Stage 006`

## Environment

- Git repo: `<team-repo-root>`
- Git branch before run: `feature/ai-llama-lora-training`
- Git commit before run: `4c49a33aeb5c5d7816560d95e293db40c4e5f4e6`
- Python: `3.11.15`
- Platform: `Linux-6.6.87.2-microsoft-standard-WSL2-x86_64-with-glibc2.39`
- Conda env: `clearread-llama-lora`
- GPU: `NVIDIA GeForce RTX 4070 Ti SUPER`
- VRAM: `16376 MiB`
- BF16 supported: `True`

| Package | Version |
| --- | --- |
| torch | 2.10.0+cu128 |
| transformers | 5.5.0 |
| datasets | 4.3.0 |
| accelerate | 1.13.0 |
| peft | 0.19.1 |
| trl | 0.24.0 |
| bitsandbytes | 0.49.2 |
| unsloth | 2026.4.8 |
| huggingface_hub | 1.12.0 |
| safetensors | 0.7.0 |
| sentencepiece | 0.2.1 |

## Commands And Config

- Command: `python scripts/train_full_qlora.py --config ai/lora_training/configs/train_llama31_8b_qlora_candidate_a.example.yaml`
- Max sequence length: `3072`
- QLoRA: `4-bit NF4`
- LoRA r/alpha/dropout: `16 / 32 / 0.05`
- Target modules: `q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj`
- Per-device train batch size: `1`
- Gradient accumulation steps: `8`
- Effective train batch size: `8`
- Epochs: `3`
- Learning rate: `0.0002`
- Warmup ratio: `0.03`
- Optimizer: `adamw_8bit`
- Scheduler: `linear`
- Seed: `5120`
- Assistant-only loss masking: `enabled`
- Save strategy: `no`
- Validation loss: `computed once after training with trainer.evaluate(eval_dataset=validation)`

## Preflight Tokenization Gate

- Config: `ai/lora_training/configs/train_llama31_8b_qlora_candidate_a.example.yaml`
- Tokenizer model id: `unsloth/Llama-3.1-8B-Instruct-unsloth-bnb-4bit`
- Train data: `<external-local-raw-8b-training-workspace-not-in-git>/ai/lora_training/data/splits/train.jsonl`
- Validation data: `<external-local-raw-8b-training-workspace-not-in-git>/ai/lora_training/data/splits/val.jsonl`
- Split manifest: `<external-local-raw-8b-training-workspace-not-in-git>/ai/lora_training/data/splits/split_manifest.json`
- Split manifest SHA256: `42bfe9974c31e74b98b45d45daa792f8582d517541e153439b510e9a9b307f19`

| Split | Records | Expected | SHA256 | Max Input Tokens | Max Assistant Tokens | Total Assistant Tokens | Truncated | Trunc % | Non-Empty Labels | JSON OK | Matches Gold JSON |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| train | 1162 | 1162 | b99caa6b06963a05ca7e32da3c3be3237c9ea6b128ce1ccf329b78d2d56929fb | 2296 | 192 | 148979 | 0 | 0.00% | 1162 | 1162 | 1160 |
| validation | 145 | 145 | a7cf5277eda97ef1868376caa79343b040ba6920602bc607dc145a2039d2d4be | 2171 | 204 | 18677 | 0 | 0.00% | 145 | 145 | 145 |

### Train Decoded Label Samples

| # | Record ID | Stable Hash | Input Tokens | Assistant Tokens | Truncated | JSON OK | Matches Gold | Preview |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | assignment_rubric:000001:d99146f7bdb0 | d99146f7bdb0 | 1190 | 122 | False | True | True | {"main_idea":"The text asks for five easy graduation thesis topics in art design. It also sets many rules for the reply, including topic scope, format, methods, and extra advice.","key_points":["The topics must be abo... |
| 2 | assignment_rubric:000003:8705a1e329c1 | 8705a1e329c1 | 1692 | 142 | False | True | True | {"main_idea":"The source asks for a highly detailed literature review on the ethical implications of mass surveillance for data collection in contemporary society. It also gives a long rubric that requires Harvard cit... |
| 3 | assignment_rubric:000004:66d047d6a48b | 66d047d6a48b | 1479 | 136 | False | True | True | {"main_idea":"The source text gives a detailed brief and rubric for a research paper on child narrators in twenty-first-century novels. It requires a formal, analytical essay with critics, quotations, close reading, a... |
| 4 | assignment_rubric:000005:e59485009f29 | e59485009f29 | 1559 | 125 | False | True | True | {"main_idea":"This text is an assignment brief and scoring guide for a summary of a research paper. It asks for a precise academic summary on quantum computing for climate modeling with specific content and format req... |
| 5 | assignment_rubric:000006:58111e14faf0 | 58111e14faf0 | 1653 | 149 | False | True | True | {"main_idea":"The text is an assignment brief and scoring rubric for a research paper on machine learning algorithms. It says the paper must be a formal survey with standard sections, citations, equations, and broad c... |

### Validation Decoded Label Samples

| # | Record ID | Stable Hash | Input Tokens | Assistant Tokens | Truncated | JSON OK | Matches Gold | Preview |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | assignment_rubric:000002:f6d33a3c7474 | f6d33a3c7474 | 1450 | 118 | False | True | True | {"main_idea":"The source asks for a literature review on multimedia resources in mobile-assisted language learning. It also gives a rubric with many required sections, citations, theories, studies, and format rules.",... |
| 2 | assignment_rubric:000025:7c7863351ba9 | 7c7863351ba9 | 2075 | 138 | False | True | True | {"main_idea":"The text asks for a research-paper introduction on cloud cybersecurity in multi-tenant cloud environments. It says the introduction should explain current defenses, their limits, and then present a new s... |
| 3 | assignment_rubric:000029:52832807838c | 52832807838c | 1658 | 147 | False | True | True | {"main_idea":"This text asks for a scholarly section on the theoretical and practical significance of a blockchain trust mechanism for collaborative product design in cloud manufacturing. It requires a clear academic ... |
| 4 | assignment_rubric:000030:978cad9acf6d | 978cad9acf6d | 2171 | 130 | False | True | True | {"main_idea":"The text gives a detailed assignment brief for a methodology section in a research paper. It asks for a VR healthcare training system with physical device integration and real-time data synchronization."... |
| 5 | assignment_rubric:000032:c5725ec3598d | c5725ec3598d | 1859 | 123 | False | True | True | {"main_idea":"The source text gives an assignment brief for a long critical essay on the child narrator in *The Catcher in the Rye*. It also gives strict scoring rules for thesis, quotations, criticism, structure, sty... |

### Truncation Detail

- Train truncated by domain: `{}`
- Train truncated by length bucket: `{}`
- Validation truncated by domain: `{}`
- Validation truncated by length bucket: `{}`

### Gate Result

- Gate passed: `True`
- Blockers:
- None

## Training Result

- Status: `success`
- Model id actually used: `unsloth/Llama-3.1-8B-Instruct-unsloth-bnb-4bit`
- Start time: `2026-04-28T15:29:34+10:00`
- End time: `2026-04-28T16:34:13+10:00`
- Elapsed runtime: `1h 04m 39s` (3879.21 seconds)
- Output/checkpoint path: `ai/lora_training/outputs/full/candidate_a_3epoch`
- Adapter output path: `<external-local-raw-8b-training-workspace-not-in-git>/ai/lora_training/models/adapters/full_candidate_a_3epoch`
- OOM: `no`
- Final train loss: `0.4797596574748216`
- Validation loss: `0.9654271602630615`
- Average seconds per step at final progress sample: `8.68`

### Progress Samples

| Step | Total | Elapsed | Avg Sec/Step | Remaining | ETA |
| --- | --- | --- | --- | --- | --- |
| 370 | 438 | 53m 52s | 8.735 | 9m 54s | 2026-04-28T16:33:20+10:00 |
| 375 | 438 | 54m 34s | 8.73 | 9m 10s | 2026-04-28T16:33:18+10:00 |
| 380 | 438 | 55m 17s | 8.728 | 8m 26s | 2026-04-28T16:33:17+10:00 |
| 385 | 438 | 56m 01s | 8.73 | 7m 43s | 2026-04-28T16:33:18+10:00 |
| 390 | 438 | 56m 45s | 8.73 | 6m 59s | 2026-04-28T16:33:18+10:00 |
| 395 | 438 | 57m 28s | 8.728 | 6m 15s | 2026-04-28T16:33:17+10:00 |
| 400 | 438 | 58m 10s | 8.726 | 5m 32s | 2026-04-28T16:33:16+10:00 |
| 405 | 438 | 58m 51s | 8.718 | 4m 48s | 2026-04-28T16:33:13+10:00 |
| 410 | 438 | 59m 35s | 8.719 | 4m 04s | 2026-04-28T16:33:14+10:00 |
| 415 | 438 | 1h 00m 15s | 8.712 | 3m 20s | 2026-04-28T16:33:10+10:00 |
| 420 | 438 | 1h 00m 56s | 8.705 | 2m 37s | 2026-04-28T16:33:07+10:00 |
| 425 | 438 | 1h 01m 40s | 8.705 | 1m 53s | 2026-04-28T16:33:07+10:00 |
| 430 | 438 | 1h 02m 22s | 8.702 | 1m 10s | 2026-04-28T16:33:06+10:00 |
| 435 | 438 | 1h 03m 04s | 8.699 | 26s | 2026-04-28T16:33:05+10:00 |
| 438 | 438 | 1h 03m 22s | 8.68 | 0s | 2026-04-28T16:32:56+10:00 |

### Train Loss Trend

| Step | Epoch | Loss | Learning Rate |
| --- | --- | --- | --- |
| 1 | 0.0068846815834767644 | 1.5431715250015259 | 0.0 |
| 2 | 0.013769363166953529 | 1.4505820274353027 | 1.4285714285714285e-05 |
| 3 | 0.020654044750430294 | 1.3696339130401611 | 2.857142857142857e-05 |
| ... | ... | ... | ... |
| 431 | 2.9569707401032703 | 0.2017316222190857 | 3.7735849056603773e-06 |
| 432 | 2.963855421686747 | 0.1332225501537323 | 3.30188679245283e-06 |
| 433 | 2.9707401032702236 | 0.19447225332260132 | 2.830188679245283e-06 |
| 434 | 2.9776247848537007 | 0.13396136462688446 | 2.358490566037736e-06 |
| 435 | 2.9845094664371774 | 0.16427463293075562 | 1.8867924528301887e-06 |
| 436 | 2.991394148020654 | 0.1645248383283615 | 1.4150943396226415e-06 |
| 437 | 2.9982788296041307 | 0.14567911624908447 | 9.433962264150943e-07 |
| 438 | 3.0 | 0.11370232701301575 | 4.7169811320754717e-07 |

### Trainer Metrics

```json
{
  "train": {
    "epoch": 3.0,
    "total_flos": 2.0788855374230323e+17,
    "train_loss": 0.4797596574748216,
    "train_runtime": 3801.7851,
    "train_samples_per_second": 0.917,
    "train_steps_per_second": 0.115
  },
  "validation": {
    "epoch": 3.0,
    "eval_loss": 0.9654271602630615,
    "eval_runtime": 75.1215,
    "eval_samples_per_second": 1.93,
    "eval_steps_per_second": 0.253
  }
}
```

### Adapter Files

| File | Size bytes | SHA256 |
| --- | --- | --- |
| README.md | 5256 | 1dadff2f9ed0be94f4d1253ae61de95da79f7edea3d641fc157b9270b2c62612 |
| adapter_config.json | 1262 | e18a24897876cbeea6453292e0027a728bd85b700cd0c05a9aa29c02414c50f1 |
| adapter_model.safetensors | 167832240 | not recorded (large local artifact) |
| chat_template.jinja | 4614 | e10ca381b1ccc5cf9db52e371f3b6651576caee0a630b452e2816b2d404d4b65 |
| tokenizer.json | 17209920 | not recorded (large local artifact) |
| tokenizer_config.json | 50669 | 52a57d911c30cf2b645e3350aafd9f1c424d2529483fd4628e7e34bfb33a7fe2 |

### ETA Accuracy Note

The ETA callback used average observed seconds per completed optimizer step. Early estimates included warmup/cache effects and stabilized after several progress samples.

## Validation Inference

Command run after training:

`python scripts/run_inference_check.py --config configs/train_llama31_8b_qlora_candidate_a.example.yaml --adapter-path <external-local-raw-8b-training-workspace-not-in-git>/models/adapters/full_candidate_a_3epoch --data-path <external-local-raw-8b-training-workspace-not-in-git>/data/splits/val.jsonl --num-examples 10`

## Decision

- Candidate A training completed without OOM. Validation inference sanity check results are appended below.

## Inference Sanity Check

Date/time: 2026-04-28T16:36:25+10:00
Adapter path: `<external-local-raw-8b-training-workspace-not-in-git>/ai/lora_training/models/adapters/full_candidate_a_3epoch`
Data path: `<external-local-raw-8b-training-workspace-not-in-git>/ai/lora_training/data/splits/val.jsonl`
Examples checked: `10`
Schema pass count: `10`

| # | Schema OK | Reason | Output Preview |
| --- | --- | --- | --- |
| 1 | True | ok | {"main_idea":"The text is an assignment brief for a literature review on multimedia resources in mobile-assisted language learning. It also gives a long grading |
| 2 | True | ok | {"main_idea":"The text is an assignment brief for a research paper introduction on cloud cybersecurity. It asks for a formal paper that explains cloud security  |
| 3 | True | ok | {"main_idea":"The text is an assignment brief for a research paper section on the theoretical and practical significance of a blockchain-based trust mechanism f |
| 4 | True | ok | {"main_idea":"The text is an assignment brief for a research paper methodology section. It asks for a technical description of a VR training system for smart he |
| 5 | True | ok | {"main_idea":"The source text is an assignment brief for a long critical essay about the child narrator in *The Catcher in the Rye*. It gives detailed grading r |
| 6 | True | ok | {"main_idea":"The source text is an assignment brief for a long critical essay on the opening of *The Catcher in the Rye*. It asks for a focused, theory-based a |
| 7 | True | ok | {"main_idea":"The source text is an essay assignment about Japanese gardens and Bashō’s poetry. It asks for a long, philosophical essay with labeled sections, B |
| 8 | True | ok | {"main_idea":"The source text is an assignment brief for a critical essay on Haushofer’s geopolitics of empire. It also gives a detailed rubric that sets many r |
| 9 | True | ok | {"main_idea":"The text explains how Python variables work in different scopes. It also shows how global and nonlocal rules control access to variables, and how  |
| 10 | True | ok | {"main_idea":"The text explains how Python exceptions work. It shows how to raise, catch, and handle errors, and also how exceptions can be used for more than j |

## Inference Sanity Check

Date/time: 2026-04-28T17:07:39+10:00
Adapter path: `<external-local-raw-8b-training-workspace-not-in-git>/ai/lora_training/models/adapters/full_candidate_a_3epoch`
Data path: `<external-local-raw-8b-training-workspace-not-in-git>/ai/lora_training/data/splits/val.jsonl`
Examples checked: `5`
Schema pass count: `5`

| # | Schema OK | Reason | Output Preview |
| --- | --- | --- | --- |
| 1 | True | ok | {"main_idea":"The text is an assignment brief for a literature review on multimedia resources in mobile-assisted language learning. It also gives a long grading |
| 2 | True | ok | {"main_idea":"The text is an assignment brief for a research paper introduction on cloud cybersecurity. It asks for a formal paper that explains cloud security  |
| 3 | True | ok | {"main_idea":"The text is an assignment brief for a research paper section on the theoretical and practical significance of a blockchain-based trust mechanism f |
| 4 | True | ok | {"main_idea":"The text is an assignment brief for a research paper methodology section. It asks for a technical description of a VR training system for smart he |
| 5 | True | ok | {"main_idea":"The source text is an assignment brief for a long critical essay about the child narrator in *The Catcher in the Rye*. It gives detailed grading r |
