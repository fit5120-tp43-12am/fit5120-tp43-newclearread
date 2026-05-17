# Label Mask Sanity Check

Date/time: 2026-04-28T14:49:20+10:00

## Scope

Verified assistant-only loss labels on the 10-record smoke set. This check loaded only the tokenizer, not full model weights.

## Inputs

- Config: `ai/lora_training/configs/smoke_llama31_8b_qlora.example.yaml`
- Model tokenizer: `unsloth/Llama-3.1-8B-Instruct-unsloth-bnb-4bit`
- Smoke data: `<external-local-raw-8b-training-workspace-not-in-git>/ai/lora_training/data/splits/smoke_test_10.jsonl`
- Smoke data SHA256: `8f51d083e8fafae143ec146c0155f85dc23a5cfdaf931a04092e7f8543d2d3a8`
- Split manifest: `<external-local-raw-8b-training-workspace-not-in-git>/ai/lora_training/data/splits/split_manifest.json`

## Result

- Overall pass: `True`
- Smoke records checked: `10`
- Records with trainable assistant tokens: `10`
- Records whose decoded trainable labels parse as JSON: `10`
- Records whose decoded trainable JSON matches source assistant JSON: `10`
- Token-prefix masks: `10`
- Offset-fallback masks: `0`
- Truncated records at configured max length: `0`
- Total masked prompt tokens: `12071`
- Total trainable assistant tokens: `1323`

## Example Label Summaries

| # | Record ID | Stable Hash | Prompt Tokens | Trainable Tokens | Mask Method | Trainable JSON OK | Decoded Trainable Preview |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | medlineplus:000227:db32be2813ba | db32be2813ba | 789 | 151 | token_prefix | True | {"main_idea":"The text explains nausea and vomiting and gives common causes, warning signs, diagnosis, and treatment. It says these symptoms are usually not serious, but some cases need urgent medical care.","key_poin... |
| 2 | medlineplus:000017:71c1ad8ed8ef | 71c1ad8ed8ef | 1202 | 136 | token_prefix | True | {"main_idea":"This text explains infectious mononucleosis, or mono. It says mono is a contagious viral illness, most often caused by Epstein-Barr virus, and people usually recover with rest and care.","key_points":["M... |
| 3 | public_service:000142:220899075124 | 220899075124 | 1051 | 159 | token_prefix | True | {"main_idea":"This text explains how to report suspected tax fraud to the IRS. It says the IRS wants serious, well-supported cases and gives the form and mailing address to use.","key_points":["The IRS has limited aud... |

## Errors

- None

## Interpretation

The prompt region contains the system and user/source text plus the assistant generation header. Labels for that region are set to `-100`, so loss is computed only on the assistant JSON completion tokens.
