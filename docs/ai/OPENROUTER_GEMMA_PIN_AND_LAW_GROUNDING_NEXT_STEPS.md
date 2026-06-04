# OpenRouter Gemma pin and law grounding next steps

## Purpose

This note records the next safe AI-quality steps after the backend emergency restore in PR #205.

The immediate production problem was not only answer quality. The backend had to be restored first so Railway could deploy successfully. After that, Paradiso AI should stop using `openrouter/auto` and use a deterministic model configured by the backend environment.

## Current model pin

Use this Railway variable:

```text
OPENROUTER_MODEL=qwen/qwen3-next-80b-a3b-instruct:free
```

Also leave Groq unset unless intentionally testing it:

```text
GROQ_API_KEY=
```

The current backend already prefers OpenRouter when `OPENROUTER_API_KEY` is configured. If both OpenRouter and Groq keys are configured, OpenRouter is selected first. Therefore, leaving `GROQ_API_KEY` empty is the practical fallback-off setting until a follow-up code PR adds an explicit `ALLOW_GROQ_FALLBACK=false` gate.

## Manual Railway check after deploy

After merging the model-pin PR and setting Railway variables, retest the same user-visible question:

```text
G-1-5 비자로 제주에 입국한지 2달차인데, 일본을 갈 수 있나요?
```

Expected UI-level behavior:

- Provider still shows OpenRouter.
- Model should no longer show `openrouter/auto`.
- Model should show or resolve to `qwen/qwen3-next-80b-a3b-instruct:free`; Gemma remains a fallback candidate.
- The answer may still be ungrounded until law/manual grounding is expanded.

## Known limitation

Pinning the model does not itself make the answer legally stronger. It only removes model-router variability. For G-1-5 travel/re-entry questions, answer quality still depends on better law/manual grounding.

## Next PR: law grounding expansion

Recommended branch:

```text
feat/expand-law-grounding-stay-risk-questions
```

Recommended scope:

1. Expand `backend/services/law_grounding.py` trigger patterns beyond explicit legal-basis wording.
2. Add stay-risk and travel/re-entry triggers:
   - Korean: 출국, 해외여행, 재입국, 일본, 외국인등록, 외국인등록증, 체류기간, 체류자격, 불법체류, G-1, G-1-5, 난민, 인도적 체류
   - English: re-entry, leave Korea, travel abroad, Japan, foreigner registration, alien registration, ARC, overstay, G-1
3. Build compact legal search queries instead of sending only raw user text.
4. For G-1 / Japan / re-entry style questions, include query terms such as:
   - 출입국관리법 재입국허가 체류자격 G-1
   - 출입국관리법 시행령 G-1 기타 난민 인도적 체류
   - 출입국관리법 출국 재입국 체류자격
5. Inject compact law result fields into the answer prompt when available:
   - law title/name
   - article/article number
   - article title
   - short excerpt or summary
   - source URL if present
6. Keep safety constraints:
   - Do not invent legal conclusions.
   - Do not assert that G-1-5 holders can or cannot travel to Japan unless retrieved official law/manual grounding supports it.
   - Do not change `visa_data.json` in this PR.
   - Do not present law grounding as final immigration-office determination.

## Recommended tests for the law-grounding PR

```bash
python3 -m py_compile backend/paradiso_backend.py backend/services/law_grounding.py backend/services/korean_law_client.py
python3 -m pytest backend/tests/test_paradiso_backend.py
python3 scripts/evaluate_paradiso_ai_golden_questions.py --strict
git diff --check
```

Add tests for:

- G-1-5 + 일본/재입국 question triggers a law-grounding attempt.
- G-1-5 travel/re-entry fallback does not assert definitive permission or departure consequences without grounding.
- Existing explicit legal-basis triggers still work.
