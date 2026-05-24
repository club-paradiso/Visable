# HiKorea & Immigration Source — JSON Schema Proposal

**Date:** 2026-05-24
**Branch:** `audit/hikorea-source-map`
**Companion to:** `docs/data/HIKOREA_SOURCE_MAP_AUDIT.md`
**Scope:** Schema definitions only. No runtime code, no enabled fetcher. Reference for the upcoming PR-B (`data/hikorea-source-catalog-v1`).

---

## 0. Purpose

This document defines two JSON record shapes Paradiso will adopt when it begins cataloguing public HiKorea and Korea Immigration Service surfaces:

1. **Source record** — describes a public page or downloadable artifact we know about (regardless of whether we ever fetch it). Lives in a new `data/sources/hikorea_source_catalog.json` (PR-B).
2. **Topic card** — describes an extracted, human-reviewed, citable unit of information derived from one or more source records. Lives in a future `data/topics/` directory (later PRs).

These coexist with — and do not replace — the existing `data/source_registry.json` allow-list. The source registry remains the single allow-list read by `scripts/check_source_updates.py`. The new catalog is a richer descriptive index; entries can be promoted into `source_registry.json` after operator confirmation.

The schema is presented as annotated JSON (not formal JSON Schema) for readability. A `schemas/hikorea_source_catalog.schema.json` JSON Schema file can be added in PR-B without changing field semantics.

---

## 1. Conventions

- `snake_case` field names, matching `source_registry.json`.
- All timestamps are ISO 8601 UTC (`YYYY-MM-DDTHH:MM:SSZ`).
- All hashes are prefixed with the algorithm (`sha256:`).
- `null` is used for "unknown / not applicable"; missing keys are not allowed for required fields.
- `needs_review: true` is the default until operator-verified.
- Language codes are BCP-47 short forms used elsewhere in Paradiso (`ko`, `en`, `zh`, `vi`, `ja`).
- Tier values mirror `HIKOREA_SOURCE_MAP_AUDIT.md` §1 (`T1`…`T8`).
- `host` values use the bare hostname (`hikorea.go.kr`, `immigration.go.kr`, `socinet.go.kr`, `visa.go.kr`, `law.go.kr`, `1345.go.kr`).

---

## 2. Source record schema

A source record describes a single public surface Paradiso knows about. It is **descriptive metadata**, not extracted content. A record exists even when its `status` is `not_configured` (i.e., not yet operator-verified).

```jsonc
{
  // Required identity
  "id": "hikorea_notice_index",            // stable snake_case id, unique within the catalog
  "schema_version": "1.0",                 // schema version this record conforms to
  "tier": "T3",                            // T1..T8 from the audit
  "category": "notice_index",              // see §2.1 enum
  "host": "hikorea.go.kr",
  "url": "https://www.hikorea.go.kr/...",  // public landing URL (operator-verified); null if not yet known
  "title_ko": "공지사항",
  "title_en": "Notices",

  // Authority / provenance
  "authority": "법무부 출입국·외국인정책본부",
  "authority_en": "Ministry of Justice — Korea Immigration Service",
  "language": ["ko"],                      // primary languages the page publishes in
  "kogl_type": null,                       // 1|2|3|4|"unknown" — reuse license
  "robots_allowed": null,                  // true|false|"unknown" — set after operator robots.txt check

  // Retrieval posture (no fetcher implied by these fields)
  "status": "not_configured",              // "not_configured" | "active" | "deprecated" | "blocked"
  "ingest_mode": "link_only",              // "link_only" | "metadata_mirror" | "content_extract" | "monitor_only"
  "scrape_allowed": false,                 // default false; only true after operator + ToS check
  "update_frequency": "daily",             // "on_amendment"|"daily"|"weekly"|"monthly"|"irregular"|"unknown"
  "monitor": {
    "enabled": false,                      // monitor never enabled by default
    "method": "if_modified_since",         // "if_modified_since"|"etag"|"hash_diff"|"none"
    "selector_hint": null                  // optional CSS/JSON path hint; null if not configured
  },

  // Content fingerprinting (set by monitor; null until first verified retrieval)
  "last_checked_at": null,
  "last_seen_hash": null,                  // e.g. "sha256:..."
  "last_seen_etag": null,
  "last_seen_modified": null,

  // Cross-references
  "topic_ids": [],                         // ids of topic cards derived from this source
  "supersedes": [],                        // older source ids this one replaces
  "related_law_ids": [],                   // optional law ids (e.g. "출입국관리법", with article anchors)

  // Risk + review
  "risk_level": "medium",                  // "low"|"medium"|"high" — from audit §8
  "legal_review_required": false,          // true for refugee/nationality/etc. categories
  "needs_review": true,                    // true until operator verifies record

  // Free-form
  "notes": "Placeholder. Confirm exact notice index URL before enabling monitor."
}
```

