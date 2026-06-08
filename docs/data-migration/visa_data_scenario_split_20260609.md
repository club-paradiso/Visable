# Paradiso visa_data canonical split PR 1

This package performs the first data-only migration step:

1. Replace `visa_data.json` with a canonical-only version.
2. Preserve removed scenario/FAQ/common guidance records in `data/scenario_help_records.json`.
3. Preserve a byte-level audit-style snapshot in `data/removed_from_visa_data_noncanonical_records_20260609.json`.
4. Add `data/visa_data_split_report_20260609.json` for review counts and removed code list.

This package intentionally does **not** change frontend search rendering or AI grounding. Those should be handled in a separate PR after this data split lands.

## Counts

- Source records: 59
- Kept canonical records: 42
- Removed noncanonical records: 17

## Removed codes

- `K-ETA`
- `TB-1`
- `SCN-1`
- `SCN-2`
- `SCN-3`
- `SCN-4`
- `SCN-5`
- `SCN-6`
- `OVS-1`
- `NHIS-1`
- `FAQ-1`
- `FAQ-2`
- `FAQ-3`
- `FAQ-4`
- `VW-1`
- `COM-1`
- `RF-1`
