#!/usr/bin/env python3
"""Paradiso matrix-driven manual-grounding candidate generator.

Given a row id in ``backend/data/eval/paradiso_coverage_matrix.json``,
this script attempts to locate the corresponding section in a
committed source manual PDF and writes a **draft** candidate folder
under ``backend/data/manual_grounding/candidates/<row_id>/``.

Hard rules enforced here:

- Rows with ``coverage_status == "active_grounded"`` are refused.
  Active grounding is owned by ``stay_manual_grounding_2026_05.json``;
  this script never writes there.
- Rows with ``coverage_status == "unsupported"`` are refused.
- Generation requires ``pdftotext`` (poppler-utils). If it is missing,
  the script exits non-zero with install instructions. **It never
  writes a candidate based on a guess.**
- If the visa section or the printed page footer cannot be located in
  the extracted text, the script writes nothing and exits non-zero.
- If the ``제출서류`` block cannot be extracted verbatim, the script
  writes nothing and exits non-zero. **Document lists are never
  fabricated.**
- Generated candidates always have ``candidate_status == "draft"``,
  ``source_verification_status == "machine_extracted"``, and
  ``source_confidence == "low"``. Promotion to ``verified_locally`` or
  ``verified_candidate`` is a human reviewer task.
- The active fixture is never touched.
- The coverage matrix is never touched. A reviewer must update the
  row's ``coverage_status`` to ``candidate_only`` in a follow-up PR
  after the candidate is reviewed.

Exit codes:

- 0 — candidate written (or --dry-run preview emitted).
- 1 — generation failed for a tractable reason (no source section
  found, document list unclear, target already exists, etc.).
- 2 — invocation error (bad row id, refused coverage status, missing
  pdftotext, etc.).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MATRIX_PATH = os.path.join(
    REPO_ROOT, "backend", "data", "eval", "paradiso_coverage_matrix.json"
)
DEFAULT_MANUAL = os.path.join(
    REPO_ROOT, "docs", "source-manuals", "2026-06", "stay_manual_2026_06_01.pdf"
)
DEFAULT_OUT_DIR = os.path.join(
    REPO_ROOT, "backend", "data", "manual_grounding", "candidates"
)
SOURCE_TITLE = "외국인체류 안내매뉴얼"
SOURCE_DATE = "2026.5"
SOURCE_REVISION_DATE = "2026-06-01"
ISSUING_BODY = "법무부 출입국·외국인정책본부"

_REFUSED_COVERAGE_STATUSES = {"active_grounded", "unsupported"}
_ELIGIBLE_COVERAGE_STATUSES = {
    "source_needed",
    "clarification_needed",
    "scoped_fallback",
    "candidate_only",
}

# Map visa codes to the Korean header strings used in the stay manual.
# Only entries we have actually seen in the committed PDF are listed.
# Anything outside this map falls back to a generic "(<code>)" search.
_VISA_HEADERS_KO: Dict[str, Tuple[str, ...]] = {
    "D-2": ("유학(D-2)",),
    "D-4": ("일반연수(D-4)",),
    "D-10": ("구직(D-10)",),
    "E-7": ("특정활동(E-7)",),
    "F-1": ("방문동거(F-1)",),
    "F-2": ("거주(F-2)",),
    "F-5": ("영주(F-5)",),
    "F-6": ("결혼이민(F-6)",),
}

# Procedure-type Korean signals. These are not used to fabricate
# content — only to disambiguate which subsection the script targets
# inside a visa chapter.
_PROCEDURE_SIGNALS_KO: Dict[str, Tuple[str, ...]] = {
    "체류기간 연장허가": ("체류기간 연장허가",),
    "marriage_divorce_status_change": (
        "이혼", "혼인단절", "혼인 단절",
    ),
    "근무처 변경·추가 신고/허가": ("근무처 변경", "근무처 추가"),
    "체류지 변경신고": ("체류지 변경", "주소 변경"),
    "여권정보 변경신고": ("여권", "여권 정보", "여권정보"),
    "외국인등록": ("외국인등록",),
    "체류자격 변경허가": ("체류자격 변경",),
    "체류자격외 활동허가": ("체류자격외 활동",),
    "permanent_residence_card_renewal": ("영주증", "영주 카드"),
    "academic_status_change": ("휴학", "졸업", "수료"),
}

_PAGE_FOOTER_RE = re.compile(r"-\s*(\d+)\s*-")
# Match a ❍ / ① ② … / 가. 나. 다. block under a "제출서류" heading.
_SUBMISSION_HEADING_RE = re.compile(r"제출서류|제 출 서 류")

# Character-position threshold used to distinguish chapter-title pages from
# table-of-contents and cross-reference pages when locating a visa section.
# A chapter title page has the visa code in the very first characters of the
# pdftotext -layout output (e.g. "구 직(D-10)\n❍ ..."). Cross-references and
# TOC entries embed the code in a sentence that starts much later.
_CHAPTER_TITLE_MAX_OFFSET = 50


# ---------------------------------------------------------------------------
# Matrix
# ---------------------------------------------------------------------------


def _load_matrix() -> Dict[str, Any]:
    if not os.path.isfile(MATRIX_PATH):
        raise SystemExit(
            f"ERROR: coverage matrix not found at {MATRIX_PATH!r}. "
            "Run from a repo where PR #60 has been merged."
        )
    with open(MATRIX_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _find_row(matrix: Dict[str, Any], row_id: str) -> Optional[Dict[str, Any]]:
    for row in matrix.get("rows", []):
        if isinstance(row, dict) and row.get("id") == row_id:
            return row
    return None


# ---------------------------------------------------------------------------
# PDF extraction
# ---------------------------------------------------------------------------


def _require_pdftotext() -> str:
    path = shutil.which("pdftotext")
    if not path:
        print(
            "ERROR: pdftotext is required but was not found on PATH.\n"
            "       Install poppler-utils:\n"
            "         macOS:   brew install poppler\n"
            "         Debian:  sudo apt-get install -y poppler-utils\n"
            "       Then re-run this script.\n"
            "       The script will not fabricate page numbers or document "
            "lists from a guess.",
            file=sys.stderr,
        )
        raise SystemExit(2)
    return path


def _pdftotext_full(pdf_path: str) -> str:
    """Run pdftotext -layout over the whole PDF and return text."""
    _require_pdftotext()
    if not os.path.isfile(pdf_path):
        raise SystemExit(f"ERROR: PDF not found: {pdf_path!r}")
    result = subprocess.run(
        ["pdftotext", "-layout", pdf_path, "-"],
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        raise SystemExit(
            f"ERROR: pdftotext failed (exit {result.returncode}): "
            f"{result.stderr.decode('utf-8', 'replace')[:500]}"
        )
    return result.stdout.decode("utf-8", "replace")


def _pdftotext_page(pdf_path: str, page: int) -> str:
    """Re-extract a single PDF page to confirm the footer marker."""
    _require_pdftotext()
    result = subprocess.run(
        [
            "pdftotext",
            "-layout",
            "-f",
            str(page),
            "-l",
            str(page),
            pdf_path,
            "-",
        ],
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        raise SystemExit(
            f"ERROR: pdftotext page extraction failed (exit "
            f"{result.returncode})"
        )
    return result.stdout.decode("utf-8", "replace")


# ---------------------------------------------------------------------------
# Search & extraction logic
# ---------------------------------------------------------------------------


def _split_pages(full_text: str) -> List[str]:
    """Split pdftotext output on form-feed (one chunk per PDF page)."""
    return full_text.split("\f")


def _visa_header_candidates(row: Dict[str, Any]) -> List[str]:
    code = row.get("visa_code") or ""
    sub = row.get("visa_sub_code") or ""
    headers: List[str] = []
    if code in _VISA_HEADERS_KO:
        headers.extend(_VISA_HEADERS_KO[code])
    if code and code != "*":
        headers.append(f"({code})")
    if sub:
        headers.append(f"({sub})")
    return headers


def _procedure_signals(row: Dict[str, Any]) -> List[str]:
    proc = row.get("procedure_type") or ""
    signals: List[str] = []
    if proc in _PROCEDURE_SIGNALS_KO:
        signals.extend(_PROCEDURE_SIGNALS_KO[proc])
    if proc and proc not in signals and not _is_internal_token(proc):
        signals.append(proc)
    return signals


def _is_internal_token(s: str) -> bool:
    """True if the string looks like an internal english_underscore token."""
    return bool(s) and all(c.isascii() for c in s) and "_" in s


def _header_at_chapter_position(page_text: str, visa_headers: List[str]) -> bool:
    """Return True when any visa header appears near the top of the page.

    A chapter-title page in the stay manual starts with the visa category
    name (e.g. "구 직(D-10)") in the very first characters of the
    pdftotext -layout output.  Table-of-contents lines and cross-reference
    sentences embed the same code much later (typical offset > 100 chars).

    Using a threshold of _CHAPTER_TITLE_MAX_OFFSET (50 chars) reliably
    distinguishes chapter openings from TOC entries and cross-references,
    without requiring any knowledge of the overall chapter count or visa
    code inventory.
    """
    for h in visa_headers:
        pos = page_text.find(h)
        if pos != -1 and pos < _CHAPTER_TITLE_MAX_OFFSET:
            return True
    return False


def _locate_page(
    pages: List[str],
    visa_headers: List[str],
    procedure_signals: List[str],
) -> Optional[Tuple[int, int]]:
    """Locate (pdf_page_index, printed_page_number) for the candidate.

    pdf_page_index is 1-based to match pdftotext -f.
    Returns None when the section cannot be unambiguously located.
    """
    # Find the first page whose visa header appears in chapter-title position.
    # This skips table-of-contents lines and cross-reference sentences where
    # the same visa code is mentioned later in the text (see
    # _header_at_chapter_position for the heuristic).
    section_start: Optional[int] = None
    for i, page_text in enumerate(pages, start=1):
        if _header_at_chapter_position(page_text, visa_headers):
            section_start = i
            break
    if section_start is None:
        return None

    # Search forward within a reasonable window for a page that
    # contains BOTH a procedure signal AND a 제출서류 heading.
    window_end = min(len(pages), section_start + 80)
    best: Optional[int] = None
    for i in range(section_start, window_end + 1):
        page_text = pages[i - 1]
        if not _SUBMISSION_HEADING_RE.search(page_text):
            continue
        if procedure_signals and not any(s in page_text for s in procedure_signals):
            continue
        # First hit wins; do not silently pick later occurrences.
        best = i
        break

    if best is None:
        return None

    footer_match = _PAGE_FOOTER_RE.search(pages[best - 1])
    if not footer_match:
        return None
    return best, int(footer_match.group(1))


def _extract_submission_block(page_text: str) -> Optional[Tuple[str, List[str]]]:
    """Pull the verbatim 제출서류 block + a clean bullet list.

    Returns (verbatim_excerpt, bullet_list) or None when the block
    cannot be cleanly parsed. The bullet list is built only from
    lines that begin with a recognised manual-style bullet marker;
    free-text paragraphs are never converted into bullets.
    """
    heading_match = _SUBMISSION_HEADING_RE.search(page_text)
    if not heading_match:
        return None
    start = heading_match.start()
    tail = page_text[start:]

    # Stop at the next 제 ... lettered heading (e.g. "라.", "마.") or
    # the next big section header. Conservative: stop on first blank
    # double-newline after we have collected at least one bullet, or on
    # a printed page footer.
    bullets: List[str] = []
    excerpt_lines: List[str] = []
    bullet_re = re.compile(r"^\s*(?:[①-⑳]|❍|[가-힣]\.|\d+\.|⑴|⑵|⑶|⑷|⑸|⑹|⑺|⑻|⑼|⑽|[a-z]\.)\s+(.+)$")
    stop_re = re.compile(r"^\s*(?:[가-힣]\.\s|특\s?칙|확인사항|기본원칙|허가요건)")

    for line in tail.splitlines():
        excerpt_lines.append(line)
        if _PAGE_FOOTER_RE.fullmatch(line.strip()):
            break
        if bullets and stop_re.match(line) and "제출서류" not in line:
            break
        bm = bullet_re.match(line)
        if bm:
            bullets.append(bm.group(1).strip())

    if not bullets:
        return None
    excerpt = "\n".join(excerpt_lines).rstrip()
    return excerpt, bullets


def _extract_section_header(page_text: str) -> str:
    """Pull the most-specific visible section header from the page.

    Picks a header line that contains visa context (e.g. "유학(D-2)").
    Falls back to the first non-empty stripped line.
    """
    for line in page_text.splitlines():
        s = line.strip()
        if not s:
            continue
        if "(" in s and ")" in s and re.search(r"[A-Z]-\d", s):
            return s[:200]
    for line in page_text.splitlines():
        s = line.strip()
        if s:
            return s[:200]
    return ""


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def _build_candidate(
    row: Dict[str, Any],
    *,
    section_label: str,
    printed_page: int,
    excerpt: str,
    bullets: List[str],
    source_file_rel: str,
    pdftotext_path: str,
) -> Dict[str, Any]:
    visa_code = row.get("visa_code") or ""
    visa_sub_code = row.get("visa_sub_code")
    procedure_type = row.get("procedure_type") or ""
    scenario = row.get("scenario")

    verification_note = (
        f"Machine-extracted by scripts/generate_candidate_from_matrix.py "
        f"using {pdftotext_path} against {source_file_rel} for matrix row "
        f"{row.get('id')!r}. Candidate page identified as PDF printed "
        f"page {printed_page}. This is a MACHINE EXTRACT ONLY: a human "
        f"reviewer must re-verify the page number, the section header, "
        f"the verbatim 제출서류 list, and the scope (sub-code / scenario) "
        f"before this candidate can be promoted to verified_candidate or "
        f"used as active grounding."
    )

    candidate: Dict[str, Any] = {
        "candidate_status": "draft",
        "visa_code": visa_code,
        "visa_sub_code": visa_sub_code,
        "sub_codes_covered": None,
        "scenario": scenario,
        "scenarios_covered": None,
        "requires_clarification_when_missing_subcode": bool(
            row.get("requires_subcode") or row.get("requires_scenario")
        ),
        "procedure_type": procedure_type,
        "section": section_label,
        "page_range": str(printed_page),
        "source_file": source_file_rel,
        "source_title": SOURCE_TITLE,
        "source_date": SOURCE_DATE,
        "source_revision_date": SOURCE_REVISION_DATE,
        "issuing_body": ISSUING_BODY,
        "source_verification_status": "machine_extracted",
        "source_confidence": "low",
        "verification_note": verification_note,
        "required_documents": bullets,
        "source_excerpt": excerpt,
        "caveats": [
            "본 후보(candidate)는 기계 추출(machine_extracted) 결과이며, "
            "활성 grounding 항목이 아닙니다. /api/ask 응답에 사용되지 않습니다.",
            "본 후보의 제출서류 목록과 페이지 번호는 한국 이민·체류 도메인 "
            "전문가의 재검증을 거친 후에야 promote 대상이 될 수 있습니다.",
            "관할 출입국·외국인청/사무소/출장소는 개별 사안에 따라 제출서류를 "
            "추가하거나 일부 면제할 수 있습니다.",
            "본 응답은 매뉴얼 본문의 기계 추출이며, 최종 허가 여부와 심사기준은 "
            "관할 출입국·외국인관서의 판단에 따릅니다.",
        ],
        "risk_notes": [
            "human_review_required: machine extraction can mis-route across "
            "neighbouring subsections (different sub-code, different "
            "scenario, different 제출서류 list). The reviewer must confirm "
            "that the extracted block matches the row's expected sub-code "
            "and scenario.",
            "human_review_required: the page footer match used to set "
            "page_range is a heuristic. The reviewer must re-run "
            "`pdftotext -layout -f N -l N` on the cited page and confirm "
            "both the footer and the section header by eye before "
            "promotion.",
            "human_review_required: 제출서류 bullets were parsed by regex. "
            "Multi-line bullet continuations, inline parentheticals, and "
            "neighbouring 특칙 boxes may have been dropped or merged.",
        ],
        "human_review": {
            "decision": "pending",
            "reviewer": "",
            "reviewed_at": "",
        },
    }
    return candidate


def _build_review_md(row: Dict[str, Any], candidate: Dict[str, Any]) -> str:
    rid = row.get("id")
    visa_code = row.get("visa_code") or ""
    visa_sub_code = row.get("visa_sub_code") or "(none)"
    procedure_type = row.get("procedure_type") or ""
    scenario = row.get("scenario") or "(none)"
    page = candidate.get("page_range")
    source_file = candidate.get("source_file")

    return f"""# REVIEW — {rid}

