# Repository Audit: Paradiso Visa Manual Groundwork
**Date:** 2026-06-08  
**Scope:** Inventory of data sources, runtime entry points, and references to visa/status documentation

---

## 1. Data Files Inventory

### Primary Data Files

| File | Location | Format | Role | Status |
|------|----------|--------|------|--------|
| `visa_data.json` | `/workspaces/Paradiso/` | JSON (array) | Canonical visa/status registry | ✓ Exists, 5.7K+ records |
| `doc_master.json` | `/workspaces/Paradiso/` | JSON (array) | Normalized document dictionary | ✓ Exists, 100+ doc types |
| `backend/data/visas.json` | `/workspaces/Paradiso/backend/data/` | JSON (array) | Backend deployed copy (synced from visa_data.json) | ✓ Exists, identical to visa_data.json |

### Supporting Data Files

| File | Location | Purpose |
|------|----------|---------|
| `data/scenario_help_records.json` | `/workspaces/Paradiso/data/` | Shadow store of 17 scenario/help/FAQ records; mirrors entries in visa_data.json |
| `data/removed_from_visa_data_scenario_records_20260608.json` | `/workspaces/Paradiso/data/` | Audit snapshot of records that are in visa_data.json but marked for future removal |
| `data/source_registry.json` | `/workspaces/Paradiso/data/` | Registry of source manual versions and metadata |
| `docs/data/visa_status_coverage_audit_2026_05.json` | `/workspaces/Paradiso/docs/data/` | Coverage audit output (read-only) |

---

## 2. Runtime Entry Points

### Frontend (index.html)

#### Data Loading
- **Line 16864, 18215:** Two fetch calls to `./visa_data.json` with `cache: 'no-store'`
  - Indicates fresh data pull on each search session
  - Error handling: throws if HTTP status not OK

#### Schema References
- **Line 13280–13292:** Function `getManualDomains(v)` checks for `v.manualDomains` array field
  - Used to determine if status has domain-specific guidance
  - Domains currently referenced: `'visa_issuance'`, `'stay_sojourn'`

- **Line 14551–14552:** References to domains for manual citation
  - `visa_issuance` → label: "사증발급"
  - `stay_sojourn` → label: "체류민원"

- **Line 13028:** Comment confirms DOC_DICT is kept in sync with doc_master.json

#### Document Rendering
- **Line 12034:** Text about visa issuance fees at overseas missions

### Backend (paradiso_backend.py)

#### Load Strategy
- **Line 1970–2000:** Function `_candidate_visa_paths()` searches for visa data in priority order:
  1. `VISA_DATA_PATH` environment variable (explicit override)
  2. `backend/data/visas.json` (committed copy for deployment)
  3. `visa_data.json` (repository root fallback for local dev)

- **Line 2027–2095:** Function `_load_visas()` implements deterministic loading
  - Attempts union resolver first (record_store_union) for E-4A plumbing
  - Falls back to path-based loading if resolver unavailable
  - Caches globally (`_VISAS_CACHE`) for request-level efficiency
  - Returns metadata: `source_type` in ['fallback', 'backend-data', 'repo-root', 'union-resolver']

- **Line 3315:** `/api/visas` endpoint calls `_load_visas()` to fetch records

#### Document Resolution
- **Line 13028 in index.html (mentioned in backend context):** Every doc ID must resolve through DOC_DICT to doc_master.json

---

## 3. Schema Analysis

### Top-Level Visa Record Fields (visa_data.json / backend/data/visas.json)

