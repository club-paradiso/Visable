# Manual Text Extraction Status — 2026-05

## Result: manual **body** text is DRM-protected and not extractable here; only the official **TOC preview** is recoverable

Both committed HWP manuals are **배포용 (distribution-protected) Hangul documents**.
Their real body content lives in encrypted `ViewText/Section*` streams (the
`DocOptions/_LinkDoc` distribution DRM); the normal `BodyText/Section0` stream is
just a 314-byte "open me in the latest Hangul viewer" placeholder. The committed
PDFs are image-only. So **no manual body text (제출서류 lists, per-status prose)
could be extracted** in this environment.

**However**, each HWP carries a readable, unencrypted `PrvText` preview stream
containing the manual's **official table of contents**, which *is* genuine
extractable evidence and is committed under `docs/data/manual_text_2026_05/`.

## Tools used / attempted

- `olefile` + `zlib` + a custom HWP5 record walker (`scripts/extract_hwp_manual_text.py`)
  — reads `BodyText` (placeholder only) and `PrvText` (real TOC).
- `pdfminer.six` attempted — **import panics** here
  (`cryptography`/`_cffi_backend` → `pyo3_runtime.PanicException`); PDFs image-only regardless.
- No `pdftotext`/`pdfinfo`/`hwp5txt`; `soffice` present, not used for headless conversion this pass.

## Per-source results

| Source | Result |
| --- | --- |
| `stay_manual_2026_05_21.hwp` | **Body DRM-encrypted.** `BodyText/Section0` = 314-byte placeholder; real content in encrypted `ViewText/Section0–22` (raw-inflate fails, full-byte entropy). **`PrvText` TOC recovered** → `docs/data/manual_text_2026_05/stay_manual_2026_05_PrvText_TOC.txt` (외국인체류 안내매뉴얼 2026.5; lists all 41 status sections 외교(A-1) … K-STAR). |
| `visa_manual_2026_05_21.hwp` | **Body DRM-encrypted.** Same structure. **`PrvText` TOC recovered** → `docs/data/manual_text_2026_05/visa_manual_2026_05_PrvText_TOC.txt` (사증발급 안내매뉴얼 2026.5; lists 40 status sections). |
| `stay_manual_2026_05.pdf` | Image-only; pdfminer unusable here. No text. |
| `visa_manual_2026_05.pdf` | Image-only. No text. |

> Honesty note: an earlier draft of this report claimed a successful
> ~470K-character HWP **body** extraction with all status headers located. **That
> was wrong** — the body is DRM-encrypted; only the 1,023-char `PrvText` TOC is
> recoverable. The false `*_extracted.txt` artifacts and claims were removed and
> replaced with the genuine TOC previews.

## What the TOC evidence does / does not support

- **Does** confirm (status-level, official): which statuses each 2026.5 manual
  covers and the manual titles/dates — useful for the source/section registry.
- **Does not** provide per-status 제출서류 (required-document) lists or page-cited
  sections — those are in the encrypted body. So **no field-level required-document
  correction** can be grounded from these files here.

## Only usable field-level evidence remains the committed grounding

`backend/data/manual_grounding/stay_manual_grounding_2026_05.json` (3
`verified_locally` extension entries: D-2 p.43-44, D-4 p.90-91, E-7 p.226),
produced earlier with `pdftotext` in a different environment. Those are already
reflected/covered in `main`.

## To unblock field-level corrections later

- An **un-DRM'd** copy of the 2026.5 HWP manuals (saved in normal format), or a
  text-extractable / OCR'd PDF that also recovers printed page footers.
- Not possible in this environment → this pass commits TOC + analysis artifacts
  and applies **0** production data corrections.
