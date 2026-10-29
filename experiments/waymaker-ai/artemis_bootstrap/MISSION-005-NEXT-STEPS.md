# ARTEMIS MISSION 005 — ROADMAP & NEXT STEPS
## Authoritative Gold Certification, Air-Gapped Blind Evaluation & Production Guardrail Integration

- **Target Mission**: Artemis Mission 005
- **Preceding Baseline**: Mission 004-D (`feat/artemis-mission004-d`)
- **Repository**: `club-paradiso/Visable`
- **Scope**: Production readiness, authoritative legal certification, and clean-room evaluation

---

## 1. Executive Summary

Mission 004-D successfully delivered the foundations for trustworthy legal evaluation:
- 16 structured Group A review packets (`review_packets/*.json`, `*.md`)
- A local review workbench with non-authoritative draft controls and audit history
- An evaluation isolation protocol with explicit `isolation_not_verified` disclosure
- Reproducible multi-adapter evaluation runs
- An 8-module shadow guardrail runner with unit-fixture validation across 7 hand-authored calibration cases (0.04ms overhead) and nuance-protection heuristics for complex Korean conditional clauses

Mission 005 transitions these experimental prototypes into authoritative legal compliance and production guardrail middleware.

---

## 2. Core Workstreams for Mission 005

### Workstream 1: Authoritative Legal Review Pilot Execution
- **Objective**: Execute authentic legal review on the 16 Group A packets with licensed immigration practitioners (행정사, 출입국 전문 변호사).
- **Process**:
  1. Distribute review packets (`review_packets/`) to licensed legal reviewers.
  2. Reviewers verify primary legal sources (출입국관리법, 시행령, 시행규칙, 체류관리지침).
  3. Reviewers complete the structured checklist and sign findings.
  4. Import reviewed packets back into the review ledger with genuine legal provenance.
- **Rule**: Never automate or simulate legal review approvals.

### Workstream 2: Independent Clean-Room Blind Benchmark (100 Items)
- **Objective**: Address the `isolation_not_verified` limitation by authoring a completely independent, air-gapped 100-item evaluation set.
- **Protocol**:
  - Authored externally by independent legal experts without access to the codebase or prompt templates.
  - Stored in an encrypted, air-gapped repository partition.
  - Evaluation runtime accesses only blind projections (question and visa context), with expected answers revealed strictly inside an ephemeral grading container.
  - Generates verifiable cryptographic attestation of zero training-data contamination.

### Workstream 3: Independent Identity & PKI Attestation Layer
- **Objective**: Replace the local prototype's fail-closed restriction (`AuthoritativeGoldPromotionDisabledError`) with a genuine identity verification provider.
- **Architecture**:
  - Implement an extensible `IdentityAttestationProvider` interface.
  - Support PKI / X.509 digital certificates or W3C Decentralized Identifiers (DID) representing verified licensed practitioners.
  - Verify cryptographic signatures over packet digests before permitting `official_gold` promotion.
  - Maintain an append-only, tamper-evident audit ledger backed by external timestamping authority.

### Workstream 4: Production Guardrail Middleware
- **Objective**: Promote the offline 8-module shadow guardrail (`guardrail_shadow.py`) into production inference middleware.
- **Specifications**:
  - Asynchronous non-blocking inspection with fallback handling.
  - Strict latency budget (< 5ms; current empirical average is 0.01ms).
  - Dynamic alert severity thresholds:
    - `critical` (Polarity reversal, prompt injection compliance): Intercept and redirect to safe disclaimer response.
    - `high` / `warning` (Procedure confusion, fee anomalies): Tag response metadata and log to telemetry without blocking user experience.

### Workstream 5: Local Quantized Inference Adapter (M1 8GB Optimization)
- **Objective**: Enable local model inference on resource-constrained development machines without requiring external paid APIs or large unquantized weights.
- **Implementation**:
  - 4-bit quantized MLX / GGUF adapter (e.g. Gemma 2/4 2B/9B Q4_K_M).
  - Memory footprint strictly bounded under 4.5 GB to prevent swap thrashing on 8GB Apple Silicon machines.
  - Structured latency, tokens-per-second, and memory profiling.

---

## 3. Milestones and Acceptance Criteria

| Milestone | Deliverables | Success Criteria |
|:---|:---|:---|
| **M5.1** | External Legal Review Pilot | At least 8 Group A packets reviewed and signed by licensed practitioners |
| **M5.2** | PKI Attestation Verifier | Cryptographic signature validation passes; fail-closed behavior on invalid signatures |
| **M5.3** | Clean-Room 100 Blind Set | Zero leakage verified by `verify_benchmark_partitions` and commit history audit |
| **M5.4** | Production Middleware | Guardrail latency < 1ms p99; zero regression on Korean conditional sentences |
| **M5.5** | End-to-End Certified Run | First authoritative `official_gold_pass_rate` calculated on genuine gold items |
