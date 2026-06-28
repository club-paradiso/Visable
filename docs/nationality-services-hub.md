# 국적민원·귀화면접 준비 — feature & authoring guide

Full-page hub for Korean nationality civil affairs and naturalization interview
prep. Opened from `new-home.html` ("국적민원·귀화면접 준비" card).

- **Page:** `nationality-interview-hub.html` + `assets/js/nationality-interview-hub.js`
- **Waymaker modes:** `nationality_services` (국적민원 안내 코치) and
  `naturalization_interview_prep` (귀화면접 코치) — text-first, no voice.
- **Backend:** isolated `POST /api/nationality-coach` (Groq-first → OpenRouter,
  bounded timeout, structured JSON, 503 → local-feedback fallback). The
  `/api/ask` pipeline is untouched.

## Data files

| File | Holds |
| --- | --- |
| `data/nationality_service_sources.json` | Official source registry (task schema) |
| `data/nationality_service_guides.json` | 15 nationality civil-affairs guides |
| `data/naturalization_interview_questions.json` | Practice questions (50+) |
| `data/naturalization_video_sources.json` | Reference playlists/channels (metadata-only) |
| `data/naturalization_learning_topics.json` | 8 core study topics |

> These are **separate** from `data/nationality_sources.json` etc. (which power
> the existing New Home wizards) to avoid schema collisions. Do not merge them.

## Safety rules (enforced by validators — do not bypass)

1. **No invented citations.** Only official hosts: `law.go.kr`, `immigration.go.kr`,
   `hikorea.go.kr`, `socinet.go.kr`, `kiiptest.org`, `moj.go.kr`, `gwanbo.go.kr`,
   `easylaw.go.kr`, `mojminwon.moj.go.kr`. Reuse a verified URL; never fabricate
   article numbers or deep links you have not opened.
2. **No official-past-question claims.** Every question keeps
   `is_official_past_question: false` and a 공식 기출 아님 / 연습문제 label.
   Setting it `true` requires a `source_refs` entry that is an `official_level:
   primary` source — the validator fails otherwise.
3. **YouTube: metadata only.** Never store transcripts, captions, or full lesson
   text. `transcript_stored` must be exactly `false`; no field name may contain
   `transcript`/`caption`/`script`/`body_text`; `is_official` stays `false`
   unless an explicit verified `official_source_id` marker is added.
4. **Local notices are examples, not rules.** Use `official_level: local_notice`
   and a caution that says it cannot be generalized.
5. **Short paraphrase only.** `summary_ko` must stay a short, source-aware
   paraphrase (≤ 600 chars) — never pasted page/PDF/law text.
6. **Guides always carry a `caution_ko`.** Uncertain content uses
   `source_confidence: needs_review` and surfaces as 확인 필요 in the UI.

## Validation

```bash
npm run test:nationality-services        # both validators
node scripts/check_nationality_services_data.mjs       # sources + guides (+ freshness warnings)
node scripts/check_naturalization_interview_data.mjs   # questions + videos + topics
```

Both are wired into `scripts/check_repo.sh` (step 9g) and run in CI. The
sources/guides validator also emits **non-blocking freshness warnings** when a
record's `checked_at` / `last_reviewed_at` is older than 180 days — re-verify
those against the official source and bump the date.

## Adding content

- **A source:** add to `nationality_service_sources.json` with a valid
  `source_kind` / `official_level`, an official-host `url`, `checked_at` (today),
  a short `summary_ko`, and a `caution_ko`. Then reference its `id` from guides.
- **A guide:** add to `nationality_service_guides.json` with a valid `category`,
  `typical_flow_ko` (general, not a guaranteed sequence), a cautious
  `key_documents_note_ko`, `related_laws`/`related_sources` (must resolve), a
  `caution_ko`, and honest `source_confidence`.
- **A question:** add to `naturalization_interview_questions.json` with a valid
  `category` + `difficulty`, `is_official_past_question: false`, a 공식 기출
  아님 label, and a unique `id`.
- Run the validators before committing.

## Optional: enrich video titles (no transcripts)

`scripts/import_naturalization_video_metadata.mjs` fills real playlist/channel
titles from the **official** YouTube Data API metadata endpoints
(`playlists`/`playlistItems`/`channels`/`videos`) — the captions endpoint is
never called and no transcript-like field is ever written.

```bash
npm run import:naturalization-videos          # dry-run (no key → clean no-op)
YOUTUBE_API_KEY=... npm run import:naturalization-videos -- --write
```

Without a key it is a no-op and the human-written seed (titles marked 제목
미확인) is kept.

## Out of scope (future)

- Voice (STT/TTS): explicitly excluded; the feature is text-first by design.
- Languages beyond KO/EN.
- A full admin editor UI (this doc + validators are the current safe workflow).
