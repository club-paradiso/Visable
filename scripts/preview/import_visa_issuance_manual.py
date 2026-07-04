#!/usr/bin/env python3
"""PreView by Paradiso — visa issuance manual importer (manual/offline data prep).

Accepts a local HWP / HWPX / DOCX / TXT Korean visa issuance manual file,
extracts text where possible, and normalizes MINIMAL reference data into:

    data/preview/visa-issuance-manual.snapshot.json

plus an audit report:

    audits/preview/visa-issuance-manual-import-report.md

Boundaries (do not weaken):
- This is a manual/offline data-preparation script. It is NEVER called by
  preview.html at runtime.
- The manual is a baseline REFERENCE layer for PreView, not its main source.
- Extraction is deterministic and minimal: per visa code we record only the
  actual heading line found in the manual and which issuance-route marker
  phrases appear near it. We never auto-summarize legal requirements and we
  never emit long verbatim dumps.
- If extraction fails (distribution-protected HWP, missing tools, unreadable
  input), we do NOT fake manual contents: we write a clear report, keep any
  existing snapshot untouched, and PreView keeps working without the manual
  layer.

Extraction strategy order (documented in the report):
1. dedicated HWP extraction skill/tool        -> not available in this repo
2. HWP -> DOCX conversion skill/tool          -> not available in this repo
3. pyhwp / hwp5txt CLI                        -> used if installed
4. LibreOffice soffice --convert-to txt       -> used if installed
5. user-provided converted DOCX/TXT fallback  -> always supported

Usage:
    python3 scripts/preview/import_visa_issuance_manual.py <manual-file> \
        [--codes C-3,C-4,D-2,D-4] [--snapshot PATH] [--report PATH]
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from xml.etree import ElementTree

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SNAPSHOT = REPO_ROOT / "data" / "preview" / "visa-issuance-manual.snapshot.json"
DEFAULT_REPORT = REPO_ROOT / "audits" / "preview" / "visa-issuance-manual-import-report.md"

# Parent codes only (subcodes stay under their parents; PreView never
# flattens subcode rules into parent-level claims).
DEFAULT_CODES = ["C-3", "C-4", "D-2", "D-4"]

PURPOSE_BY_CODE = {
    "C-3": "short_visit",
    "C-4": "business",
    "D-2": "study",
    "D-4": "study",
}

# Standalone heading lines in the readable manual exports look like
# "유 학(D-2)" / "단기취업(C-4)" / "단기방문(C-3)해당자 및 활동범위".
HEADING_RE = re.compile(
    r"^\s*([가-힣][가-힣\s·]{0,20})\(([A-H]-\d{1,2})\)(.{0,40})$"
)
PAGE_MARKER_RE = re.compile(r"=====\s*(.+?)\s*/\s*PDF page\s+(\d+)\s+of\s+\d+\s*=====")
VERSION_RE = re.compile(r"안내매뉴얼\s*(\d{4}\.\s*\d{1,2})")

# Issuance-route marker phrases: we only report WHICH of these literally
# appear in the code's manual section. No interpretation, no summarizing.
ROUTE_MARKERS = [
    ("공관장 재량", "공관장 재량 발급 관련 절"),
    ("사증발급인정서", "사증발급인정서 관련 절"),
    ("전자사증", "전자사증 관련 절"),
    ("첨부서류", "첨부서류 절"),
    ("제출서류", "제출서류 절"),
]

MAX_HEADING_CHARS = 120
MAX_SUMMARY_CHARS = 300
SECTION_SCAN_LINES = 40

STANDARD_NOTES_KO = (
    "공관별 접수 방식과 추가 제출서류는 관할 재외공관 공식 안내 확인 필요"
)


def _read_text_file(path: Path) -> Tuple[Optional[str], str]:
    raw = path.read_bytes()
    for encoding in ("utf-8", "cp949", "euc-kr"):
        try:
            return raw.decode(encoding), f"text_read_{encoding}"
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace"), "text_read_utf8_lossy"


def _extract_docx(path: Path) -> Tuple[Optional[str], str]:
    try:
        with zipfile.ZipFile(path) as archive:
            with archive.open("word/document.xml") as handle:
                tree = ElementTree.parse(handle)
    except Exception as exc:  # noqa: BLE001
        return None, f"docx_read_failed: {type(exc).__name__}"
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    lines: List[str] = []
    for paragraph in tree.iter(f"{{{ns['w']}}}p"):
        texts = [node.text or "" for node in paragraph.iter(f"{{{ns['w']}}}t")]
        line = "".join(texts).strip()
        if line:
            lines.append(line)
    if not lines:
        return None, "docx_no_text"
    return "\n".join(lines), "docx_stdlib_zipfile"


def _extract_hwpx(path: Path) -> Tuple[Optional[str], str]:
    try:
        with zipfile.ZipFile(path) as archive:
            names = sorted(
                n for n in archive.namelist()
                if re.match(r"Contents/section\d+\.xml$", n)
            )
            manifest = ""
            if "META-INF/manifest.xml" in archive.namelist():
                manifest = archive.read("META-INF/manifest.xml").decode("utf-8", "replace")
            if "encryption-data" in manifest:
                return None, "hwpx_sections_encrypted"
            lines: List[str] = []
            for name in names:
                try:
                    tree = ElementTree.fromstring(archive.read(name))
                except ElementTree.ParseError:
                    continue
                for node in tree.iter():
                    tag = node.tag.rsplit("}", 1)[-1]
                    if tag == "t" and node.text:
                        lines.append(node.text.strip())
    except Exception as exc:  # noqa: BLE001
        return None, f"hwpx_read_failed: {type(exc).__name__}"
    text = "\n".join(line for line in lines if line)
    if not text:
        return None, "hwpx_no_text"
    return text, "hwpx_stdlib_zipfile"


def _extract_hwp(path: Path, tool_log: List[str]) -> Tuple[Optional[str], str]:
    hwp5txt = shutil.which("hwp5txt")
    if hwp5txt:
        try:
            result = subprocess.run(
                [hwp5txt, str(path)], capture_output=True, timeout=180, check=False
            )
            if result.returncode == 0 and result.stdout:
                return result.stdout.decode("utf-8", "replace"), "hwp5txt_cli"
            tool_log.append(f"hwp5txt exited {result.returncode}")
        except Exception as exc:  # noqa: BLE001
            tool_log.append(f"hwp5txt failed: {type(exc).__name__}")
    else:
        tool_log.append("hwp5txt (pyhwp) not installed")

    soffice = shutil.which("soffice")
    if soffice:
        with tempfile.TemporaryDirectory(prefix="preview-hwp-") as tmp:
            try:
                result = subprocess.run(
                    [
                        soffice, "--headless", "--norestore",
                        f"-env:UserInstallation=file://{tmp}/lo-profile",
                        "--convert-to", "txt:Text (encoded):UTF8",
                        "--outdir", tmp, str(path),
                    ],
                    capture_output=True, timeout=300, check=False,
                )
                converted = Path(tmp) / (path.stem + ".txt")
                if converted.exists():
                    text, _ = _read_text_file(converted)
                    if text and len(text.strip()) > 500:
                        return text, "soffice_convert_to_txt"
                    tool_log.append("soffice produced a stub (<500 chars) — likely distribution-protected HWP")
                else:
                    tool_log.append(f"soffice exited {result.returncode} without output")
            except Exception as exc:  # noqa: BLE001
                tool_log.append(f"soffice failed: {type(exc).__name__}")
    else:
        tool_log.append("soffice (LibreOffice) not installed")
    return None, "hwp_extraction_blocked"


def extract_text(path: Path, tool_log: List[str]) -> Tuple[Optional[str], str]:
    suffix = path.suffix.lower()
    tool_log.append("dedicated HWP extraction skill: not available in this repo")
    tool_log.append("HWP->DOCX conversion skill: not available in this repo")
    if suffix == ".txt":
        return _read_text_file(path)
    if suffix == ".docx":
        return _extract_docx(path)
    if suffix == ".hwpx":
        return _extract_hwpx(path)
    if suffix == ".hwp":
        return _extract_hwp(path, tool_log)
    return None, f"unsupported_extension_{suffix or 'none'}"


def korean_ratio(text: str) -> float:
    if not text:
        return 0.0
    korean = sum(1 for ch in text if "가" <= ch <= "힣")
    return korean / max(len(text), 1)


def detect_version(text: str) -> str:
    match = VERSION_RE.search(text[:4000])
    if match:
        return match.group(1).replace(" ", "")
    return "unknown"


def build_records(text: str, codes: List[str]) -> List[Dict[str, object]]:
    lines = text.splitlines()
    page = None
    # Track the page number of the most recent page marker before each line.
    pages: List[Optional[int]] = []
    for line in lines:
        marker = PAGE_MARKER_RE.search(line)
        if marker:
            page = int(marker.group(2))
        pages.append(page)

    wanted = set(codes)
    records: List[Dict[str, object]] = []
    seen: set = set()
    for index, line in enumerate(lines):
        match = HEADING_RE.match(line.strip())
        if not match:
            continue
        name, code, _tail = match.groups()
        if code not in wanted or code in seen:
            continue
        # Skip table-of-contents hits: TOC lines contain many codes at once.
        if len(re.findall(r"\([A-H]-\d", line)) > 2:
            continue
        seen.add(code)
        heading = re.sub(r"\s+", "", name) + f"({code})"
        section = "\n".join(lines[index: index + SECTION_SCAN_LINES])
        found_markers = [label for marker, label in ROUTE_MARKERS if marker in section]
        if found_markers:
            summary = (
                "매뉴얼 해당 절에서 확인된 발급 경로 단서: "
                + ", ".join(found_markers)
                + " — 적용 대상과 세부 요건은 매뉴얼 원문과 관할 재외공관 공식 안내 확인 필요"
            )
        else:
            summary = "발급 경로 요약은 자동 추출하지 않았습니다. 매뉴얼 원문 확인 필요"
        records.append(
            {
                "code": code,
                "purposeCategory": PURPOSE_BY_CODE.get(code, "not_sure"),
                "headingKo": heading[:MAX_HEADING_CHARS],
                "issuanceRouteSummaryKo": summary[:MAX_SUMMARY_CHARS],
                "evidenceLevel": "manual_reference",
                "requiresOfficialMissionCheck": True,
                "sourcePointer": {
                    "page": pages[index],
                    "section": heading[:MAX_HEADING_CHARS],
                },
                "notesKo": STANDARD_NOTES_KO,
            }
        )
    records.sort(key=lambda record: codes.index(str(record["code"])))
    return records


def write_report(
    report_path: Path,
    source: Path,
    method: str,
    tool_log: List[str],
    status: str,
    records: List[Dict[str, object]],
    text_stats: Dict[str, object],
    snapshot_path: Path,
    snapshot_written: bool,
) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# PreView 사증발급 매뉴얼 임포트 감사 보고서 — {time.strftime('%Y-%m-%d')}",
        "",
        "> 범위 한정: 이 보고서는 PreView의 '매뉴얼 기준 참고' 레이어를 위한 최소 추출 기록이다. "
        "법적 정확성 전수 재검증이 아니며, 매뉴얼은 PreView의 주 소스가 아니라 참고 레이어다. "
        "면책·주의·출처 경고 문구는 어떤 단계에서도 약화하지 않는다.",
        "",
        "## 입력",
        f"- 입력 파일: `{source}`",
        f"- 추출 방법: `{method}`",
        f"- 상태: **{status}**",
        "",
        "## 도구 가용성 로그",
    ]
    lines += [f"- {entry}" for entry in tool_log]
    lines += [
        "",
        "## 추출 통계",
        f"- 텍스트 길이: {text_stats.get('chars', 0):,} chars",
        f"- 한글 비율: {text_stats.get('koreanRatio', 0):.3f}",
        f"- 감지된 매뉴얼 버전: {text_stats.get('version', 'unknown')}",
        "",
        "## 생성 레코드",
        "",
    ]
    if records:
        lines.append("| code | purposeCategory | headingKo | page | 발급 경로 단서 |")
        lines.append("|---|---|---|---|---|")
        for record in records:
            pointer = record.get("sourcePointer") or {}
            lines.append(
                "| {code} | {purpose} | {heading} | {page} | {summary} |".format(
                    code=record.get("code"),
                    purpose=record.get("purposeCategory"),
                    heading=record.get("headingKo"),
                    page=(pointer.get("page") if isinstance(pointer, dict) else None) or "-",
                    summary=str(record.get("issuanceRouteSummaryKo", ""))[:80],
                )
            )
    else:
        lines.append("(레코드 없음 — 추출 실패 또는 대상 코드 미발견. 매뉴얼 내용은 위조하지 않는다.)")
    lines += [
        "",
        "## 산출물",
        f"- 스냅샷: `{snapshot_path}` — {'기록됨' if snapshot_written else '기록되지 않음 (기존 파일 유지)'}",
        "",
        "## 경계 확인",
        "- 매뉴얼 원문 전체를 저장하지 않았다 (헤딩·경로 단서만 기록).",
        "- 요구서류 목록을 새로 만들지 않았다.",
        "- 모든 레코드는 `evidenceLevel: manual_reference`와 `requiresOfficialMissionCheck: true`를 갖는다.",
        "- 최종 판단은 관할 재외공관 공식 안내를 따른다 (공식 원문 확인 필요).",
        "",
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="HWP/HWPX/DOCX/TXT manual file path")
    parser.add_argument("--codes", default=",".join(DEFAULT_CODES))
    parser.add_argument("--snapshot", default=str(DEFAULT_SNAPSHOT))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    args = parser.parse_args()

    source = Path(args.input)
    snapshot_path = Path(args.snapshot)
    report_path = Path(args.report)
    codes = [code.strip().upper() for code in args.codes.split(",") if code.strip()]

    tool_log: List[str] = []
    if not source.exists():
        write_report(
            report_path, source, "none", tool_log + ["입력 파일이 존재하지 않음"],
            "failed_missing_input", [], {}, snapshot_path, False,
        )
        print(f"[import_visa_issuance_manual] input not found: {source}")
        print(f"[import_visa_issuance_manual] report written: {report_path}")
        return 0

    text, method = extract_text(source, tool_log)
    if not text or len(text.strip()) < 500:
        write_report(
            report_path, source, method, tool_log,
            "failed_extraction_blocked", [],
            {"chars": len(text or ""), "koreanRatio": korean_ratio(text or ""), "version": "unknown"},
            snapshot_path, False,
        )
        print("[import_visa_issuance_manual] extraction blocked/empty — no snapshot written")
        print(f"[import_visa_issuance_manual] report written: {report_path}")
        return 0

    ratio = korean_ratio(text)
    version = detect_version(text)
    records = build_records(text, codes)
    status = "ok" if records else "ok_no_target_codes_found"

    snapshot = {
        "schemaVersion": 1,
        "manualVersion": version,
        "importedAt": time.strftime("%Y-%m-%d"),
        "sourceFileName": source.name,
        "extractionMethod": method,
        "usageBoundaryKo": (
            "이 스냅샷은 PreView의 참고 레이어다. 사증발급 여부·요구서류·심사 결과의 근거가 아니며, "
            "최종 확인은 관할 재외공관 공식 안내를 따라야 한다."
        ),
        "records": records,
    }
    snapshot_written = False
    if records:
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot_path.write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        snapshot_written = True

    write_report(
        report_path, source, method, tool_log, status, records,
        {"chars": len(text), "koreanRatio": ratio, "version": version},
        snapshot_path, snapshot_written,
    )
    print(f"[import_visa_issuance_manual] status={status} records={len(records)}")
    print(f"[import_visa_issuance_manual] snapshot: {snapshot_path} written={snapshot_written}")
    print(f"[import_visa_issuance_manual] report:   {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
