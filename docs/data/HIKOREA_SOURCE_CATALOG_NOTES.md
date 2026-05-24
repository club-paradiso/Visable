# HiKorea Source Catalog v1 — Notes

**Date:** 2026-05-24
**Branch:** `data/hikorea-source-catalog-v1`
**Companion to:** `docs/data/HIKOREA_SOURCE_MAP_AUDIT.md` and `docs/data/HIKOREA_SOURCE_SCHEMA_PROPOSAL.md`

---

## What this PR adds

Two machine-readable catalog files plus this notes document:

| Path | Records | Purpose |
|---|---|---|
| `data/sources/hikorea_source_catalog.json` | 33 | Main public-source catalog across all 15 required domains |
| `data/sources/immigration_notice_sources.json` | 10 | Notice / press / materials indexes (highest-value monitoring targets) |
| `docs/data/HIKOREA_SOURCE_CATALOG_NOTES.md` | — | This file |

Both JSON files conform to the field set required by the catalog task:
`source_id`, `title_ko`, `title_en`, `url`, `domain`, `category_path`,
`language`, `source_type`, `monitoring_priority`, `extract_mode`,
`requires_login`, `include_in_user_search`, `legal_sensitivity`,
`expected_update_frequency`, `notes`, `status`, `needs_review`,
`scrape_allowed`, `monitor_enabled`, `retrieved_at`.

Where a record aligns with an existing placeholder in
`data/source_registry.json`, an additional `registry_id` field links the
two (e.g. `hikorea_notice_index` ↔ `hikorea_notice_placeholder`).

This catalog is **descriptive metadata only**. No runtime code path reads
either file. Nothing in this PR enables a fetcher, scraper, monitor, or
scheduler. No UI is changed and no production dataset is modified.

---

## What was intentionally excluded

The following surfaces were considered and **excluded by hard rule**:

- **My Page / application status** on HiKorea — login-walled and personal.
- **Payment / fee transactions** — out of scope.
- **In-flight e-Application form sessions** — authenticated, mid-transaction.
- **Visit Reservation slot grids** — authenticated and personally identifying.
- **Residence-card validity check result page** — produced from personal-data input; not mirrorable.
- **Address → office lookup query results** — live MoJ service, not Paradiso's logic to replicate.
- **Soci-Net enrollment, course booking, test booking, certificate verification** — login-walled.
- **Visa Portal online application** — login-walled.
- **Embassy / consulate appointment systems** — out of scope.
- **Any URL with a CAPTCHA gate, session cookie, or rate-limit auth** — out of scope.

The five service portals listed above that **do** appear in the catalog
(`hikorea_eapplication_portal`, `hikorea_visit_reservation_portal`,
`hikorea_residence_card_validity_check_portal`,
`hikorea_office_lookup_service`, plus `visa_portal_mofa_root` and
`socinet_root` as adjacent_official records) are present as
**link-only references** with `extract_mode="link_only"`,
`scrape_allowed=false`, and `requires_login=true` where applicable.

---

## Why some services are link-only

Per the audit (§5 of `HIKOREA_SOURCE_MAP_AUDIT.md`) and the schema
proposal (§2.1, `service_portal` category), the following surfaces must
be **deep-linked** with clear labels and never mirrored, scraped, or
automated:

| Source | Why link-only |
|---|---|
| `hikorea_eapplication_portal` | Authentication + personal data input; automating it is unauthorized agency |
| `hikorea_visit_reservation_portal` | Authentication + slot allocation; scraping would compete with real users for slots |
| `hikorea_residence_card_validity_check_portal` | Personal-data input; must not retain or proxy such queries |
| `hikorea_office_lookup_service` | Live MoJ service; jurisdiction logic is MoJ's, not Paradiso's |
| `visa_portal_mofa_root` | Mixed portal; sub-flows require auth; treat root as link-only |
| `socinet_root` | KIIP operational portal; most surfaces are login-walled |
| `oka_root` | New agency portal; section paths not yet stable enough to mirror |
| `center_1345_root` | Reference contact card only; no content extraction |

For each, Paradiso UI work in a later PR (`ui/source-attribution-affordance`)
should provide an outbound link with a "leaves Paradiso" affordance, plus
the 1345 fallback.

---

## How `scrape_allowed` and `monitor_enabled` were assigned

Both flags default to `false` for every v1 record. This is intentional.

The task rule permits:

- `scrape_allowed=true` for "clearly public, static guide/index pages",
- `monitor_enabled=true` for "public notice indexes or public guide pages
  suitable for later read-only monitoring".

However, in v1 **no record** has both an operator-verified URL **and**
operator-confirmed posture (robots.txt check, KOGL classification, rate
budget). Setting either flag to `true` before that operator step would
violate the audit's posture: catalog descriptive first, monitor wiring in
a separate PR.

The plan:

- **PR-B (this PR):** catalog populated; all flags `false`.
- **PR-C (`scripts/source-monitor-extension`):** operator confirms the
  notice-index URLs flagged below, fills `robots_allowed`, flips
  `monitor_enabled=true` on a small, audited subset, and extends
  `scripts/check_source_updates.py` accordingly (still default-off and
  still respecting the existing `--allow-network` gate).
- **PR-D and beyond:** content-extract pages can have `scrape_allowed=true`
  only after the operator confirms the page is static, the URL is
  permanent, and the reuse license (KOGL type) is recorded.

URL-confidence policy in v1:

- Where the canonical landing URL is a long-standing root on an official
  government host (`hikorea.go.kr`, `immigration.go.kr`, `moj.go.kr`,
  `socinet.go.kr`, `visa.go.kr`, `1345.go.kr`, `law.go.kr`, `oka.go.kr`,
  `kosis.kr`), the URL is included.
