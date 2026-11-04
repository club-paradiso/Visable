"""Render a parsed Korean law version as a corpus Markdown document.

The Markdown is a faithful rendering of the official text: article
wording is never paraphrased, summarised or shortened. The header block
carries the provenance (official source, identifiers, dates, hashes,
verification status) so a reader can always trace the text back to the
National Law Information Center.
"""

from __future__ import annotations

from typing import Any, Dict, List


def _article_heading(article: Dict[str, Any]) -> str:
    num = article["articleNumber"]
    branch = article["branchNumber"]
    label = f"제{num}조" + (f"의{branch}" if branch else "")
    if article.get("titleKo"):
        label += f"({article['titleKo']})"
    return label


def render_korean_markdown(metadata: Dict[str, Any], parsed: Dict[str, Any], annexes: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    lines.append(f"# {metadata['titleKo']}")
    lines.append("")
    lines.append(f"- 법령 식별자 (법령ID / 법령일련번호): {metadata['lawId']} / {metadata['sourceIdentifier']}")
    lines.append(f"- 법령 종류: {metadata['lawType']} ({metadata.get('promulgationKindKo') or ''})")
    lines.append(f"- 공포: {metadata.get('promulgationDate') or '미확인'} (제{metadata.get('promulgationNo') or '?'}호, {metadata.get('revisionTypeKo') or ''})")
    lines.append(f"- 시행일: {metadata['effectiveFrom']}")
    lines.append(f"- 원문 출처: {metadata['sourceProvider']} — {metadata['sourceUrl']}")
    lines.append(f"- 수집일: {metadata['retrievedAt']}")
    lines.append(f"- 검증 상태: {metadata['verificationStatus']}")
    lines.append(f"- 본문 SHA-256 (구조화 조문 기준): {metadata['contentSha256']}")
    lines.append("")
    lines.append("> 한국어 원문이 법적 효력을 가집니다. 이 문서는 국가법령정보센터가 제공하는 공식 법령정보를 출처 표시와 함께 수록한 것으로, 원문을 의역하거나 축약하지 않았습니다.")
    lines.append("")

    section_by_article: Dict[str, List[str]] = {}
    for sec in parsed.get("sections", []):
        key = sec.get("beforeArticle") or "__start__"
        section_by_article.setdefault(key, []).append(sec["heading"])

    def emit_sections(key: str) -> None:
        for heading in section_by_article.get(key, []):
            lines.append(f"## {heading}")
            lines.append("")

    emit_sections("__start__")
    emitted_sections = set(section_by_article.get("__start__", []))
    for article in parsed["articles"]:
        art_id = article["articleId"]
        # Sections recorded as "beforeArticle == this article" belong to the
        # *previous* article's trailing position in the parser; emit any
        # not-yet-emitted section headings before this article in order.
        lines.append(f"## {_article_heading(article)}")
        lines.append("")
        if article.get("deleted"):
            lines.append("삭제")
            lines.append("")
            continue
        for para in article["paragraphs"]:
            lines.append(para)
            lines.append("")
        for heading in article.get("trailingSections", []):
            if heading not in emitted_sections:
                lines.append(f"## {heading}")
                lines.append("")
                emitted_sections.add(heading)

    if parsed.get("addenda"):
        lines.append("## 부칙")
        lines.append("")
        for line in parsed["addenda"]:
            lines.append(line)
            lines.append("")

    if annexes:
        lines.append("## 별표·서식 참조")
        lines.append("")
        lines.append("별표·서식 본문은 국가법령정보센터가 파일(HWP/PDF 등)로 제공합니다. 이 코퍼스에서는 별표 7만 공식 파일을 함께 보존하고(annexes 참조), 나머지는 제목과 공식 파일 식별자만 기록합니다.")
        lines.append("")
        for annex in annexes:
            seqs = ", ".join(f["flSeq"] for f in annex["files"])
            lines.append(f"- {annex['titleKo']} (bylId: {annex['bylId']}, flSeq: {seqs})")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