### 2.1 `category` enum

The category field bins records by what kind of surface they are. Multiple records of the same category are fine.

| `category` | Description | Typical tier |
|---|---|---|
| `statute` | Statute, decree, rule, ministerial notice | T1 |
| `manual` | Authority-published manual (PDF/HWP) | T2 |
| `notice_index` | Index page of dated notices/press releases | T3 |
| `notice_item` | Single dated notice or press release | T3 |
| `guide_page` | Persistent guide / how-to page | T4 |
| `directory` | Office, center, or institution directory | T4 |
| `form_catalog` | Index of petition forms | T4 |
| `form_artifact` | A single downloadable form (PDF/HWP) | T4 |
| `service_portal` | Live transactional/lookup surface (link-only) | T5 |
| `policy_page` | Policy-level explanation (often immigration.go.kr) | T4 |
| `adjacent_official` | Cross-government reference (Soci-Net, Visa Portal, 1345, gov.kr, data.go.kr) | T6 |
| `faq` | FAQ list | T4 |
| `sitemap` | Site map / navigation helper (for crawl planning only) | T4 |

### 2.2 Required vs optional fields

Required: `id`, `schema_version`, `tier`, `category`, `host`, `title_ko`, `authority`, `status`, `ingest_mode`, `scrape_allowed`, `risk_level`, `needs_review`.

`url` is required when `status != "not_configured"`. While `status="not_configured"`, `url` may be `null` (placeholder record).

`monitor.enabled` MUST be `false` whenever `status != "active"` or `scrape_allowed=false` — validation should enforce this.

### 2.3 Relationship to `data/source_registry.json`

`source_registry.json` is the existing allow-list consumed by `scripts/check_source_updates.py`. It is intentionally minimal. Going forward:

- The richer catalog (`data/sources/hikorea_source_catalog.json`, added in PR-B) describes every source we want to track.
- Only a vetted subset is mirrored into `data/source_registry.json` with `status="active"` for actual monitoring.
- A field `registry_id` (optional) may link a catalog record to its registry counterpart, e.g. `"registry_id": "hikorea_notice_placeholder"`.
- Promotion from catalog to registry is always a separate human-reviewed PR.

---

## 3. Topic card schema

A topic card is a curated, citable unit of information presented to users (or used as grounding context). It is derived from one or more source records and always carries verifiable provenance.