> **Candidate status:** `draft` (machine_extracted).
> **Not active grounding.** Nothing in this folder is read by `/api/ask`.
> Human domain-expert sign-off is required before any consideration of
> promotion. `human_review.decision` is `"pending"`.

## 1. Provenance

- Generated by `scripts/generate_candidate_from_matrix.py`.
- Matrix row id: `{rid}`.
- Source file: `{source_file}`.
- Candidate printed page: `{page}`.
- Extraction tool: `pdftotext -layout` (poppler-utils).

## 2. Reviewer checklist

A reviewer MUST do all of the following before this candidate can be
considered for promotion. Until every box is checked, the candidate
stays `draft` and `source_verification_status` stays
`machine_extracted`.

- [ ] Re-run `pdftotext -layout -f {page} -l {page} {source_file}` and
      confirm the printed page footer matches `- {page} -`.
- [ ] Confirm the section header reported in `candidate.json` is the
      correct subsection for visa `{visa_code}` / sub-code
      `{visa_sub_code}` / scenario `{scenario}` / procedure
      `{procedure_type}`.
- [ ] Confirm every entry in `required_documents` appears verbatim on
      the cited page. Reject the candidate if any bullet was
      mis-parsed, merged across rows, or dropped a parenthetical.
- [ ] Confirm no document from a neighbouring sub-code or scenario
      leaked into the list.
