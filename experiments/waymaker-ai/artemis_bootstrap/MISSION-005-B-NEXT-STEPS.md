# ARTEMIS MISSION 005-B — ROADMAP & NEXT STEPS
## External Legal Review Pilot, Cryptographic PKI Attestation & Clean-Room Blind Evaluation

- **Target Mission**: Artemis Mission 005-B
- **Preceding Baseline**: Mission 005-A (`feat/artemis-mission005-a`)
- **Repository**: `club-paradiso/Visable`
- **Scope**: Production legal verification, authentic practitioner reviews, and clean-room blind benchmarking

---

## 1. Executive Summary

Mission 005-A successfully established substantive foundations:
- **Real Model Inference Baseline**: Fully reproducible local MLX benchmark (`gemma-3-270m-it-4bit`) executed on Apple Silicon M1 (Peak RSS: 426.7MB, ~1.2s latency), confirming that small ungrounded models cannot perform legal reasoning (0.0% candidate pass rate, Official Gold: `N/A`).
- **Primary Source Evidence Audit**: 16 Group A priority review packets audited against primary sources (`law.go.kr`, `hikorea.go.kr`, 2026.10.19 manual extracts) with traceable dossiers (`source_located`: 12, `excerpt_mismatch`: 3, `version_mismatch`: 1).
- **Legal Source Versioning**: `LegalSourceCatalog` with immutable SHA-256 digests, chronological change tracking, and candidate invalidation diffing.
- **Evaluation Quality Audit**: Adversarial contrastive test suite proving keyword hits cannot mask reversed conclusions, amount inversions, or table role swaps.
- **Human Review Onboarding**: `REVIEWER-ONBOARDING.md` with COI declarations, verification checklists, and strict fail-closed boundaries.
- **Independent Benchmark Intake**: `independent_benchmark_intake.py` providing blind question projections, isolated answer keys, contamination auditing, and role-based access control.
- **8-Module Shadow Guardrails**: Multi-group evaluation reporting separate metrics for calibration fixtures (Precision: 100%, Recall: 100%), adversarial regression (Precision: 100%, Recall: 85.7%, 0 FP), and real model inference.

Mission 005-B translates these technical components into authentic external partnerships and production deployment.

---

## 2. Core Workstreams for Mission 005-B

### Workstream 1: Licensed Practitioner Review Pilot Execution
- **Objective**: Execute genuine, authenticated legal reviews on the 16 Group A packets with licensed immigration practitioners (행정사, 출입국 전문 변호사).
- **Execution Protocol**:
  1. Distribute review packets (`review_packets/*.json`) and onboarding guide (`REVIEWER-ONBOARDING.md`).
  2. Practitioners verify primary legal sources against official gazettes and current 2026 manuals.
  3. Practitioners complete the 4-step checklist, sign independence declarations, and document rationale.
  4. Ingest signed packets via `review_workbench.py import` with cryptographic verification.
- **Non-Negotiable Rule**: Never automate, simulate, or fabricate practitioner approvals.

### Workstream 2: Independent Clean-Room 100-Item Benchmark Authoring
- **Objective**: Address the `isolation_not_verified` limitation by authoring a completely clean, external 100-item evaluation set.
- **Protocol**:
  - Authored externally by independent legal practitioners without access to repo prompts or test suites.
  - Ingested via `BenchmarkSubmissionItem` schema.
  - Frozen dataset manifest generated with separate blind and key partition digests.
  - Contamination checked against public corpora via `ContaminationAuditor`.
  - Stored in an encrypted, air-gapped partition accessible only during ephemeral grading.

### Workstream 3: PKI Digital Attestation & Authoritative Promotion Layer
- **Objective**: Replace the local fail-closed prototype (`AuthoritativeGoldPromotionDisabledError`) with an authenticated cryptographic verification provider.
- **Architecture**:
  - Implement `X509SignatureVerifier` / W3C DID attestation provider.
  - Validate cryptographic digital signatures over packet digests before permitting `official_gold` promotion.
  - Append-only tamper-evident audit ledger backed by external timestamping authority.

### Workstream 4: RAG Retrieval Grounding & Legal Hallucination Elimination
- **Objective**: Overcome the 0.0% pass rate observed in ungrounded local model inference by integrating authoritative statutory retrieval.
- **Specifications**:
  - Ground inference queries directly against `data/manual-corpus/stay_manual_2026_10_19_md.json` and `visa_manual_2026_10_19_md.json`.
  - Evaluate retrieval augmented generation against the 20 development candidates.
  - Measure reduction in polarity reversal and statutory hallucinations.

### Workstream 5: Hardware-Aware Quantized Model Serving
- **Objective**: Provide scalable local inference options beyond 270M parameters.
- **Implementation**:
  - Test 4-bit quantized Qwen-2.5-7B-Instruct or Gemma-2-9B on unified memory hardware.
  - Maintain runtime memory profiling (< 6.0 GB) and measure tokens per second.

---

## 3. Milestones and Acceptance Criteria

| Milestone | Deliverables | Success Criteria |
|:---|:---|:---|
| **M5B.1** | External Practitioner Pilot | At least 8 Group A packets reviewed and signed by licensed practitioners |
| **M5B.2** | PKI Attestation Layer | Cryptographic digital signature verification passing; fail-closed on invalid signatures |
| **M5B.3** | 100 Blind Benchmark | Zero leakage verified by `ContaminationAuditor` on clean-room partition |
| **M5B.4** | RAG-Grounded Local Evaluation | Pass rate on dev 20 candidate set improving from 0.0% to > 70.0% |
| **M5B.5** | First Authoritative Gold Metric | First genuine `official_gold_pass_rate` calculated on cryptographically signed items |
