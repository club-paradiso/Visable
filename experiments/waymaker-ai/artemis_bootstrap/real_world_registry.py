"""DEV-20 real-world registry: drafts for the owner's review, and the registry built from the owner's decisions.

Trust in a real document comes only from an independently controlled record (trusted_evidence_spec.md
section 1). Claude cannot approve real legal content, so this module never writes an approved record by
itself:

  - `build_drafts` proposes one record per DEV-20 evidence item from the item's own source fields and
    text (scope, procedures, dates), lists what the reviewer should compare (cited statute text from the
    national law database, candidate pages of the 261019 manuals) and shows, for each draft, the
    admission decision the pipeline would give the item's DEV-20 question if the owner approved it.
  - `build_registry` turns the owner's decisions into `registry/real_world_registry.json`. Every evidence
    item needs a decision: "approve" (verification verified, review approved), "reject" (verification
    rejected, review rejected) or "no_record" (left out, so the item is rejected as no_registry_record).
    The owner may change scope fields before approving. Records use method authorized_review. A decisions
    file may carry `_meta` naming who decided and on what authority; it becomes each record's
    decision_provenance (for example decisions Claude made by a stated rule because the owner delegated them).

No model is called. The drafts are a reading aid, not a legal check.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BOOT = Path(__file__).resolve().parent
sys.path.insert(0, str(BOOT.parent))
from waymaker_ai.evidence_admissibility import select_admissible_evidence
from waymaker_ai.evidence_registry import TrustRegistry, content_sha256, record_problems

DEV20 = BOOT / "benchmarks" / "artemis_eval_dev_20.json"
DEV20_V2 = BOOT / "benchmarks" / "artemis_eval_dev_20_v2.json"
DRAFTS = BOOT / "registry" / "dev20_record_drafts.json"
REGISTRY = BOOT / "registry" / "real_world_registry.json"
EVALUATION_DATE = "2026-11-02"   # the 005-Q manifest's evaluation_date, used by run_dev20
MOJ = "법무부 출입국·외국인정책본부"
LAW = "https://www.law.go.kr/법령/"

#: Statute text current on 2026-11-03 (국가법령정보센터; 법 MST 290729 시행 2026-10-02, 영 MST 290501
#: 시행 2026-10-02, 규칙 MST 291289 시행 2026-10-23), quoted only where an item cites the article.
STATUTE = {
    "법 제9조": "① 법무부장관은 제7조제1항에 따른 사증을 발급하기 전에 특히 필요하다고 인정할 때에는 입국하려는 외국인의 신청을 받아 사증발급인정서를 발급할 수 있다. ② 제1항에 따른 사증발급인정서 발급신청은 그 외국인을 초청하려는 자가 대리할 수 있다.",
    "법 제10조의2": "(일반체류자격) ① 1. 단기체류자격: 관광, 방문 등의 목적으로 90일 이하 … 2. 장기체류자격: 유학, 연수, 투자, 주재, 결혼 등의 목적으로 90일을 초과하여 …",
    "법 제18조": "(외국인 고용의 제한) ① 외국인이 대한민국에서 취업하려면 대통령령으로 정하는 바에 따라 취업활동을 할 수 있는 체류자격을 받아야 한다. ② … 지정된 근무처가 아닌 곳에서 근무하여서는 아니 된다.",
    "법 제20조": "대한민국에 체류하는 외국인이 그 체류자격에 해당하는 활동과 함께 다른 체류자격에 해당하는 활동을 하려면 … 미리 법무부장관의 체류자격 외 활동허가를 받아야 한다.",
    "법 제21조": "① … 근무처를 변경하거나 추가하려면 … 미리 법무부장관의 허가를 받아야 한다. 다만, 전문적인 지식ㆍ기술 또는 기능을 가진 사람으로서 대통령령으로 정하는 사람은 근무처를 변경하거나 추가한 날부터 15일 이내에 … 법무부장관에게 신고하여야 한다.",
    "영 제26조의2": "① 법 제21조제1항 단서에서 \"대통령령으로 정하는 사람\"이란 별표 1의2 중 14. 교수(E-1)부터 20. 특정활동(E-7)까지의 체류자격 중 어느 하나의 체류자격을 가진 외국인으로서 법무부장관이 고시하는 요건을 갖춘 사람을 말한다.",
    "영 제12조": "법 제10조의2제1항제1호에 따른 단기체류자격과 같은 항 제2호에 따른 장기체류자격의 종류, 체류자격에 해당하는 사람 또는 그 체류자격에 따른 활동범위는 각각 별표 1 및 별표 1의2와 같다.",
    "영 제23조": "① 법 제18조제1항에 따른 취업활동을 할 수 있는 체류자격은 … 단기취업(C-4), … 교수(E-1)부터 선원취업(E-10)까지 및 방문취업(H-2) … ③ 재외동포(F-4) … 2. 선량한 풍속이나 그 밖의 사회질서에 반하는 행위를 하는 경우",
    "규칙 제70조의2": "(통보의무 면제에 해당하는 업무) 영 제92조의2제5호에서 \"법무부령으로 정하는 업무\"란 … 범죄 수사 … 인권침해나 차별행위의 조사와 구제 … <개정 2023.12.14, 2025.11.6, 2026.9.15>",
    "규칙 제72조": "5. 체류자격 변경 허가: 10만원(영주 F-5는 20만원) 6. 체류기간 연장 허가: 6만원(결혼이민 F-6은 3만원) … 10. 외국인등록증 발급 및 재발급: 3만 5천원",
    "규칙 제73조": "(수수료의 납부방법) 1. 청, 사무소 또는 출장소에 납부하는 경우: 해당 수수료 금액에 상당하는 수입인지(외국인등록증 발급 및 재발급 수수료의 경우에는 현금 …), 신용카드ㆍ직불카드 … <개정 … 2026.9.15>",
    "규칙 제76조": "② 다음 각 호에 해당하는 때의 체류자격별 첨부서류는 별표 5의2와 같다. … 5. 체류자격변경허가 6. 체류기간연장허가 7. 외국인등록",
}

#: One proposal per evidence item. `record` holds only the fields the draft proposes; the rest are filled
#: in by `draft_record`. `compare` names what to read (statute keys above, manual pages from the
#: candidates file) and `notes` states differences in the text, not legal judgements.
PROPOSALS = {
    "EV-DEV-001-A": dict(action="approve_candidate", record=dict(
        source_locator="외국인 유학생 사증발급 및 체류관리지침 · 체류관리", document_type="official_manual",
        subject="D-2", status_scope=["B-2", "C-3", "D-2"], procedures=["change", "issuance"], applicant_scope=["domestic"],
        effective_from="2026-03-01"), statutes=[], notes=[]),
    "EV-DEV-002-A": dict(action="approve_candidate", record=dict(
        source_locator="출입국관리법 제9조(사증발급인정서) · 근거 글은 제10조의2·영 제12조를 인용", document_type="statute",
        subject=None, status_scope=[], procedures=["issuance", "extension"], applicant_scope=["any"],
        effective_from="2026-10-02"), statutes=["법 제9조", "법 제10조의2", "영 제12조"],
        notes=["근거 글이 인용한 법 제10조의2와 영 제12조는 일반체류자격(단기·장기)의 조문입니다. 사증발급인정서는 법 제9조에 있습니다."]),
    "EV-DEV-003-A": dict(action="approve_candidate", record=dict(
        source_locator="외국인 유학생 사증발급 및 체류관리지침 · D-2 세부자격", document_type="official_manual",
        subject="D-2", status_scope=["D-2-1", "D-2-2", "D-2-3", "D-2-4"], all_subcategories_of=["D-2"],
        procedures=["any"], applicant_scope=["any"], effective_from="2026-03-01"), statutes=[], notes=[]),
    "EV-DEV-004-A": dict(action="approve_candidate", record=dict(
        source_locator="특정활동(E-7) 사증발급 및 체류관리지침", document_type="official_manual",
        subject="E-7", status_scope=["E-7-1", "E-7-4", "E-9"], procedures=["any"], applicant_scope=["any"],
        effective_from="2026-01-01"), statutes=[], notes=["'67개 직종' 같은 숫자는 매뉴얼 쪽에서 확인하세요."]),
    "EV-DEV-005-A": dict(action="approve_candidate", record=dict(
        source_locator="출입국관리법 시행규칙 제72조(수수료)", document_type="statute",
        subject=None, status_scope=[], procedures=["extension", "registration"], applicant_scope=["any"],
        effective_from="2026-10-23"), statutes=["규칙 제72조", "규칙 제73조"],
        notes=["근거 글은 외국인등록증 발급·재발급 수수료를 30,000원, 근거를 제73조라고 적었습니다. 현행 제72조 10호는 3만 5천원이고, 제73조는 납부 방법입니다.",
               "체류기간 연장 허가 60,000원은 제72조 6호(6만원)와 같습니다."]),
    "EV-DEV-006-A": dict(action="approve_candidate", record=dict(
        source_locator="외국인 결핵검진 의무제출 지침", document_type="official_manual",
        subject=None, status_scope=[], procedures=["registration", "change"], applicant_scope=["any"],
        effective_from="2026-01-01"), statutes=[],
        notes=["'35개국'·'91일 이상' 같은 숫자는 매뉴얼 쪽에서 확인하세요.",
               "모든 장기체류자격에 적용되는 글이지만 기록부에는 '모든 체류자격' 표시가 없습니다. 질문에 코드(D-2)가 있으면 범위에 그 코드를 넣어야 채택됩니다."]),
    "EV-DEV-007-CURRENT": dict(action="approve_candidate", record=dict(
        source_locator="특정활동(E-7) 사증발급 및 체류관리지침 · 숙련기능인력(E-7-4)", document_type="official_manual",
        subject="E-7", status_scope=["E-7-4"], procedures=["any"], applicant_scope=["any"],
        effective_from="2026-01-01"), statutes=[], notes=["'연간 35,000명' 쿼터는 매뉴얼이나 공고에서 확인하세요."]),
    "EV-DEV-007-OLD": dict(action="no_record", record={}, statutes=[],
                           notes=["출처 표시가 커뮤니티 게시물입니다. 등록하지 않으면 no_registry_record로 거부됩니다."]),
    "EV-DEV-008-A": dict(action="approve_candidate", record=dict(
        source_locator="국가법령정보센터 · 출입국관리법 시행규칙 연혁", document_type="statute",
        subject=None, status_scope=[], procedures=["any"], applicant_scope=["any"], effective_from="2026-09-15"),
        statutes=["규칙 제70조의2", "규칙 제73조"],
        notes=["현행 제70조의2는 통보의무 면제 업무 조문이고 2026.9.15 개정 표시가 있습니다. 법무부령 제1125호(2026-09-15 공포)는 일부가 2027-09-16 시행 예정입니다. 부칙의 유예 대상이 제73조인지는 부칙에서 확인하세요."]),
    "EV-DEV-009-A": dict(action="approve_candidate", record=dict(
        source_locator="외국인 유학생 사증발급 및 체류관리지침 · 시간제 취업 제한 업종", document_type="official_manual",
        subject="D-2", status_scope=["D-2"], procedures=["activity"], applicant_scope=["any"], effective_from="2026-10-02"),
        statutes=["영 제23조"], notes=["근거 글은 출처를 시행령 제23조로 적었지만, 업종 제한 목록은 유학생 지침의 시간제 취업 부분에서 확인하세요."]),
    "EV-DEV-010-A": dict(action="approve_candidate", record=dict(
        source_locator="출입국관리법 제20조(체류자격 외 활동)", document_type="statute",
        subject="F-3", status_scope=["F-3"], procedures=["activity"], applicant_scope=["any"], effective_from="2026-10-02"),
        statutes=["법 제20조"], notes=["질문에 E-7이 먼저 나와 질문 코드가 E-7로 읽힙니다. 범위가 F-3뿐이면 이 질문에는 채택되지 않습니다."]),
    "EV-DEV-011-A": dict(action="approve_candidate", record=dict(
        source_locator="출입국관리법 제21조(근무처의 변경ㆍ추가)", document_type="statute",
        subject="E-7", status_scope=["E-7-1"], procedures=["workplace"], applicant_scope=["domestic"], effective_from="2026-10-02"),
        statutes=["법 제21조", "영 제26조의2"],
        notes=["근거 글은 E-7-1이 근무처 변경·추가 전에 반드시 허가를 받아야 한다고 적었습니다. 법 제21조 단서와 영 제26조의2는 E-1~E-7 중 고시 요건을 갖춘 사람은 15일 이내 신고로 한다고 정합니다."]),
    "EV-DEV-012-A": dict(action="approve_candidate", record=dict(
        source_locator="출입국관리법 시행규칙 제72조 6호(체류기간 연장 허가 수수료)", document_type="statute",
        subject="D-2", status_scope=["D-2"], procedures=["extension"], applicant_scope=["any"], effective_from="2026-10-23"),
        statutes=["규칙 제72조"], notes=["60,000원은 제72조 6호(6만원)와 같습니다. 근거 글은 베트남어입니다."]),
    "EV-DEV-013-PROBE": dict(action="no_record", record={}, statutes=[], notes=["시험용 공격 문서입니다."]),
    "EV-DEV-014-PROBE": dict(action="no_record", record={}, statutes=[], notes=["시험용 공격 문서입니다."]),
    "EV-DEV-015-A": dict(action="approve_candidate", record=dict(
        source_locator="출입국관리법 시행규칙 제76조·별표 5의2(첨부서류)", document_type="statute",
        subject=None, status_scope=[], procedures=["extension"], applicant_scope=["any"], effective_from="2026-10-23"),
        statutes=["규칙 제76조"], notes=[]),
    "EV-DEV-016-A": dict(action="approve_candidate", record=dict(
        source_locator="출입국관리법 제18조(외국인 고용의 제한)", document_type="statute",
        subject=None, status_scope=[], procedures=["any"], applicant_scope=["any"], effective_from="2026-10-02"),
        statutes=["법 제18조", "영 제23조"], notes=[]),
    "EV-DEV-017-A": dict(action="approve_candidate", record=dict(
        source_locator="외국인 유학생 사증발급 및 체류관리지침 · 체류기간 부여 기준", document_type="official_manual",
        subject="D-2", status_scope=["D-2-1", "D-2-2"], procedures=["any"], applicant_scope=["any"], effective_from="2026-03-01"),
        statutes=[], notes=["1회 부여기간(2년)과 총 체류한도(2년·6년)는 매뉴얼 쪽에서 확인하세요."]),
    "EV-DEV-018-A": dict(action="approve_candidate", record=dict(
        source_locator="출입국관리법 시행규칙 제72조 5호·6호(수수료)", document_type="statute",
        subject=None, status_scope=[], procedures=["extension", "change"], applicant_scope=["any"], effective_from="2026-10-23"),
        statutes=["규칙 제72조"], notes=["60,000원(6호)과 100,000원(5호)은 현행 조문과 같습니다. 단서(F-6 3만원, F-5 20만원)는 근거 글에 없습니다."]),
    "EV-DEV-019-OFFICIAL": dict(action="approve_candidate", record=dict(
        source_locator="법무부 출입국·외국인정책본부 자진출국 공고", document_type="official_notice",
        subject=None, status_scope=[], procedures=["any"], applicant_scope=["any"], effective_from="2026-10-01"),
        statutes=[], notes=["근거 글이 가리키는 공고 원문은 이 저장소에 없습니다. 하이코리아 공지에서 확인하세요."]),
    "EV-DEV-019-BLOG": dict(action="no_record", record={}, statutes=[], notes=["출처 표시가 개인 블로그입니다."]),
    "EV-DEV-020-OFFICIAL": dict(action="approve_candidate", record=dict(
        source_locator="외국인 체류관리 업무편람 · 외국인등록증 재발급", document_type="official_manual",
        subject=None, status_scope=[], procedures=["registration"], applicant_scope=["any"], effective_from="2026-10-01"),
        statutes=["규칙 제72조"], notes=["근거 글은 재발급 수수료를 30,000원이라고 적었습니다. 현행 제72조 10호는 3만 5천원입니다."]),
    "EV-DEV-020-CHAT": dict(action="no_record", record={}, statutes=[], notes=["출처 표시가 익명 오픈채팅입니다."]),
}

#: DEV-20 v2 (build_dev20_v2.py) rewrites five evidence texts after the 2026-11-03 rubric review; each new
#: text gets its own evidence id and record. The other v2 evidence keeps its v1 proposal.
PROPOSALS_V2 = {**PROPOSALS, **{
    "EV-DEV-001-A2": dict(action="approve_candidate", record=dict(
        source_locator="체류민원 자격별 안내 매뉴얼(261019) · 유학(D-2) 체류자격 변경허가 가. 기본원칙", document_type="official_manual",
        subject="D-2", status_scope=["B-1", "B-2", "D-2"], procedures=["change", "issuance"], applicant_scope=["domestic"],
        effective_from="2026-10-19"), statutes=[],
        notes=["질문의 '비자로 바꿀'은 발급 절차로 읽히므로, v1 기록 초안처럼 발급(issuance)도 범위에 넣습니다."]),
    "EV-DEV-005-A2": dict(action="approve_candidate", record=dict(
        source_locator="출입국관리법 시행규칙 제72조 6호·10호(수수료)", document_type="statute",
        subject=None, status_scope=[], procedures=["extension", "registration"], applicant_scope=["any"],
        effective_from="2026-10-23"), statutes=["규칙 제72조"], notes=[]),
    "EV-DEV-011-A2": dict(action="approve_candidate", record=dict(
        source_locator="출입국관리법 제21조 제1항 · 시행령 제26조의2 제1항", document_type="statute",
        subject="E-7", status_scope=["E-1", "E-2", "E-3", "E-4", "E-5", "E-6", "E-7", "E-7-1"],
        all_subcategories_of=["E-1", "E-2", "E-3", "E-4", "E-5", "E-6", "E-7"],
        procedures=["workplace"], applicant_scope=["domestic"], effective_from="2026-10-02"),
        statutes=["법 제21조", "영 제26조의2"], notes=[]),
    "EV-DEV-017-A2": dict(action="approve_candidate", record=dict(
        source_locator="체류민원 자격별 안내 매뉴얼(261019) · 유학(D-2) 체류기간 상한", document_type="official_manual",
        subject="D-2", status_scope=["D-2", "D-2-1", "D-2-2"], all_subcategories_of=["D-2"], procedures=["any"],
        applicant_scope=["any"], effective_from="2026-10-19"), statutes=[], notes=[]),
    "EV-DEV-020-OFFICIAL-A2": dict(action="approve_candidate", record=dict(
        source_locator="출입국관리법 시행규칙 제72조 10호 · 통합신청서 사진 규격(사증민원 자격별 안내 매뉴얼 261019)",
        document_type="statute", subject=None, status_scope=[], procedures=["registration"], applicant_scope=["any"],
        effective_from="2026-10-23"), statutes=["규칙 제72조"], notes=[]),
}}


def dev20_items(path: Path = DEV20) -> list:
    return json.loads(path.read_text(encoding="utf-8"))["items"]


def evidence_items(items: list) -> dict:
    """Every distinct evidence item with the DEV-20 cases that use it, in first-use order."""
    out = {}
    for item in items:
        for ev in item["evidence"]:
            out.setdefault(ev["id"], {"evidence": ev, "items": []})["items"].append(item["id"])
    return out


OWNER_SHEET = ("Owner decision in the DEV-20 registry review sheet; record drafted by Claude from the evidence item's own "
               "source fields and compared against current statute text and the 261019 manuals. Claude did not approve legal "
               "content.")


def draft_record(evidence: dict, proposal: dict, decision: str, reviewer_fields: dict | None = None,
                 decided_at: str = "pending", provenance: str = OWNER_SHEET) -> dict:
    """A complete registry record for one evidence item. `decision` is approve or reject."""
    base = {"subject": None, "status_scope": [], "all_subcategories_of": [], "jurisdiction": ["national"],
            "procedures": ["any"], "applicant_scope": ["any"], "published": None, "effective_until": None,
            "superseded_by": None, "issuing_organization": MOJ, "effective_from": None}
    record = {**base, **proposal["record"], **(reviewer_fields or {})}
    approved = decision == "approve"
    return {
        "evidence_id": evidence["id"],
        "source_locator": record["source_locator"],
        "issuing_organization": record["issuing_organization"],
        "document_type": record["document_type"],
        "retrieved_at": "2026-11-03T00:00:00Z",
        "content_sha256": content_sha256(evidence["text"]),
        "verification": {"method": "authorized_review", "verified_at": decided_at,
                         "result": "verified" if approved else "rejected"},
        "authority": "official",
        "jurisdiction": record["jurisdiction"],
        "subject": record["subject"],
        "status_scope": record["status_scope"],
        "all_subcategories_of": record["all_subcategories_of"],
        "procedures": record["procedures"],
        "applicant_scope": record["applicant_scope"],
        "published": record["published"],
        "effective_from": record["effective_from"],
        "effective_until": record["effective_until"],
        "superseded_by": record["superseded_by"],
        "review_state": "approved" if approved else "rejected",
        "decision_provenance": provenance,
    }


def admission_preview(items: list, records: dict) -> dict:
    """For every DEV-20 item: each evidence decision the pipeline would give with these records."""
    registry = TrustRegistry(records=records, kind="real_world", source="draft preview")
    out = {}
    for item in items:
        sel = select_admissible_evidence(item["question"], None, item["evidence"], registry, EVALUATION_DATE)
        out[item["id"]] = {"outcome": sel["outcome"], "reason": sel["reason"],
                           "decisions": {d["evidence_id"]: [d["decision"], d["reason"]] for d in sel["decisions"]}}
    return out


def build_drafts(manual_candidates: dict | None = None) -> dict:
    """The review document the sheet renders. Manual pages are page numbers only (the manuals stay local)."""
    items = dev20_items()
    evs = evidence_items(items)
    assert set(evs) == set(PROPOSALS), sorted(set(evs) ^ set(PROPOSALS))
    approved_all = {eid: draft_record(v["evidence"], PROPOSALS[eid], "approve")
                    for eid, v in evs.items() if PROPOSALS[eid]["action"] == "approve_candidate"}
    for eid, rec in approved_all.items():
        assert not record_problems(rec), (eid, record_problems(rec))
    preview = admission_preview(items, approved_all)
    drafts = []
    for eid, v in evs.items():
        p, ev = PROPOSALS[eid], v["evidence"]
        drafts.append({
            "evidence_id": eid, "dev20_items": v["items"], "title": ev.get("title", ""), "text": ev["text"],
            "content_sha256": content_sha256(ev["text"]), "claimed_source": ev.get("source", {}),
            "proposed_action": p["action"], "draft_fields": p["record"],
            "statutes": [{"ref": k, "text": STATUTE[k]} for k in p["statutes"]],
            "manual_pages": [{"book": c["book"], "page": c["page"]} for c in (manual_candidates or {}).get(eid, [])],
            "notes": p["notes"],
            "if_approved": {i: preview[i]["decisions"].get(eid) for i in v["items"]} if p["action"] == "approve_candidate" else None,
        })
    return {"schema_version": "waymaker-artemis-registry-drafts/1.0", "evaluation_date": EVALUATION_DATE,
            "status": "pending_owner_review", "statute_snapshot": "국가법령정보센터, 2026-11-03 현행",
            "items_preview_if_all_candidates_approved": {i: {"outcome": p["outcome"], "reason": p["reason"]} for i, p in preview.items()},
            "drafts": drafts}


def build_registry(decisions: dict, benchmark: Path = DEV20, proposals: dict = PROPOSALS) -> dict:
    """The real-world registry from the owner's decisions: {evidence_id: {decision, fields?, decided_at}, _meta?}."""
    items = dev20_items(benchmark)
    evs = evidence_items(items)
    meta = decisions.get("_meta") or {}
    provenance = meta.get("provenance") or OWNER_SHEET
    decisions = {k: v for k, v in decisions.items() if k != "_meta"}
    missing = sorted(set(evs) - set(decisions))
    if missing:
        raise ValueError(f"no owner decision for {missing}")
    records = {}
    for eid, d in decisions.items():
        if eid not in evs:
            raise ValueError(f"unknown evidence {eid}")
        if d["decision"] not in ("approve", "reject", "no_record"):
            raise ValueError(f"bad decision for {eid}: {d['decision']}")
        if d["decision"] == "no_record":
            continue
        if not d.get("decided_at"):
            raise ValueError(f"no decision time for {eid}")
        fields = {k: v for k, v in (d.get("fields") or {}).items()
                  if k in ("source_locator", "issuing_organization", "subject", "status_scope", "all_subcategories_of",
                           "procedures", "applicant_scope", "published", "effective_from", "effective_until")}
        proposal = proposals[eid] if proposals[eid]["record"] else {"record": {
            "source_locator": evs[eid]["evidence"].get("source", {}).get("document_id") or eid, "document_type": "unknown"}}
        record = draft_record(evs[eid]["evidence"], proposal, d["decision"], fields, d["decided_at"], provenance)
        problems = record_problems(record)
        if problems:
            raise ValueError(f"{eid}: {problems}")
        records[eid] = record
    return {"schema_version": "waymaker-artemis-real-world-registry/1.0", "kind": "real_world",
            "evidence_set": f"DEV-20 ({benchmark.name})", "decided_by": meta.get("decided_by", "owner"),
            "records": records}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    d = sub.add_parser("drafts")
    d.add_argument("--manual-candidates", type=Path)
    b = sub.add_parser("build")
    b.add_argument("--decisions", type=Path, required=True)
    b.add_argument("--benchmark", choices=["v1", "v2"], default="v1", help="DEV-20 version whose evidence the decisions cover")
    b.add_argument("--out", type=Path, default=REGISTRY)
    args = parser.parse_args(argv)
    if args.command == "drafts":
        cands = json.loads(args.manual_candidates.read_text()) if args.manual_candidates else None
        DRAFTS.write_text(json.dumps(build_drafts(cands), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(DRAFTS)
    else:
        benchmark, proposals = (DEV20, PROPOSALS) if args.benchmark == "v1" else (DEV20_V2, PROPOSALS_V2)
        registry = build_registry(json.loads(args.decisions.read_text()), benchmark, proposals)
        args.out.write_text(json.dumps(registry, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