- [ ] If any `claim_to_verify` or legal-interpretation question remains
      open, leave the candidate as `draft` and document the open
      question here.

## 3. Promotion gate

Promotion requires a separate, reviewer-authored PR that:

1. Changes `candidate_status` to `verified_candidate`.
2. Changes `source_verification_status` to `verified_locally`.
3. Fills in `human_review.decision = "approved"` with a non-empty
   `reviewer` and an ISO-8601 `reviewed_at`.
4. Adds the entry to
   `backend/data/manual_grounding/stay_manual_grounding_2026_05.json`
   via `scripts/promote_grounding_candidate.py`.

This generator script does none of those things and never will.

## 4. What this script did NOT do

- It did NOT modify
  `backend/data/manual_grounding/stay_manual_grounding_2026_05.json`.
- It did NOT modify `backend/data/eval/paradiso_coverage_matrix.json`.
- It did NOT promote this candidate.
- It did NOT make any HTTP request.
- It did NOT fabricate the document list — every bullet was parsed
  from the cited PDF page or generation would have failed.
"""


def _write_outputs(
    *,
    row: Dict[str, Any],
    out_dir: str,
    candidate: Dict[str, Any],
    review_md: str,
    dry_run: bool,
) -> str:
    rid = row.get("id")
    target_dir = os.path.join(out_dir, str(rid))
    candidate_path = os.path.join(target_dir, "candidate.json")
    review_path = os.path.join(target_dir, "REVIEW.md")

    if dry_run:
        print(f"[dry-run] would create: {candidate_path}")
        print(f"[dry-run] would create: {review_path}")
        print("[dry-run] candidate preview:")
        print(json.dumps(candidate, ensure_ascii=False, indent=2))
        return target_dir

    if os.path.isdir(target_dir):
        raise SystemExit(
            f"ERROR: target directory already exists: {target_dir!r}. "
            "Refusing to overwrite. Remove it manually or pick a "
            "different --row-id."
        )

    os.makedirs(target_dir, exist_ok=False)
    with open(candidate_path, "w", encoding="utf-8") as fh:
        json.dump(candidate, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    with open(review_path, "w", encoding="utf-8") as fh:
        fh.write(review_md)
    return target_dir


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: Optional[List[str]]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Generate a draft manual-grounding candidate folder for a "
            "matrix row. Never modifies active grounding."
        )
    )
    p.add_argument("--row-id", required=True, help="matrix row id")
    p.add_argument(
        "--manual",
        default=DEFAULT_MANUAL,
        help="path to the committed source manual PDF "
        "(default: %(default)s)",
    )
    p.add_argument(
        "--out-dir",
        default=DEFAULT_OUT_DIR,
        help="candidates directory root (default: %(default)s)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="print what would be written; do not write files",
    )
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = _parse_args(argv)

    matrix = _load_matrix()
    row = _find_row(matrix, args.row_id)
    if row is None:
        print(
            f"ERROR: row id {args.row_id!r} not found in coverage matrix "
            f"({os.path.relpath(MATRIX_PATH, REPO_ROOT)}).",
            file=sys.stderr,
        )
        return 2

    coverage_status = row.get("coverage_status")
    if coverage_status in _REFUSED_COVERAGE_STATUSES:
        print(
            f"ERROR: row {args.row_id!r} has coverage_status="
            f"{coverage_status!r}; this script refuses to generate "
            "candidates for active or unsupported rows.",
            file=sys.stderr,
        )
        return 2
    if coverage_status not in _ELIGIBLE_COVERAGE_STATUSES:
        print(
            f"ERROR: row {args.row_id!r} has coverage_status="
            f"{coverage_status!r}; allowed values are "
            f"{sorted(_ELIGIBLE_COVERAGE_STATUSES)}.",
            file=sys.stderr,
        )
        return 2

    existing_ref = row.get("candidate_ref")
    if isinstance(existing_ref, str) and existing_ref.strip():
        abs_ref = (
            existing_ref
            if os.path.isabs(existing_ref)
            else os.path.join(REPO_ROOT, existing_ref)
        )
        if os.path.isfile(abs_ref):
            print(
                f"ERROR: row {args.row_id!r} already has candidate_ref="
                f"{existing_ref!r} on disk. Refusing to generate a "
                "second candidate for the same row in this PR. A "
                "reviewer must reconcile the existing candidate first.",
                file=sys.stderr,
            )
            return 2

    pdftotext_path = _require_pdftotext()
    pdf_path = (
        args.manual
        if os.path.isabs(args.manual)
        else os.path.join(REPO_ROOT, args.manual)
    )
    if not os.path.isfile(pdf_path):
        print(f"ERROR: manual PDF not found: {pdf_path!r}", file=sys.stderr)
        return 2

    print(f"[info] extracting {os.path.relpath(pdf_path, REPO_ROOT)} ...")
    full_text = _pdftotext_full(pdf_path)
    pages = _split_pages(full_text)

    visa_headers = _visa_header_candidates(row)
    procedure_signals = _procedure_signals(row)
    if not visa_headers:
        print(
            f"ERROR: row {args.row_id!r} has no resolvable Korean visa "
            "header (visa_code may be '*' or unknown). Cross-status "
            "procedures need a manual page hint; pass a more specific "
            "row.",
            file=sys.stderr,
        )
        return 1

    located = _locate_page(pages, visa_headers, procedure_signals)
    if located is None:
        print(
            f"ERROR: could not locate a candidate page in "
            f"{os.path.relpath(pdf_path, REPO_ROOT)} for row "
            f"{args.row_id!r}.\n"
            f"       Searched visa headers: {visa_headers}\n"
            f"       Searched procedure signals: {procedure_signals}\n"
            "       Refusing to write a candidate based on a guess.",
            file=sys.stderr,
        )
        return 1
    pdf_page_idx, printed_page = located

    page_text = pages[pdf_page_idx - 1]
    extracted = _extract_submission_block(page_text)
    if extracted is None:
        print(
            f"ERROR: located visa section at PDF page {pdf_page_idx} "
            f"(printed {printed_page}) but could not extract a clean "
            "verbatim 제출서류 bullet list. Refusing to fabricate one.",
            file=sys.stderr,
        )
        return 1
    excerpt, bullets = extracted

    section_label = _extract_section_header(page_text)
    visa_code_for_label = row.get("visa_code") or ""
    if (
        visa_code_for_label
        and visa_code_for_label != "*"
        and visa_code_for_label not in section_label
    ):
        section_label = f"{visa_code_for_label} — {section_label}".rstrip(" —")
    source_file_rel = os.path.relpath(pdf_path, REPO_ROOT)

    candidate = _build_candidate(
        row,
        section_label=section_label,
        printed_page=printed_page,
        excerpt=excerpt,
        bullets=bullets,
        source_file_rel=source_file_rel,
        pdftotext_path=pdftotext_path,
    )
    review_md = _build_review_md(row, candidate)

    target_dir = _write_outputs(
        row=row,
        out_dir=args.out_dir,
        candidate=candidate,
        review_md=review_md,
        dry_run=args.dry_run,
    )

    if args.dry_run:
        print("[dry-run] no files were written.")
    else:
        print(
            f"OK: draft candidate written under "
            f"{os.path.relpath(target_dir, REPO_ROOT)}/."
        )
        print(
            "     Next step: run "
            "`python3 scripts/validate_manual_grounding_candidate.py` and "
            "have a Korean immigration domain reviewer fill in REVIEW.md."
        )
        print(
            "     This script did NOT modify active grounding, the "
            "coverage matrix, or any production code path."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