Core fields observed:
```
- code (string): Visa code, e.g., "D-2", "F-1"
- name (string): Korean name of status
- cat (string): Category, e.g., "short", "long"
- period (string): Permitted stay duration
- dataBadge (string): Data source/version tag
- dataDate (string): Metadata timestamp
- newReq (string): Narrative requirement summary
- newReqDocs (array): Initial entry doc IDs referencing doc_master.json
- extReq (string): Extension requirement narrative
- extReqDocs (array): Extension doc IDs
- faq (string): FAQ block (multi-question)
- aliases (array): Search aliases for the status
- subCodes (array): Subordinate codes (e.g., B-1-1, B-1-2)
- initialReqDocs (array): Canonical initial doc list
- extensionReqDocs (array): Canonical extension doc list
- changeReqDocs (array): Canonical change-of-status doc list
- procedures (object): Structured procedure blocks
  - extension (object):
    - available (boolean)
    - summary (string)
    - requiredDocs (object with commonDocs, requiredDocs, additionalDocs, conditionalDocs)
    - notes (array)
    - manualRefs (array): Manual citations with page ranges
  - registration (object): Similar structure to extension
- manualDomains (array): **DOMAIN FIELD** — tracks which manual sections apply
  - Observed values: 'visa_issuance', 'stay_sojourn'
  - Used by getManualDomains() in index.html line 13280
```

### Key Observation: manualDomains Field

- **Current State:** Field exists in some records but not all
- **Usage:** Signals whether guidance comes from 체류민원 매뉴얼 (stay manual) vs. 사증발급 매뉴얼 (visa issuance manual)
- **Missing Records:** Not all records have this field populated
- **Future Intent:** Will enable separate UI tabs for domain-specific guidance

---

## 4. Legacy Warning Strings

### Warning Found in visa_data.json (Line 2064, D-2 record)

```
"(체류민원 매뉴얼 기준이므로 재외공관 사증발급 서류는 별도 사증 매뉴얼 확인이 필요합니다."
```

**Translation:**  
"(This is based on the stay-procedures manual; documents for overseas-mission visa issuance must be separately verified in the visa-issuance manual)"

**Location in Record:**
- visa_data.json, line 2064, D-2 record, `newReq` field, end of paragraph

**Context:** This warning appears as a disclaimer appended to the D-2 (Student visa) requirements narrative. Similar patterns may exist in other records.

### Grep Results Summary

