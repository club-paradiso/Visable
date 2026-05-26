# DATA + F/G/H + LAW GROUNDING CONSOLIDATED ROADMAP (2026-05)

Date (UTC): 2026-05-26

## 1) Executive verdict
Paradiso is ready for the **next staged implementation sequence**, but not for immediate production data correction or live law-grounding activation.

## 2) What is ready now
- D0/D1D2 readiness artifacts exist and clearly gate patching.
- Batch 2 final rerun prompt and interactive GO/NO-GO standards are prepared.
- Law-grounding staged activation plan is documented with safe default retention (`disabled`).

## 3) What is still blocked
- No high-confidence patch-ready data entries from D0.
- F/G/H and many subcodes remain untested due to blocked prior interactive runs.
- Law-grounding live enablement requires staged verification and rollback readiness.

## 4) Data correction roadmap
Reference: `docs/audits/DATA_CORRECTION_NEXT_ROADMAP_2026_05.md`.
- D3A: A/B/C extraction and candidate corrections
- D3B: C/D/E subcode crosswalk stabilization
- D3C: F/G/H extraction/correction only after successful Batch 2 rerun
- D3D: manual-grounding JSON expansion after crosswalk stabilization

## 5) F/G/H audit roadmap
Reference: `docs/audits/BATCH_2_FINAL_INTERACTIVE_RERUN_PROMPT_2026_05.md`.
- enforce GO/NO-GO preflight
- treat blocked/static-only runs as non-coverage
- complete code/subcode/button/modal/AI audit outputs with issue IDs `PDA-B2R2-*`

## 6) Law grounding activation roadmap
Reference: `docs/integrations/LAW_GROUNDING_ACTIVATION_ROADMAP_2026_05.md`.
- Stage 0→5 progression only
- no default mode change
- no production activation in this PR

## 7) Risk register
- R1: false confidence from locator-only manual references
- R2: claiming F/G/H coverage from blocked/static-only runs
- R3: enabling law grounding without citation/fallback hardening
- R4: mixing legal authority and operational manual requirements in output
- R5: silent grounding failure causing fabricated certainty

## 8) Recommended PR sequence
1. PR E (if not merged): AI fallback safety
2. PR F: regression/smoke consolidation
3. PR G: final Batch 2 interactive audit rerun
4. PR H1: law-grounding disabled-mode smoke/runbook hardening
5. PR H2: law API debug endpoint verification
6. PR H3: opt-in law grounding integration
7. PR D3A: A/B/C source-confirmed corrections
8. PR D3B: C/D/E subcode crosswalk and corrections
9. PR D3C: F/G/H corrections after Batch 2 success

## 9) Machine-readable JSON roadmap list
```json
[
  {"pr":"E","title":"AI fallback safety","gate":"if_not_already_merged"},
  {"pr":"F","title":"regression_smoke_consolidation","gate":"after_E_or_in_parallel_if_safe"},
  {"pr":"G","title":"final_batch2_interactive_audit_rerun","gate":"visual_browser_go"},
  {"pr":"H1","title":"law_grounding_disabled_mode_smoke_and_runbook_hardening","gate":"stage0_safe_default"},
  {"pr":"H2","title":"law_api_debug_endpoint_verification","gate":"stage1_complete"},
  {"pr":"H3","title":"opt_in_law_grounding_integration","gate":"stage2_to_stage4_checks_pass"},
  {"pr":"D3A","title":"A_B_C_source_confirmed_data_corrections","gate":"patch_ready_source_confirmed_high"},
  {"pr":"D3B","title":"C_D_E_subcode_crosswalk_and_corrections","gate":"subcode_crosswalk_stable"},
  {"pr":"D3C","title":"F_G_H_data_corrections","gate":"batch2_success_and_source_confirmed"}
]
```