```jsonc
{
  // Identity
  "id": "topic.reporting.change_of_residence",
  "schema_version": "1.0",
  "topic_type": "reporting_obligation",     // see §3.1 enum
  "title_ko": "체류지 변경신고",
  "title_en": "Notification of change of residence",

  // Summary content — informational, no advice framing
  "summary_ko": "외국인등록을 마친 사람이 체류지를 옮긴 경우 신고해야 하는 절차에 대한 안내.",
  "summary_en": "Guidance on the notification procedure when a registered foreigner changes their place of stay.",
  "details_ko": null,                        // optional longer body; markdown allowed
  "details_en": null,

  // Provenance — at least one source_ref required
  "source_refs": [
    {
      "source_id": "hikorea_guide_change_of_residence",
      "url": "https://www.hikorea.go.kr/...",
      "retrieved_at": "2026-05-24T00:00:00Z",
      "page_title": "체류지 변경신고",
      "language": "ko",
      "tier": "T4",
      "content_hash": "sha256:..."          // hash of the extracted snippet, not the whole page
    },
    {
      "source_id": "statute_immigration_control_act_art36",
      "url": "https://www.law.go.kr/...",
      "retrieved_at": "2026-05-24T00:00:00Z",
      "page_title": "출입국관리법 제36조",
      "language": "ko",
      "tier": "T1",
      "content_hash": "sha256:..."
    }
  ],

  // Cross-links
  "related_visa_codes": ["F-2", "F-5", "F-6", "D-2", "D-4", "E-7"],   // optional
  "related_procedures": ["registration", "extension"],                  // optional
  "related_forms": ["form_change_of_residence"],                        // catalog ids
  "external_links": [
    {
      "label_ko": "전자민원 바로가기",
      "label_en": "Go to e-Application",
      "url": "https://www.hikorea.go.kr/...",
      "kind": "service_portal",
      "leaves_paradiso": true
    }
  ],

  // Editorial state
  "language_coverage": ["ko", "en"],
  "risk_level": "medium",
  "legal_review_required": false,
  "review_state": "candidate",               // "candidate" | "in_review" | "published" | "deprecated"
  "reviewed_by": null,                       // free-form (operator id or "external attorney"); null until reviewed
  "reviewed_at": null,
  "needs_review": true,

  // Conflict tracking
  "conflicts": [],                           // array of {with_source_id, summary, detected_at}
  "supersedes": [],                          // older topic ids

  // Lifecycle
  "created_at": "2026-05-24T00:00:00Z",
  "updated_at": "2026-05-24T00:00:00Z",
  "disclaimer_required": true,               // always true for now
  "notes": "Initial draft; pending manual page anchor in 2026.5 stay manual."
}
```

### 3.1 `topic_type` enum

| `topic_type` | Description |
|---|---|
| `visa_overview` | Cross-reference summary of a visa code (does not replace `visa_data.json`) |
| `procedure` | A specific procedure (extension, change, registration, etc.) |
| `reporting_obligation` | A required report/notification under the Immigration Control Act |
| `certificate` | An immigration certificate type and where to obtain it |
| `nationality` | Naturalization / renunciation / recovery / dual nationality |
| `overseas_korean` | F-4 / 재외동포 specifics |
| `refugee` | Refugee status / humanitarian status / appeal (legal review required) |
| `social_integration` | KIIP and related programs |
| `seasonal_worker` | E-8 program info |
| `office_directory` | An immigration office card (name/address/phone/hours/jurisdiction notes) |
| `form` | A petition form (metadata only) |
| `notice_summary` | A summary of a dated notice (human-reviewed) |
| `policy_overview` | Policy-level explanatory card |
| `contact_resource` | 1345, foreigner support centers, multilingual help |

### 3.2 Conflict and `needs_review` rules

- A topic card with `source_refs` from different tiers where T1 and T4 disagree MUST record an entry in `conflicts` and set `needs_review: true`.
- `review_state` can be `published` only when:
  - `needs_review == false`,
  - at least one `source_ref` is tier T1 or T2, OR `legal_review_required == false` AND the topic type permits T4-only sourcing,
  - `reviewed_by` and `reviewed_at` are populated,
  - all referenced source records exist in the catalog.
- A monitor-detected change to any underlying source MUST flip `needs_review` back to `true` and create a `conflicts[]` entry if the page content hash changed since the last successful review.

### 3.3 Disclaimer continuity

`disclaimer_required` is `true` for every topic card in the foreseeable future. Renderers must show the existing Paradiso disclaimer near content derived from any topic card. Topic cards must never carry advice-framed language (`"you should…"`, `"we recommend…"`). The audit (§9) restates this.

---

## 4. Content hash strategy

A consistent hash strategy is needed both for source-level change detection and for topic-level provenance.

### 4.1 Source-level hash (page-level)

For monitoring source records:

1. Fetch only when `monitor.enabled == true` and `scrape_allowed == true` (never by default).
2. Normalize: strip volatile fragments — server-side timestamps in footers, CSRF tokens, session ids, ad/promo banners, dynamic visitor counters — using a per-source `selector_hint` or a small allow-list of meaningful selectors.
3. Compute `sha256` over the normalized UTF-8 byte stream.
4. Store as `last_seen_hash = "sha256:" + hex`.
5. Prefer HTTP `ETag` / `Last-Modified` when present; only compute the body hash when those headers indicate a change or are absent.
6. PDF/HWP downloads hash the raw file (no normalization needed); store file size alongside.