Search for `체류민원 매뉴얼|별도 사증 매뉴얼` returned 100+ matches:
- Majority are in **visa_data.json** (baseline data)
- Many in **scripts/** (data migration/cleanup scripts)
- Several in **docs/** (audit snapshots)
- Archive copies in **docs/archive/**

---

## 5. Validation Scripts

### Key Validation Checks

| Script | Location | Purpose | Data Inputs |
|--------|----------|---------|-------------|
| `check_doc_master_integrity.py` | `/workspaces/Paradiso/scripts/` | Verify doc IDs in visa_data.json resolve to doc_master.json; detect duplicates | visa_data.json, doc_master.json |
| `check_scenario_help_records.py` | `/workspaces/Paradiso/scripts/` | Verify scenario_help_records.json mirrors byte-for-byte with visa_data.json source records | visa_data.json, scenario_help_records.json, doc_master.json |
| `sync_visa_data.py` | `/workspaces/Paradiso/scripts/` | Synchronize backend/data/visas.json with canonical visa_data.json | visa_data.json → backend/data/visas.json |
| `check_required_documents_coverage.py` | `/workspaces/Paradiso/scripts/` | Audit document field coverage for all statuses | visa_data.json or backend/data/visas.json |
| `check_repo.sh` | `/workspaces/Paradiso/scripts/` | Shell-based smoke tests for repository integrity | (runs multiple internal checks) |

---

## 6. Runtime Implications

### Data Flow: Current State

```
┌─────────────────────────────────────────────────────────────┐
│ Development / Local                                         │
├─────────────────────────────────────────────────────────────┤
│  visa_data.json                                             │
│  └─→ (fetch by frontend index.html at runtime)             │
│  └─→ (read by backend if env VISA_DATA_PATH not set)      │
│  └─→ (source for backend/data/visas.json via sync script)  │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Deployment (Railway)                                        │
├─────────────────────────────────────────────────────────────┤
│  backend/data/visas.json (committed copy, fast path)       │
│  └─→ Preferred if present (backend paradiso_backend.py)    │
│  └─→ Fallback: reads visa_data.json from repo root         │
│  └─→ Frontend fetches visa_data.json (no backend override) │
└─────────────────────────────────────────────────────────────┘
```

### Search & Indexing

- Frontend search is triggered by user input and fetches fresh visa_data.json
- No persistent search index referenced (search is in-memory, filtered)
- AI grounding (if enabled) reads from loaded visa records + manual sources

### Backend API Exposure

- **`GET /api/visas`** returns the full visa list loaded via `_load_visas()`
- Source metadata included in response (source_type tag)
- Doc IDs in records are resolved client-side against doc_master.json

---

## 7. Compatibility Contracts

### Hard Constraints

1. **visa_data.json Shape:** Array of objects with visa code, name, procedures
   - Changing structure breaks frontend fetch + backend parsing
   - Field `manualDomains` is optional but used if present

2. **doc_master.json IDs:** Must be stable
   - Every doc ID in visa records must exist in doc_master.json
   - Validated by check_doc_master_integrity.py

3. **Backend Data Priority:** backend/data/visas.json takes precedence
   - Must be kept in sync with visa_data.json
   - Deployment relies on this being fresh

4. **Search Logic:** Field-level search (aliases, code, name)
   - No changes to search indexing expected in this audit

### Optional Fields (Safe to Extend)

- `manualDomains` array — frontend safely ignores if absent
- New fields in procedures block — backend ignores unknown keys
- Custom metadata fields — no validation required

---

## 8. Risk Points

### High-Risk Areas

1. **manualDomains Population Gap**
   - Not all records have `manualDomains` field
   - UI logic (getManualDomains) defaults to empty array if missing
   - **Risk:** Tabs will not render correctly for unpopulated statuses

2. **Legacy Warning Persists**
   - Warning string "체류민문 매뉴얼 기준이므로..." appears in visa_data.json
   - Will render verbatim in frontend
   - **Risk:** User sees outdated disclaimer until removed

3. **Dual-Source Inconsistency**
   - Scenario records split between visa_data.json and scenario_help_records.json
   - Deep-equality check enforced by check_scenario_help_records.py
   - **Risk:** Migration to separate storage will require schema and runtime changes

4. **Data Sync Dependency**
   - Backend prefers backend/data/visas.json but falls back to visa_data.json
   - If sync script fails, backend and frontend may diverge
   - **Risk:** Deployment may run stale data if sync not triggered

### Medium-Risk Areas

5. **Manual Source References**
   - Records contain `manualRefs` with page ranges and source dates
   - No validation that referenced pages actually exist in source PDFs
   - **Risk:** Page ranges may be outdated; needs periodic re-verification

6. **doc_master.json Stability**
   - 100+ doc types; any ID rename breaks visa records
   - No deprecation mechanism; deletion is breaking change
   - **Risk:** Future schema refactoring must maintain backward compat

---

## 9. File References Summary

### Configuration
- `.claude/settings.local.json`: Contains build step `cp visa_data.json → backend/data/visas.json`
- `backend/README.md`: Documents data sync strategy and fallback loading

### Scripts for Maintenance
- `scripts/check_repo.sh`: Runs all validation checks
- `scripts/sync_visa_data.py`: Syncs backend copy
- `scripts/check_doc_master_integrity.py`: Validates doc references

### Documentation
- `docs/paradiso_ai_safe_automation_architecture.md` (line 430): Warns against modifying visa_data.json directly without proper validation
- `backend/README.md` (lines 208, 213, 339): Details on data loading strategy

### Test Coverage
- `backend/tests/test_paradiso_backend.py` (line 6, 56): Tests visa loading with fallback behavior

---

## 10. Validation State

**All discovered files exist:**
- ✓ visa_data.json
- ✓ backend/data/visas.json
- ✓ doc_master.json
- ✓ data/scenario_help_records.json
- ✓ data/source_registry.json
- ✓ All referenced scripts

**Cross-references:**
- ✓ Backend loads visas via defined path search
- ✓ Frontend fetches visa_data.json
- ✓ index.html references doc_master.json implicitly
- ✓ All validation checks present

**No missing source files detected.**

---

## Next Steps (Recommendations)

1. **Populate manualDomains** for all records that have manual source data
2. **Remove or replace** legacy warning string with structured domain tabs
3. **Define visa_issuance_procedures.json** schema for overseas-mission procedures
4. **Extend doc_master.json** with domain tags if needed
5. **Run validation suite** after any schema changes (scripts/check_repo.sh)
