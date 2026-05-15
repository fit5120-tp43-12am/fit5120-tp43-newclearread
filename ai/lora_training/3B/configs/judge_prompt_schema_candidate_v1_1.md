# Judge Prompt and Schema Candidate v1.1

Status: frozen for benchmark use after Worker 17 synthetic API smoke and central review.

Freeze note: The smoked schema id remains `judge_accessibility_v1_1_draft`
for reproducibility, even though this file is now frozen. Do not rename the
schema id without a new synthetic judge smoke.

Revision note: Worker 16 local inspection identified that `safety_gate_summary`
allowed `minor_risk`, `major_risk`, and `severe_fail`, but not
`moderate_risk`, even though lower-level severity labels include `moderate`.
This v1.1 candidate adds `moderate_risk` before any real candidate/test data
access, real model-output review, judge API smoke result, or scoring change.

Judge model selected by user: `gpt-5.4-mini`.

Benchmark unit: one pre-split source chunk and one parsed model output.

Formal scoring mode: parsed outputs only. Strict parse failures are not sent to the semantic/accessibility judge.

## Judge Input Contract

```json
{
  "judge_input_schema_version": "judge_input_v1_draft",
  "benchmark_item_id": "string",
  "run_id": "string",
  "system_id": "string",
  "source_chunk_id": "string",
  "source_chunk": "string",
  "parsed_model_output": {
    "main_idea": "string",
    "key_points": [
      "string",
      "string",
      "string",
      "string"
    ]
  },
  "strict_parse_status": "parsed_ok",
  "parser_schema_version": "string",
  "prompt_template_id": "string",
  "generation_metadata": {
    "model_or_system_label": "string",
    "decode_config_id": "string",
    "raw_output_sha256": "string"
  }
}
```

## Proposed Judge Prompt

```text
You are an evaluation judge for a dyslexia-friendly chunk-level summarization benchmark.

You will receive one pre-split source chunk and one parsed model output. The source chunk is authoritative. Evaluate the model output only against the provided source chunk. Do not use outside knowledge. Do not reward added facts, assumptions, or claims that are not supported by the source.

The evaluated model was asked to produce:
{"main_idea":"Sentence one. Sentence two.","key_points":["Point one.","Point two.","Point three.","Point four."]}

The parser has already accepted the output shape before this judge step. Do not spend the main score on JSON formatting. If the input does not say strict_parse_status is "parsed_ok", do not score it.

Evaluation priority:
1. First assess source safety. Faithfulness, factuality, meaning preservation, critical omissions, hallucinations, qualifier loss, missing restrictions, missing warnings, and harmful oversimplification are mandatory gates.
2. After the output is sufficiently source-safe, rank primarily by dyslexia-friendly accessibility. This is not a generic summarization benchmark.

Scoring direction:
- For metric scores, use integers from 0 to 5. Higher is better.
- For severity labels, use none, minor, moderate, major, or severe. Higher severity means a worse problem.
- Keep rationales concise. Do not provide hidden reasoning or chain-of-thought. Give brief evidence-based explanations only.

Safety gate guidance:
- meaning_preservation: Does the output preserve the source's intended meaning?
- factual_grounding: Are all claims supported by the source?
- critical_omission_control: Does the output avoid omitting information needed for a safe, correct understanding?
- relationship_and_qualifier_preservation: Does it preserve causes, conditions, negation, comparisons, uncertainty, restrictions, numbers, dates, warnings, and scope?
- unsupported_claim: Mark present if the output adds a claim not grounded in the source.
- harmful_oversimplification: Mark present if simplification changes meaning, removes necessary caution, or could mislead a reader.
- safety_gate_summary: Use clear_pass when there is no meaningful source-safety concern, minor_risk for small concerns, moderate_risk for middle concerns that should affect score readiness but are not major, major_risk for serious source-safety problems, and severe_fail for severe safety failures.

Accessibility ranking guidance:
- Reward plain, familiar wording when it preserves meaning.
- Preserve necessary technical terms, names, numbers, dates, restrictions, warnings, negation, and conditions. A necessary term should be kept or briefly clarified, not erased.
- Reward short, direct sentences and low syntactic load.
- Penalize overloaded sentences, stacked clauses, dense phrasing, vague wording, ambiguous references, and avoidable jargon.
- Reward scannable structure: a clear two-sentence main idea and four useful key points that are specific, non-repetitive, and easy to scan.
- Reward quick understanding of the main message.
- Reward safe conciseness: less burden for the reader without dropping critical meaning.

Avoid double-counting:
- Use safety_gates for source-safety failures.
- Use active_accessibility_score_inputs for the six weighted accessibility-first dimensions.
- Use requested_metric_trace and accessibility_risks as diagnostic support, not as extra additive score dimensions.
- Do not punish the same issue repeatedly unless it genuinely affects different dimensions. For example, one missing warning may affect critical_omission_control and source_safety_margin, but should not also be used to lower unrelated lexical clarity unless the wording itself is unclear.

Return only valid JSON matching the provided schema. Echo the input reference fields exactly. Do not include Markdown, comments, or extra keys.
```