- Where the page lives at a query-string-driven path on HiKorea
  (`?menuSeq=...&categorySeq=...`), the URL is left as `null` and the
  record is marked `needs_review=true` with an explanatory note. These
  paths are notoriously unstable across HiKorea redesigns; pinning them
  is operator work.
- All statute landings on `law.go.kr` use the portal root rather than an
  encoded-Korean deep URL; the canonical 법제처 OPEN API path is the
  preferred fetch route (already an active placeholder in
  `data/source_registry.json`).

No URL in either catalog file was confirmed by live HTTP retrieval as
part of this PR. The audit's posture — no scraping, no automated probes —
is preserved. `retrieved_at` is `null` on every record.

---

## Records that need human legal / admin review

Every record in the v1 catalog has `needs_review=true` except a small
set of established structural references:

| Record | Why `needs_review=false` |
|---|---|
| `moj_visa_manual_2026_05` | Already mirrored under `docs/source-manuals/2026-05/` and registered in `data/source_registry.json` |
| `moj_stay_manual_2026_05` | Same |
| `hikorea_root_portal` | Root URL is stable; treated as navigation only |
| `immigration_service_root` | Same |
| `moj_root` | Same |
| `socinet_root` | Same (link-only reference) |

All other records — including every guide page, every statute landing,
every notice index, and every service portal — carry `needs_review=true`.
Reviewers should look at the `notes` field of each record for the
specific verification action required.

### High legal-sensitivity records

The following carry `legal_sensitivity="high"` and must not produce
user-facing copy without explicit legal / admin review:

| `source_id` | Domain | Reason |
|---|---|---|
| `hikorea_reporting_workplace_change_guide` | sojourn | E-series unauthorized-work risk on misinterpretation |
| `hikorea_nationality_guide_root` | nationality | Discretionary outcomes; held for legal review |
| `hikorea_naturalization_guide` | naturalization | Discretionary outcomes; held for legal review |
| `hikorea_refugee_guide_root` | refugee | Vulnerable-population content; external (legal + advocacy) review required |
| `hikorea_residence_card_validity_check_portal` | certificate | Personal-data input service |
| `hikorea_visit_reservation_portal` | reservation | Authenticated service |
| `hikorea_eapplication_portal` | e_application | Authenticated filing service |
| `hikorea_seasonal_worker_guide` | seasonal_worker | Frequent quota/MoU notice churn; freezing tables risks misinforming employers |
| `moj_seasonal_worker_notice_stream` | seasonal_worker | Same; notice-driven domain |

Of these:

- `hikorea_refugee_guide_root` and `hikorea_naturalization_guide` must
  not be promoted into topic cards without external reviewer sign-off
  (see audit §7).
- The four service portals are **never** to be promoted into anything
  other than link-only references regardless of review outcome.

---

## Domain coverage summary

| Domain | Catalog records | Notice records | Total |
|---|---:|---:|---:|
| visa | 3 | 0 | 3 |
| sojourn | 5 | 0 | 5 |
| nationality | 2 | 0 | 2 |
| naturalization | 2 | 0 | 2 |
| overseas_korean | 3 | 0 | 3 |
| refugee | 2 | 0 | 2 |
| certificate | 2 | 0 | 2 |
| office_lookup | 2 | 0 | 2 |
| reservation | 1 | 0 | 1 |
| e_application | 1 | 0 | 1 |
| civil_forms | 1 | 0 | 1 |
| notices | 4 | 8 | 12 |
| social_integration | 2 | 1 | 3 |
| seasonal_worker | 1 | 1 | 2 |
| statistics | 2 | 0 | 2 |
| **Total** | **33** | **10** | **43** |

All 15 required domains have at least one record.

---

## Recommended next PR after this catalog

Per the audit's PR sequence (§10 of `HIKOREA_SOURCE_MAP_AUDIT.md`):

**Next: PR-C — `scripts/source-monitor-extension`.** Extend
`scripts/check_source_updates.py` to handle notice indexes from the v1
catalog. Specifically:

1. Operator verifies and fills the `url` field on the
   `*_notice_index`, `*_press_index`, and `*_materials_index` records
   in `data/sources/immigration_notice_sources.json`.
2. Operator fills `robots_allowed` (after a manual robots.txt check)
   and an explicit per-host rate budget in a new operator-only config.
3. The script gains a notice-index discovery mode that respects
   `If-Modified-Since` / `ETag` first and only computes a body hash on
   fallback (per the schema proposal §4.1).
4. The script remains default-off; the existing `--allow-network` gate
   is unchanged.
5. Any detected change writes a candidate file for human review (mirrors
   the existing `scripts/promote_grounding_candidate.py` pattern).
6. No user-facing content is produced or promoted in PR-C.

Subsequent PRs (D, E, F, G, H, I, J, K) follow the audit roadmap. Each
will reference catalog `source_id`s from this PR — that is the primary
reason this catalog exists today.

---

## Hard rules restated

For future contributors editing these files:

- Public official sources only. No private, login-walled, personal-data,
  CAPTCHA-gated, or transactional URLs as scrape targets.
- `scrape_allowed=false` and `monitor_enabled=false` are the safe
  defaults. Flip either only with operator confirmation per the gate
  steps above.
- HiKorea guide pages are official but potentially stale; statute and
  manual sources are stronger.
- Conflict or uncertainty → `needs_review=true` plus an explanatory note.
- No legal-advice language anywhere in `notes` or in any downstream
  topic card built from these records. Paradiso remains an information
  and guidance platform.

---

*End of notes. This PR ships a catalog skeleton. No runtime behavior
changes.*
