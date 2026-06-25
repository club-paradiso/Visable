#!/usr/bin/env python3
"""Extract readable text from non-protected HWPX files, or emit diagnostics.

The official HiKorea manuals are often distribution/protected HWPX packages:
their manifest declares encrypted body entries and the section files are not
plain XML. This tool deliberately records that condition instead of treating
binary bytes as text.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

STATUS_RE = re.compile(r"\b(?:A|B|C|D|E|F|H)-\d+\b|\bG-\d+(?:-\d+)?\b")
SECTION_RE = re.compile(r"^Contents/section(\d+)\.xml$")


def local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag


def normalize(text: str) -> str:
    text = text.replace("\u00a0", " ")
    return re.sub(r"[ \t\r\f\v]+", " ", text).strip()


def natural_sections(names: list[str]) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    for name in names:
        match = SECTION_RE.match(name)
        if match:
            out.append((int(match.group(1)), name))
    return sorted(out)


def encrypted_entries(zf: zipfile.ZipFile) -> set[str]:
    try:
        manifest = zf.read("META-INF/manifest.xml")
    except KeyError:
        return set()
    try:
        root = ET.fromstring(manifest)
    except ET.ParseError:
        return set()
    encrypted: set[str] = set()
    for entry in root.iter():
        if local_name(entry.tag) != "file-entry":
            continue
        full_path = entry.attrib.get("full-path")
        if not full_path:
            continue
        if any(local_name(child.tag) == "encryption-data" for child in entry):
            encrypted.add(full_path)
    return encrypted


def xml_text(node: ET.Element) -> str:
    parts: list[str] = []

    def walk(el: ET.Element) -> None:
        name = local_name(el.tag)
        if el.text:
            parts.append(el.text)
        for child in el:
            walk(child)
            child_name = local_name(child.tag)
            if child_name in {"tc", "cell"}:
                parts.append(" | ")
            elif child_name in {"tr", "row"}:
                parts.append("\n")
            if child.tail:
                parts.append(child.tail)
        if name in {"br", "lineBreak"}:
            parts.append("\n")

    walk(node)
    return normalize("".join(parts))


def paragraph_nodes(root: ET.Element) -> list[ET.Element]:
    nodes = [el for el in root.iter() if local_name(el.tag) in {"p", "para", "paragraph"}]
    return nodes or [root]


def heading_candidates(text: str) -> list[str]:
    headings: list[str] = []
    for line in text.splitlines():
        line = normalize(line)
        if not line:
            continue
        if STATUS_RE.search(line) or re.match(r"^(?:제\s*\d+\s*[장절관]|[IVX]+\.|\d+\.)", line):
            if len(line) <= 120 and line not in headings:
                headings.append(line)
    return headings


def extract_hwpx(path: Path) -> list[dict]:
    records: list[dict] = []
    with zipfile.ZipFile(path) as zf:
        encrypted = encrypted_entries(zf)
        for section_index, source_file in natural_sections(zf.namelist()):
            data = zf.read(source_file)
            record = {
                "source_file": source_file,
                "section_index": section_index,
                "paragraphs": [],
                "headings_detected": [],
                "status_codes_detected": [],
            }
            stripped = data.lstrip()
            if source_file in encrypted:
                record["parse_error"] = "manifest marks this section as encrypted"
            elif not stripped.startswith(b"<"):
                record["parse_error"] = "section payload is not XML text"
            else:
                try:
                    root = ET.fromstring(data)
                except ET.ParseError as exc:
                    record["parse_error"] = f"XML parse error: {exc}"
                else:
                    for paragraph_index, node in enumerate(paragraph_nodes(root)):
                        text = xml_text(node)
                        codes = sorted(set(STATUS_RE.findall(text)))
                        if text:
                            record["paragraphs"].append(
                                {
                                    "paragraph_index": paragraph_index,
                                    "text": text,
                                    "status_codes_detected": codes,
                                }
                            )
                    joined = "\n".join(p["text"] for p in record["paragraphs"])
                    record["headings_detected"] = heading_candidates(joined)
                    record["status_codes_detected"] = sorted(set(STATUS_RE.findall(joined)))
            if not record["paragraphs"]:
                record["paragraphs"].append(
                    {
                        "paragraph_index": 0,
                        "text": "",
                        "status_codes_detected": [],
                    }
                )
            records.append(record)
    return records


def write_outputs(records: list[dict], txt_path: Path, md_path: Path, json_path: Path) -> None:
    txt_parts: list[str] = []
    md_parts: list[str] = ["# HWPX extraction diagnostics", ""]
    for record in records:
        title = f"{record['source_file']} (section {record['section_index']})"
        txt_parts.append(f"===== {title} =====")
        md_parts.append(f"## {title}")
        if record.get("parse_error"):
            msg = f"UNREADABLE: {record['parse_error']}"
            txt_parts.append(msg)
            md_parts.append(msg)
        for para in record["paragraphs"]:
            if para["text"]:
                txt_parts.append(para["text"])
                md_parts.append(para["text"])
        txt_parts.append("")
        md_parts.append("")

    txt_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    txt_path.write_text("\n".join(txt_parts), encoding="utf-8")
    md_path.write_text("\n".join(md_parts), encoding="utf-8")
    json_path.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--txt", type=Path, required=True)
    parser.add_argument("--md", type=Path, required=True)
    parser.add_argument("--json", type=Path, required=True)
    args = parser.parse_args(argv)

    if not args.input.exists():
        print(f"not found: {args.input}", file=sys.stderr)
        return 2
    records = extract_hwpx(args.input)
    write_outputs(records, args.txt, args.md, args.json)
    print(f"wrote {args.txt}, {args.md}, {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