### 4.2 Topic-level hash (snippet-level)

For each `source_refs[].content_hash`:

1. Hash only the snippet/section that backs the topic card, not the whole page.
2. Normalize whitespace (collapse runs to a single space; trim).
3. Use `sha256:` prefix.
4. On any change, the topic flips to `needs_review: true` (see §3.2).

This keeps topic cards stable against unrelated edits elsewhere on the page (e.g., menu reordering) while still catching meaningful content drift.

### 4.3 Why two levels

The page-level hash answers "did this page change at all?" (input to the monitor). The snippet-level hash answers "did the part that backs *this* topic change?" (input to the review queue). Both are needed; collapsing them produces false positives at one end and false negatives at the other.

---

## 5. Validation rules (for CI in PR-B)

A future `scripts/validate_hikorea_source_catalog.py` (added in PR-B, not in this PR) should enforce:

1. JSON parses, every record has all required fields from §2.2.
2. `id` is unique across the catalog.
3. `tier` is one of `T1..T8`; `category` is in the §2.1 enum.
4. `host` matches the host of `url` when `url` is non-null.
5. `monitor.enabled == false` whenever `status != "active"` or `scrape_allowed == false`.
6. `scrape_allowed == false` whenever `ingest_mode == "link_only"`.
7. `legal_review_required == true` implies `risk_level == "high"`.
8. Cross-references in `supersedes`, `topic_ids`, `registry_id` resolve to existing ids.
9. Every entry has either a non-null `url` or `status == "not_configured"`.
10. No record references a host outside the host allow-list (§1 hosts + any explicitly approved adjacent official host).

For topic cards (when introduced):

11. At least one `source_refs` entry.
12. `review_state == "published"` requires `needs_review == false`, populated `reviewed_by`/`reviewed_at`, and at least one T1/T2 reference unless the topic type is on the T4-permitted list.
13. `conflicts` non-empty implies `needs_review == true`.
14. No advice-framed verbs in `summary_*` / `details_*` (regex check: ko `반드시 ~하세요|~해야 합니다(?! .*(법|규정))`, en `you should|you must|we recommend`). This is a heuristic and produces warnings, not failures.

---

## 6. Storage location proposal

| Path | Purpose | PR |
|---|---|---|
| `data/source_registry.json` | Existing allow-list for monitor script | unchanged |
| `data/sources/hikorea_source_catalog.json` | New: catalog of every known source (descriptive) | PR-B |
| `data/sources/hikorea_source_catalog.example.json` | This audit: illustrative skeleton | **This PR** |
| `data/topics/` | New directory for topic cards (one JSON per topic or per category bundle) | later PR |
| `schemas/hikorea_source_catalog.schema.json` | Optional JSON Schema for CI validation | PR-B |
| `scripts/validate_hikorea_source_catalog.py` | Validator following §5 rules | PR-B |

The example file added in this PR (`hikorea_source_catalog.example.json`) is named with `.example.` to make clear it is not loaded by any runtime path and is not subject to validation as production data. It exists only to demonstrate the proposed shape.

---

## 7. Migration & compatibility notes

- No existing field on `visa_data.json`, `doc_master.json`, `data/source_registry.json`, or `data/jobcode_master.json` is renamed, removed, or repurposed.
- Topic cards are additive. UI consumption is gated by a future PR-K (UI source attribution affordance) and does not change current rendering.
- `source_registry.json` entries can carry an optional new field `catalog_id` (string) pointing to the corresponding catalog record. This change is deferred to PR-B; this audit does not modify the registry.

---

## 8. Out of scope for this proposal

- No fetcher, scraper, or HTTP client design beyond the monitor posture sketched in §4.1.
- No ranking, retrieval, or RAG embedding format for topic cards.
- No UI rendering specification (see PR-K in the audit roadmap).
- No localization workflow for ko↔en↔zh↔vi (covered later when topic cards graduate to user-facing copy).
- No data warehouse / Supabase schema; topic cards are file-based for the foreseeable phases.

---

*End of schema proposal. See `data/sources/hikorea_source_catalog.example.json` for an illustrative skeleton.*
