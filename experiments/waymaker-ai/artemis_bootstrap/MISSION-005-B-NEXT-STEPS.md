# Waymaker Artemis — Mission 005-B next steps

This plan supersedes the earlier roadmap at `d3e9490`. The canonical foundation
is Google Gemma 4 E4B Instruct, governed by
[the foundation policy](../configs/artemis_foundation.json).

Mission 005-B execution update, 2026-10-30: the dedicated runtime and actual
processor/template initialization now pass. Genuine model execution remains
blocked by the existing swap limit; see the [real inference report](MISSION-005-B-REAL-INFERENCE-REPORT.ko.md).
The steps below remain gated on actual generation, not environment preparation.

1. Prepare an isolated MLX-VLM 0.7.11 environment with processor dependencies.
   Free disk/swap headroom on the M1 or use suitable hardware. Do not alter a
   related worktree's environment. Run the single 32-token Korean probe and
   preserve all metrics/raw output. Package/metadata checks alone are insufficient.
2. Only after successful basic inference, run the 20 dev candidates with their
   evaluation keys kept out of prompts. Record exact model and revision. Do not
   reuse historical noncanonical outputs as this baseline.
3. Obtain independent legal review and a trusted attestation-verification design.
   Existing source-location audits are research, not human approval. Keep gold
   promotion and accuracy fail-closed until an independent authority is connected.
4. Commission and freeze the independent benchmark outside developer access.
   Existing 40 held-out candidates remain `isolation_not_verified`.
5. Build the separate reviewed legal-response SFT dataset, preserving source
   versions, citation alignment and split isolation. Run the E4B five-step CUDA
   QLoRA compatibility test before any full adaptation. E2B remains a separately
   selected development experiment and cannot stand in for E4B validation.
6. Evaluate guardrail false negatives and false positives separately on synthetic
   cases and provenance-verified model outputs. No aggregate legal accuracy claim.
7. Validate adapter save/reload and deployment conversion only after independent
   evaluation. Paid compute, large downloads, deployment and merge need explicit
   authorization; none was started in the recovery.

Implementation detail and resource estimates:
[Gemma 4 fine-tuning plan](WAYMAKER-ARTEMIS-FINETUNING-PLAN.md).
Official Gold Accuracy = **N/A**. No legal reviewer approval has been invented.
