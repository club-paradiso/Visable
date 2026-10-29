# ARTEMIS MISSION 004-D ROADMAP & ACTION PLAN
## Human Review Pilot, Clean-room Freeze Protocol & Serving Guardrail Integration

- **Target Mission**: ARTEMIS MISSION 004-D
- **Baseline Established**: Mission 004-C (`artemis_runner.py`, `legal_review_governance.py`, 1,452 passing tests)
- **Document Version**: 1.0.0
- **Status**: Ready for execution

---

## 1. Context & Mission 004-C Baseline

Mission 004-C established the operational execution and governance layer:
1. **Model Evaluation Runtime (`artemis_runner.py`)**: Unified offline runner with Mock, Recorded, and Local MLX adapters, reproducible run artifacts (`run_summary.json`, `report.md`, `error_summary.csv`, `run_manifest.json`), and 14-category diagnostic error analysis.
2. **Evaluation Modes & Strict Gating**:
   - Mode A (`infra_validation`): Synthetic fixtures for software integrity.
   - Mode B (`candidate_eval`): Diagnostic agreement for 60 unverified candidate items, official gold accuracy isolated as `N/A`.
   - Mode C (`gold_eval`): Strictly verified legal items; returns `N/A` when 0 verified items exist.
3. **Legal Review Governance (`legal_review_governance.py`)**:
   - Audit ledger (`reviews/legal_review_ledger.json`) tracking all 60 items.
   - Controlled state transitions with AI self-approval prevention (`AIApprovalForbiddenError`).
   - Promotional gating requiring verified evidence snapshot hashes and human reviewer signatures.

---

## 2. Mission 004-D Core Workstreams

### Workstream 1: Group A Human Legal Review Pilot (16 Items)
- **Objective**: Conduct the first pilot review with licensed immigration attorneys or certified administrative agents (`행정사`) for the 16 high-priority Group A items.
- **Target Items**:
  - 6 Prompt Injection Probes: `DEV-013`, `DEV-014`, `HLD-013`, `HLD-014`, `HLD-033`, `HLD-034` (Security policy sign-off).
  - 10 Complex Legal Policy Items: `HLD-004` (F-2-R local residency), `HLD-007` (2026.10 Immigration Act revision), `HLD-008` (K-point E-7-4 TOPIK scores), `HLD-023` (F-2-7 income proof), `HLD-027` (Act Article 17 notices), `HLD-028` (financial proof differential), `HLD-031` (E-9 to E-7-4 transition), `HLD-032` (D-2 vacation work permit), `HLD-036` (business registration for foreigners), `HLD-037` (F-2-7 duration tiers).
- **Procedure**:
  1. Reviewers claim items via `legal_review_governance.py claim <item_id> --reviewer <human_name>`.
  2. Inspect statutory text on official gazette (`law.go.kr`) and Hikorea manual (`hikorea.go.kr`).
  3. Record decision via `legal_review_governance.py decide <item_id> --decision approve --reviewer <name> --reason <substantive_rationale>`.
  4. Promote approved items to `official_gold`.

### Workstream 2: Clean-room Containerized Freeze Protocol for Heldout Set
- **Objective**: Prevent prompt engineers and model developers from having visibility into the 40 heldout candidate items during prompt tuning.
- **Protocol**:
  1. Package `artemis_eval_heldout_40.json` into a read-only, encrypted volume or dedicated clean-room evaluation environment.
  2. Restrict developer read permissions on heldout answers in the active workspace.
  3. Run blind evaluation via `artemis_runner.py` inside an isolated container, outputting only aggregate diagnostic pass rates and blinded failure category counts.

### Workstream 3: External Offline Inference Benchmarking
- **Objective**: Measure real model weights (Gemma 4 E4B MLX or quantized weights) in an environment with sufficient RAM (>= 16GB) and disk storage.
- **Protocol**:
  1. Deploy `LocalModelAdapter` on dedicated benchmarking hardware.
  2. Execute `python -m artemis_bootstrap.artemis_runner --mode candidate_eval --adapter local_mlx --benchmark benchmarks/artemis_eval_dev_20.json`.
  3. Save generated responses into recorded JSONL files.
  4. Compare latency, memory RSS, and diagnostic error rates against deterministic baselines.

### Workstream 4: Production Serving Guardrail Integration
- **Objective**: Export the hardened evaluator checks into the real-time serving path (`backend/` or middleware).
- **Target Guardrails**:
  1. `detect_polarity_and_permission_reversal`: Intercept generated answers that flip statutory prohibitions into permissions before displaying to the end user.
  2. `detect_role_and_column_swaps`: Block answers transposing table figures (e.g. 1회 부여기간 vs 총 체류기간).
  3. `check_forbidden_subject_binding`: Filter out cross-subject misattributions (e.g., applying 4-person income criteria to 1-person applicants).

---

## 3. Milestones and Acceptance Criteria

| Milestone | Target Deliverable | Acceptance Criteria |
|:---|:---|:---|
| **M1** | Group A Review Sign-off | At least 10 items in `legal_review_ledger.json` transition to `verified_by_human` with human signatures |
| **M2** | First Non-Zero Gold Benchmark | Mode C (`gold_eval`) executes with verified items, producing the first valid official gold accuracy percentage |
| **M3** | Clean-room Blind Evaluation | Heldout evaluation runs inside container without leaking item text to training logs |
| **M4** | Runtime Guardrail Middleware | Serving latency overhead < 50ms per response while intercepting 100% of synthetic test reversals |
