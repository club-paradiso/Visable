# 2026-10-19 user-supplied HiKorea manuals: staging record

## Scope and non-claims
Two user-uploaded HWP 5.0 distribution-mode files, both with filename date `261019`, have been extracted to **review-only** plain text. Filename date is not independent proof of an official publication date or the effective date of every clause. The official notice/download URL was not verified here.

| Manual | Original HWP bytes | Original SHA-256 | Parsed text |
|---|---:|---|---|
| Visa / 사증민원 | 2,241,536 | `8f9f2e049b3cf09d46bf563e2d97fde596c3743318635f985bf35b51f79a5e8f` | [visa manual](/docs/source-manuals/2026-10-19/extracted/visa_manual_261019.txt) (30,431 lines, ~506k characters) |
| Stay / 체류민원 | 3,261,440 | `7effc9d03389e87dc3613db6da873a5d3807ddf4f506df2960f2b017fefabc07` | [stay manual](/docs/source-manuals/2026-10-19/extracted/stay_manual_261019.txt) (46,223 lines, ~775k characters) |

The original binary files are **not** included in this PR (the connector only committed the parsed texts). The hashes above were computed from the original attachments in this chat. Do not treat the extraction as page-faithful, especially for tables, captions, columns, appendices, and page/paragraph ordering.

## What is staged
- Source IDs: `visa_manual_2026_10_19_hwp_text`, `stay_manual_2026_10_19_hwp_text`
- New text files under `docs/source-manuals/2026-10-19/extracted/`
- Source registry + approval-index entries, each set to **pending_review / needs_review**
- A manifest `pending_review_editions` slot; **no change to `current`**
- An accessible review notice on `manual.html` with direct links to the two extracted texts

## Not yet completed
- Original HWP binaries deposited and verified against these hashes in GitHub
- Extraction completeness, section reading order and table reconstruction independently verified
- Same-parser structured diff from the current approved 2026-09 visa and stay editions
- Code/subcode/process-specific manual reconciliation, editorial review and owner approval
- Promotion to active searchable/citable corpus, form/document requirements, AI grounding, or visa authoring data

## Review gate before promotion
1. Store originals in repository or approved provenance storage, compare SHA-256.
2. Re-extract with `scripts/decrypt_hwp_distribution.py` and cross-check the file structure; verify HWP text against visible pages manually (especially tables).
3. Diff matching extraction pipelines for visa (2026-09-01 → 2026-10-19) and stay (2026-09-18 → 2026-10-19). For every changed status/subcode and application type, compare conditions, documentary evidence, exceptions, duration, fees and delegated application rules.
4. Independently verify each material change against the original and currently applicable statutes. Record reviewer, review date and effectivity. Update authoring statuses and rebuild generated datasets only after approval.
5. Only then promote `current`, update citations and the manual reader corpus and run repository checks. Keep older editions available for point-in-time citations.

**Safety invariant:** extracted but unreviewed content is displayed as `검토 전`. It must not override previously reviewed production requirements, be silently presented as the newest legally effective rule, or be direct evidence for Waymaker.
