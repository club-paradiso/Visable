# Paradiso AI Golden Evaluation Suite

## What This Is

The golden eval suite is a deterministic regression test for Paradiso AI's routing, detection, and fallback behavior. It does **not** call any LLM provider and does **not** assess answer quality. It evaluates the deterministic backend helper functions that run before any LLM is invoked.

This is not model training data. Questions in the golden set are artificial examples written to exercise specific code paths; they are not derived from real user queries.

## What It Evaluates

For each question in the golden set, the runner calls:

| Backend function | What it checks |
|---|---|
| `_detect_visa_codes(payload_code, visa_data, text)` | Visa code and sub-code detection |
| `_detect_task_type(text)` | Procedure type (extension, workplace_change, etc.) |
| `_risk_level_for_task(task_type)` | Risk classification (low / medium / high) |
| `_select_grounding(visa_code, task_type, sub_code)` | Whether a grounding entry is selected |

No HTTP request is made. No OpenRouter or Groq API key is needed.

## Files

| File | Purpose |
|---|---|
| `backend/data/eval/paradiso_ai_golden_questions.json` | The golden question set (45 questions) |
| `scripts/evaluate_paradiso_ai_golden_questions.py` | The eval runner |
| `backend/tests/test_paradiso_backend.py` (class `GoldenEvalSuiteTests`) | Unit tests wrapping the eval |

## Running the Eval

```bash
# Default: non-strict, human-readable output
python3 scripts/evaluate_paradiso_ai_golden_questions.py

# Strict mode: exits nonzero if any regression failure occurs
python3 scripts/evaluate_paradiso_ai_golden_questions.py --strict

# Machine-readable JSON output
python3 scripts/evaluate_paradiso_ai_golden_questions.py --json

# Combined
python3 scripts/evaluate_paradiso_ai_golden_questions.py --strict --json
```

## Modes

### Non-strict mode (default)
- Known gaps (e.g. `candidate_only` grounding status, undetected task types for known coverage holes) are **reported** but do **not** cause a nonzero exit.
- Suitable for CI steps that must not be flaky.

### Strict mode (`--strict`)
- Any regression failure (an expectation that was previously passing now fails) causes exit code 1.
- Known gaps are still only reported, not counted as failures.
- Use for pre-promotion checks or branch protection.

## Result Terminology

| Status | Meaning |
|---|---|
| `active_grounded` | `_select_grounding` returned a non-None entry; the answer will be sourced from the verified manual grounding |
| `candidate_only` | A draft candidate exists in `candidates/` but has not been promoted; `_select_grounding` returns None; falls back to scoped prompt |
| `scoped_fallback` | No grounding or candidate; the answer uses the Korea-immigration-scoped fallback prompt |
| `clarification_needed` | Sub-code or scenario required before an answer can be given safely |
| `unsupported` | Out of scope for Korean immigration guidance |

## Coverage

The 45 questions cover:

- **Active grounded paths**: D-2 extension (KO/EN), D-4-1 extension (KO), E-7 extension (KO/EN)
- **Sub-code exclusion guards**: D-4-2K extension → scoped fallback (not covered by D-4 general entry); E-7-4 extension → scoped fallback
- **Candidate-only gaps**: F-6 divorce (F-6-1, F-6-3); F-6-2 child raising; F-6 general separation
- **Academic status changes**: D-2 leave of absence (KO/EN), D-2 gap semester (EN), D-2 학적 상태 변동 (KO)
- **Scoped fallback paths**: D-10 extension, D-10-1 extension, F-2 extension, F-5 card renewal, E-7 workplace change
- **Common procedures**: address change report, passport info report, foreigner registration (known detection gap), status change, activity permission (known detection gap)
- **High-risk paths**: overstay/deadline risk, status change
- **Family status**: child birth report (KO/EN)
- **Out-of-scope**: non-Korean immigration questions

## Known Gaps Documented in the Suite

These gaps are **expected** and reported in non-strict mode without failing:

| Gap | Root cause |
|---|---|
| F-6 divorce grounding_status=candidate_only | Candidate draft exists but not promoted; `_select_grounding` returns None |
| `foreigner_registration` not detected | `_detect_task_type` has no 외국인등록 signal; `_TASK_RISK_LEVELS` lists it but it is unreachable |
| Activity permission outside status not detected | No 체류자격외활동 detection signal in `_detect_task_type` |
| Graduation/completion not detected from English text | 'graduate' is not in `academic_en` regex; '수료'/'졸업' not in `academic_ko` signals |
| F-5 card renewal ('갱신') not detected as extension | '갱신' is not in the extension Korean signals |

## How to Add a New Golden Question

1. Open `backend/data/eval/paradiso_ai_golden_questions.json`.
2. Add a new object to the `"questions"` array following the schema:

```json
{
  "id": "gq_<visa_code>_<scenario>_<lang>_<seq>",
  "language": "ko" | "en",
  "question": "The question text as a user would write it.",
  "visa_code": "D-2" | null,
  "visa_sub_code": "D-2-1" | null,
  "expected_task_type": "extension" | "academic_status_change" | ... | null,
  "expected_grounding_status": "active_grounded" | "candidate_only" | "scoped_fallback" | "clarification_needed" | "unsupported",
  "expected_risk_level": "low" | "medium" | "high",
  "expected_must_include_metadata": ["visa_code_detected:D-2", "task_type_detected:extension"],
  "expected_must_not_include_terms": [],
  "matrix_row_id": "d2_extension_general" | null,
  "notes": "Why this question, what path it tests."
}
```

3. Run the eval to verify your expectations match actual backend behavior:
   ```bash
   python3 scripts/evaluate_paradiso_ai_golden_questions.py
   ```
4. If the eval reports failures, check whether your `expected_*` fields are correct, or whether you need to update `_NULL_TASK_EXPECTED` in the runner for a known gap.
5. Do not exceed 50 questions without first archiving older ones.

### Rules for question text

- Must not contain real passport numbers, ARC numbers, phone numbers, or names.
- Must be a plausible question a Korean immigration inquiry would involve.
- Questions for English-only detection paths must use English. Questions for Korean-only signals must use Korean.
- Do not write questions that mention US, UK, Canadian, or Australian immigration as the primary subject.

## How This Connects to the Coverage Matrix

Each golden question references a `matrix_row_id` from `backend/data/eval/paradiso_coverage_matrix.json`. The coverage matrix is the source of truth for which procedures have active grounding, which have candidates, and which are scoped fallback. The golden eval runner verifies that the backend's actual routing behavior matches the matrix's declared `coverage_status`.

When a matrix row transitions from `candidate_only` → `active_grounded` (after human review and promotion), the corresponding golden questions' `expected_grounding_status` must be updated from `candidate_only` to `active_grounded` and the `expected_must_include_metadata` updated accordingly.

## What This Is Not

- Not model training data (`is_training_data: false`)
- Not an LLM quality benchmark (`is_llm_eval: false`)
- Not a replacement for human review of grounding candidates
- Not a source of legal advice
- Not a scraper or RAG system — no external websites are accessed

## Knowledge Platform eval corpus

The golden questions are also referenced by the persistent Knowledge Platform
eval corpus (tag `golden_questions_v1`, same payload semantics as this runner),
alongside the fact-level seed cases in `backend/data/knowledge/eval_corpus_seed.json`.
Those cases assert facts, buckets, sources and coverage states, not only
routing. Run them with:

```bash
python3 scripts/knowledge/knowledge_cli.py --db :memory: eval --selector all --strict
```

This runner stays in place; see `docs/ai/WAYMAKER_KNOWLEDGE_PLATFORM.md` §11.