## Proposed Judge Output JSON Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Dyslexia-Friendly Chunk Summary Judge Output v1.1 Draft",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "judge_schema_version",
    "evaluation_status",
    "input_reference",
    "safety_gates",
    "requested_metric_trace",
    "active_accessibility_score_inputs",
    "accessibility_risks",
    "overall"
  ],
  "properties": {
    "judge_schema_version": {
      "type": "string",
      "const": "judge_accessibility_v1_1_draft"
    },
    "evaluation_status": {
      "type": "string",
      "const": "scored"
    },
    "input_reference": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "benchmark_item_id",
        "run_id",
        "system_id",
        "source_chunk_id"
      ],
      "properties": {
        "benchmark_item_id": {
          "type": "string"
        },
        "run_id": {
          "type": "string"
        },
        "system_id": {
          "type": "string"
        },
        "source_chunk_id": {
          "type": "string"
        }
      }
    },
    "safety_gates": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "meaning_preservation",
        "factual_grounding",
        "critical_omission_control",
        "relationship_and_qualifier_preservation",
        "unsupported_claim",
        "harmful_oversimplification",
        "severe_safety_failure",
        "safety_gate_summary"
      ],
      "properties": {
        "meaning_preservation": {
          "$ref": "#/$defs/metric_rating"
        },
        "factual_grounding": {
          "$ref": "#/$defs/metric_rating"
        },
        "critical_omission_control": {
          "$ref": "#/$defs/metric_rating"
        },
        "relationship_and_qualifier_preservation": {
          "$ref": "#/$defs/metric_rating"
        },
        "unsupported_claim": {
          "$ref": "#/$defs/flag_rating"
        },
        "harmful_oversimplification": {
          "$ref": "#/$defs/flag_rating"
        },
        "severe_safety_failure": {
          "type": "boolean"
        },
        "safety_gate_summary": {
          "type": "string",
          "enum": [
            "clear_pass",
            "minor_risk",
            "moderate_risk",
            "major_risk",
            "severe_fail"
          ]
        }
      }
    },
    "requested_metric_trace": {
      "type": "object",
      "description": "Diagnostic trace for the requested metric groups. These fields are not separate additive score inputs.",
      "additionalProperties": false,
      "required": [
        "key_information_coverage",
        "main_message_salience",
        "accessibility_clarity",
        "necessary_term_handling",
        "structure_and_bullet_quality",
        "cognitive_load_control",
        "ambiguity_and_vagueness_control"
      ],
      "properties": {
        "key_information_coverage": {
          "$ref": "#/$defs/metric_rating"
        },
        "main_message_salience": {
          "$ref": "#/$defs/metric_rating"
        },
        "accessibility_clarity": {
          "$ref": "#/$defs/metric_rating"
        },
        "necessary_term_handling": {
          "$ref": "#/$defs/metric_rating"
        },
        "structure_and_bullet_quality": {
          "$ref": "#/$defs/metric_rating"
        },
        "cognitive_load_control": {
          "$ref": "#/$defs/metric_rating"
        },
        "ambiguity_and_vagueness_control": {
          "$ref": "#/$defs/metric_rating"
        }
      }
    },
    "active_accessibility_score_inputs": {
      "type": "object",
      "description": "Only these six fields feed the active accessibility-first score. External aggregation applies the active weights.",
      "additionalProperties": false,
      "required": [
        "plain_language_lexical_accessibility_and_term_handling",
        "sentence_and_syntax_accessibility",
        "scannable_structure_and_chunking",
        "main_message_salience_and_quick_understanding",
        "cognitive_load_reduction_and_safe_conciseness",
        "source_safety_margin"
      ],
      "properties": {
        "plain_language_lexical_accessibility_and_term_handling": {
          "$ref": "#/$defs/metric_rating"
        },
        "sentence_and_syntax_accessibility": {
          "$ref": "#/$defs/metric_rating"
        },
        "scannable_structure_and_chunking": {
          "$ref": "#/$defs/metric_rating"
        },
        "main_message_salience_and_quick_understanding": {
          "$ref": "#/$defs/metric_rating"
        },
        "cognitive_load_reduction_and_safe_conciseness": {
          "$ref": "#/$defs/metric_rating"
        },
        "source_safety_margin": {
          "$ref": "#/$defs/metric_rating"
        }
      }
    },
    "accessibility_risks": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "complex_wording",
        "overloaded_sentences",
        "poor_scannability",
        "vague_or_ambiguous_wording",
        "missing_or_blurred_constraints",
        "unnecessary_cognitive_load"
      ],
      "properties": {
        "complex_wording": {
          "$ref": "#/$defs/risk_rating"
        },
        "overloaded_sentences": {
          "$ref": "#/$defs/risk_rating"
        },
        "poor_scannability": {
          "$ref": "#/$defs/risk_rating"
        },
        "vague_or_ambiguous_wording": {
          "$ref": "#/$defs/risk_rating"
        },
        "missing_or_blurred_constraints": {
          "$ref": "#/$defs/risk_rating"
        },
        "unnecessary_cognitive_load": {
          "$ref": "#/$defs/risk_rating"
        }
      }
    },
    "overall": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "accessibility_first_recommendation",
        "score_readiness",
        "summary_rationale"
      ],
      "properties": {
        "accessibility_first_recommendation": {
          "type": "string",
          "enum": [
            "excellent",
            "good",
            "mixed",
            "weak",
            "unsafe_or_unusable"
          ]
        },
        "score_readiness": {
          "type": "string",
          "enum": [
            "usable_for_accessibility_ranking",
            "usable_with_safety_caution",
            "blocked_by_safety_gate"
          ]
        },
        "summary_rationale": {
          "type": "string",
          "maxLength": 320
        }
      }
    }
  },
  "$defs": {
    "metric_rating": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "score",
        "severity",
        "rationale"
      ],
      "properties": {
        "score": {
          "type": "integer",
          "minimum": 0,
          "maximum": 5,
          "description": "Higher is better: 5 is excellent, 0 is unacceptable or absent."
        },
        "severity": {
          "type": "string",
          "enum": [
            "none",
            "minor",
            "moderate",
            "major",
            "severe"
          ],
          "description": "Higher severity means greater problem risk."
        },
        "rationale": {
          "type": "string",
          "maxLength": 240
        }
      }
    },
    "flag_rating": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "present",
        "severity",
        "rationale"
      ],
      "properties": {
        "present": {
          "type": "boolean"
        },
        "severity": {
          "type": "string",
          "enum": [
            "none",
            "minor",
            "moderate",
            "major",
            "severe"
          ]
        },
        "rationale": {
          "type": "string",
          "maxLength": 240
        }
      }
    },
    "risk_rating": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "present",
        "severity",
        "rationale"
      ],
      "properties": {
        "present": {
          "type": "boolean"
        },
        "severity": {
          "type": "string",
          "enum": [
            "none",
            "minor",
            "moderate",
            "major",
            "severe"
          ]
        },
        "rationale": {
          "type": "string",
          "maxLength": 220
        }
      }
    }
  }
}
```

## Parse Failure Handling

Strict parse failures stay outside formal semantic/accessibility judge scoring.

Required handling:

- Preserve raw model outputs unchanged.
- Log parser failure details and raw output hash.
- Do not send parse-failed outputs to this judge prompt.
- Report parse failures as format compliance/product-readiness failures separately from the main accessibility score.
- If a raw-output triage mode is later needed, label it separately and do not mix it with formal parsed-output judging.

## Active Score Mapping

The active weighted score should use only `active_accessibility_score_inputs`:

- `plain_language_lexical_accessibility_and_term_handling`
- `sentence_and_syntax_accessibility`
- `scannable_structure_and_chunking`
- `main_message_salience_and_quick_understanding`
- `cognitive_load_reduction_and_safe_conciseness`
- `source_safety_margin`

Safety gates decide whether that score is usable. Diagnostic fields help audit the decision, but they are not extra weighted dimensions.
