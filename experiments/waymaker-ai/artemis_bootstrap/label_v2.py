"""Label version 2 for the 140 real-manual cases: frozen originals in, versioned copies out.

Why this exists: the six real-manual case sets are frozen (their SHA-256 is
recorded in run records and in the review sheet), but reviews found labels
that are too strict, and one wrong gold page. Labels are never edited in
place. This module copies every case set to ``label_v2/<set>_cases.v2.json``
with the same 140 ids in the same order, applies only the decisions written
below, and writes ``label_v2/decisions.v2.json``: one row per case saying what
each source said (the frozen label, the saved verdict on the review sheet, the
AI first pass, ChatGPT's partial v2 proposal), what was decided, why, and
what is still open.

What a decision is and is not: every decision is a change to the TEST LABEL,
grounded in the text of the supplied manual page. None of them is a legal
verification; each row carries ``verification: 검증 보류``. A case with no
decision is copied unchanged and marked ``pending``. ChatGPT's partial v2
proposals are inputs, not adopted wholesale: each was checked against the page
and the recorded answers, and several are replaced by structural checks
(``answer_must_match`` / ``answer_must_not_match`` / ``answer_flag_if_match``)
because a ban on one exact sentence misses reworded errors and fails an answer
that quotes the error to correct it.

Usage, from experiments/waymaker-ai/artemis_bootstrap::

    python label_v2.py build     # writes label_v2/*.v2.json and decisions.v2.json
    python label_v2.py regrade   # re-grades recorded answers against v2 (post hoc)
    python label_v2.py check     # exit 1 if the committed v2 files differ from a fresh build
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import manual_ledger  # noqa: E402
import smoke_grader  # noqa: E402

OUT = HERE / "label_v2"
REVIEWS = HERE / "reviews"
SETS = ("manual_oracle", "manual_routing", "manual_clarify", "manual_buttons", "manual_always_ask", "manual_misclick")
#: The run whose recorded answers the review sheet shows for each set.
RUNS = {
    "manual_oracle": "2026-10-26-e4b-it-4bit-m1-8gb-manual-oracle",
    "manual_routing": "2026-10-26-e4b-it-4bit-m1-8gb-routing-routed",
    "manual_clarify": "2026-10-26-e4b-it-4bit-m1-8gb-clarify-route-clarify",
    "manual_buttons": "2026-10-26-e4b-it-4bit-m1-8gb-buttons-buttons",
    "manual_always_ask": "2026-10-26-e4b-it-4bit-m1-8gb-always-ask-always-ask",
    "manual_misclick": "2026-10-27-e4b-it-4bit-m1-8gb-misclick-label",
}
VERIFICATION = "검증 보류: 라벨을 제공된 매뉴얼 쪽 원문에 맞춘 것이며 법률 검증이 아니다"

# Patterns shared by the decisions. Korean answers are matched after NFC.
PER_GRANT = r"(?:1\s*회|한\s*번에|회당|매회|1번에)"
TOTAL = r"(?:최대|총|통산|상한)"
NOT_NEGATED = r"(?![^.\n]{0,8}아니)"


def _r(label: str, pattern: str) -> Dict[str, str]:
    return {"label": label, "pattern": pattern}


#: Each decision: the fields of ``expect`` (and, for K-14, ``evidence``) to change,
#: the sources that raised it, the page text it rests on, and what is still open.
DECISIONS: Dict[str, Dict[str, Any]] = {
    "manual_oracle/M-01-stay-extension-fee": {
        "decision": "adopted_modified",
        "drop_expect": ["answer_must_contain"],
        "set_expect": {"answer_must_match": [
            _r("연장 수수료 6만원(표기 변형 허용)", r"(?<![\d,])6\s*만\s*원|(?<![\d,])60,?000\s*원"),
        ]},
        "raised_by": ["human_review_per_handoff", "chatgpt_second_opinion"],
        "page_evidence": "stay p5 표: '체류기간 연장허가 6만원'",
        "rationale": "저장된 사람 판정(인계 기록상 기존 사람 판정)은 60,000원으로 답했다. '6만원' 글자 비교는 60,000원을 떨어뜨리므로 같은 금액의 표기 변형을 허용한다.",
        "not_adopted": "사람 판정의 F-6 3만원 외 온라인 20% 감면(48,000원), 면제 대상, 출국을 위한 연장 0원은 제공된 5쪽에 없거나 법령 확인이 필요해 쪽 근거 라벨에 넣지 않았다.",
        "open_issues": ["온라인 감면·면제 요건을 라벨에 넣을지는 법령 검토 후 소유자가 정한다.", "'16만원' 같은 다른 금액 안의 '6만원'은 앞 숫자 검사로 막았으나 모든 표기를 보장하지 않는다."],
    },
    "manual_oracle/M-04-d4-parttime-wait": {
        "decision": "adopted_modified",
        "drop_expect": ["answer_must_contain"],
        "set_expect": {
            "answer_must_match": [
                _r("6개월", r"6\s*개월"),
                _r("기산점: 변경일 또는 (사증소지자) 입국일", r"변경일|입국일|변경한\s*날|입국한\s*날|변경된\s*날"),
            ],
            "answer_flag_if_match": [
                _r("기산점을 활동·신청 시점으로 쓴 표현", r"(?:하려는|하고자\s*하는|시작하는|시작한|신청하는|신청한)\s*(?:시점|날|때)\S*\s*부터[^.\n]{0,6}6\s*개월"),
            ],
        },
        "raised_by": ["chatgpt_second_opinion", "chatgpt_partial_v2"],
        "page_evidence": "stay p37: '어학연수(D-4-1, D-4-7)자격 및 방문학생(D-2-8)자격은 변경일(사증소지자는 입국일)로부터 6개월이 경과된 사람'",
        "rationale": "부분 수정본은 기록된 오답 문장('해당 활동을 하려는 시점으로부터 6개월이 경과')만 막았다. 대신 원문의 기산점(변경일·입국일)이 답에 있어야 통과하게 한다. 잘못된 기산점 표현은 떨어뜨리지 않고 사람이 보도록 표시만 한다(오답을 인용해 바로잡는 정답을 떨어뜨리지 않기 위해).",
        "open_issues": ["변경일과 입국일 중 어느 것이 그 사람에게 맞는지는 검사하지 않는다.", "기산점을 맞게 쓰고 다른 곳에 틀린 기산점을 함께 쓴 답은 통과하되 표시된다(사람 확인 필요).", "6개월·기산점은 법 조문이 아니라 매뉴얼 운영기준이다(2차 의견 메모)."],
    },
    "manual_oracle/M-10-d10t-stay-cap": {
        "decision": "adopted_modified",
        "drop_expect": ["answer_must_contain"],
        "set_expect": {
            "answer_must_match": [
                _r("총 체류기간 상한 3년", TOTAL + r"[^.\n,년]{0,12}3\s*년|3\s*년\s*\(\s*1\s*회\s*1\s*년\s*\)"),
                _r("1회 부여 기간 1년", PER_GRANT + r"[^.\n,년]{0,15}1\s*년|1\s*년\s*씩"),
            ],
            "answer_must_not_match": [
                _r("1회 기간을 3년으로 씀(뒤바뀜)", PER_GRANT + r"[^.\n,년]{0,15}3\s*년" + NOT_NEGATED),
                _r("총 기간을 1년으로 씀(뒤바뀜)", r"(?:총|통산|상한)[^.\n,년]{0,12}1\s*년" + NOT_NEGATED),
            ],
        },
        "raised_by": ["human_review_per_handoff", "chatgpt_partial_v2"],
        "page_evidence": "stay p160 표 '체류기간 상한 (1회 부여 기간)': '3년 (1회 1년)'",
        "rationale": "기록된 답('최대 3년이며, 1회 부여 기간은 1년')은 맞는데 표의 괄호 표기와 달라 떨어졌다. 부분 수정본은 그 답 문장을 그대로 허용 목록에 넣어 다른 표현은 여전히 떨어지고 뒤바뀐 답도 잡지 못한다. 총기간 3년과 1회 1년이 각각 제자리에 있어야 통과하고, 둘이 뒤바뀌면 실패하게 한다.",
        "open_issues": ["별표의 법무부장관 재량 예외(2차 의견 메모)는 라벨에 넣지 않았다.", "'최대 1년'은 1회 상한 표현으로도 쓰이므로 '최대'만으로는 뒤바뀜을 판정하지 않는다.", "영어 답은 검사하지 않는다."],
    },
    "manual_routing/N-10-d5-consular-visa-bureau-docs": {
        "decision": "adopted",
        "drop_expect": ["answer_must_contain"],
        "set_expect": {"answer_must_contain_any_of_each": [["설치허가증", "운영자금 도입실적"]]},
        "raised_by": ["ai_first_pass", "chatgpt_partial_v2"],
        "page_evidence": "visa p90: '③ 국내 지국․지사 설치허가증이나 국내 지국․지사 운영자금 도입실적 증빙 서류'",
        "rationale": "원문이 두 서류 중 하나를 요구하고, 특수 가운뎃점(․) 때문에 '지국·지사'로 쓴 정답이 떨어졌다. 부분 수정본과 같다.",
        "open_issues": ["체류 매뉴얼 p105에도 비슷한 문구가 있어 문자열만으로 출처를 가리지 못한다(인용 검사로만 구분)."],
    },
    "manual_clarify/Q-11-e9-change-jobs-count": {
        "decision": "adopted_modified",
        "drop_expect": ["answer_must_contain"],
        "set_expect": {
            "answer_must_match": [
                _r("3회의 상한(초과 불가·까지)", r"3\s*회\s*(?:까지|이내)|(?:최대|최고)\s*3\s*회|3\s*회[^.\n]{0,40}(?:초과할\s*수\s*없|초과하지\s*못|초과\s*불가|넘을\s*수\s*없|넘지\s*못)"),
            ],
            "answer_flag_if_match": [
                _r("횟수를 초과해 변경할 수 있다는 표현", r"초과하여[^.\n]{0,15}(?:변경할\s*수\s*있|변경이\s*가능|변경\s*가능)"),
            ],
        },
        "raised_by": ["chatgpt_second_opinion", "chatgpt_partial_v2"],
        "page_evidence": "stay p328: '취업가능기간 중에는 원칙적으로 3회, 재고용절차에 따라 체류기간이 연장된 기간 중에는 2회를 초과할 수 없음'",
        "rationale": "기록된 답은 '2회를 초과하여 사업장을 변경할 수 있습니다'로 뜻이 뒤집혔는데 '원칙적으로 3회' 글자만 보고 통과했다. 부분 수정본은 그 문장만 막았다. 대신 3회가 상한이라는 뜻(까지·초과할 수 없음 등)이 있어야 통과하게 하고, '초과하여 변경 가능' 표현은 표시만 한다.",
        "open_issues": ["3회 상한은 맞게 쓰고 연장 기간의 2회는 거꾸로 쓴 답은 통과하되 표시된다(사람 확인 필요).", "변경 횟수에 넣지 않는 예외(휴·폐업 등)는 검사하지 않는다.", "법 제25조 제4항의 2026-12-10, 2027-06-10 시행 예정 개정은 반영하지 않았다(2차 의견 메모)."],
    },
    "manual_misclick/K-05-f2-2-child-of-national": {
        "decision": "adopted_modified",
        "set_expect": {"answer_must_not_match": [
            _r("5년 사증을 제외대상자에게 적용된다고 씀",
               r"제외\s*대상자?\s*(?:에게|만|에\s*한하여)[^.\n]{0,6}(?:적용|해당|발급|받을)(?![^.\n]{0,10}(?:지\s*않|안\s*되|않습니다|제한))"),
        ]},
        "raised_by": ["chatgpt_second_opinion", "chatgpt_partial_v2"],
        "page_evidence": "visa p313: '공관장 재량으로 5년간 유효한 체류기간 1년 이하의 거주(F-2-2) 복수사증' 다음에 별도로 '※ ... 거주(F-2) 사증발급 제외대상자 - 병역 ... 남성'",
        "rationale": "기록된 답은 5년 사증이 '제외대상자에게 적용되는 사항'이라고 적용 대상을 뒤집었다. 부분 수정본은 그 문장만 막았다. 제외대상자에게 적용·발급된다는 형태를 실패로 하되, '제외대상자에게는 발급되지 않습니다'처럼 부정하는 문장은 통과시킨다.",
        "open_issues": ["'제외대상자만 받을 수 있다' 외의 다른 뒤집힌 표현(예: 이 사증의 대상이 병역 미이행 남성이라고 쓰는 경우)은 잡지 못한다.", "영어 답은 검사하지 않는다."],
    },
    "manual_misclick/K-06-c3-3-medical-docs": {
        "decision": "adopted",
        "drop_expect": ["answer_must_contain"],
        "set_expect": {"answer_must_contain_any_of_each": [["의사소견서", "병원진단서", "진단서"], ["예약 입증자료", "예약 증빙", "예약 확인"]]},
        "raised_by": ["ai_first_pass", "chatgpt_partial_v2"],
        "page_evidence": "visa p339: '② ... 병원진단서, 의사소견서 등 입증자료 ③ ... 예약 입증자료'",
        "rationale": "원문이 '병원진단서, 의사소견서 등'으로 예시하므로 둘 중 하나면 된다. 부분 수정본과 같다.",
        "open_issues": ["'예약 증빙', '예약 확인'은 원문에 없는 바꿔 쓴 표현이라 범위가 넓다."],
    },
    "manual_misclick/K-10-f1-ethnic-korean-activity": {
        "decision": "adopted",
        "drop_expect": ["answer_must_contain"],
        "set_expect": {"answer_must_contain_any_of_each": [["고용추천서", "고용필요성 입증서류", "고용 필요성 입증"]]},
        "raised_by": ["chatgpt_partial_v2"],
        "page_evidence": "stay p343: '② 주무부처 장의 고용추천서 또는 고용필요성 입증서류'",
        "rationale": "원문이 둘 중 하나를 요구한다. 부분 수정본과 같다.",
        "open_issues": [],
    },
    "manual_misclick/K-14-d8-4-where-to-apply-misclick": {
        "decision": "adopted_modified",
        "set_evidence": [
            {"id": "visa_manual_2026_10_19_pdf#p107", "source_id": "visa_manual_2026_10_19_pdf", "page": 107, "domain": "visa_issuance"},
            {"id": "visa_manual_2026_10_19_pdf#p108", "source_id": "visa_manual_2026_10_19_pdf", "page": 108, "domain": "visa_issuance"},
            {"id": "stay_manual_2026_10_19_pdf#p119", "source_id": "stay_manual_2026_10_19_pdf", "page": 119, "domain": "stay"},
        ],
        "set_expect": {"must_cite": ["visa_manual_2026_10_19_pdf#p108"]},
        "raised_by": ["ai_first_pass", "chatgpt_partial_v2"],
        "page_evidence": "visa p107 맨 위 '원칙적으로 신청자의 본국에 소재한 대한민국 공관' 뒤 서류는 '외국인투자기업등록증, 공동사업자인 국민의 사업자금'으로 앞 항목에 속한다. D-8-4 항목은 p107 아래에서 시작하고 그 '나. 신청기관'은 p108에 있다.",
        "rationale": "정답 쪽을 p108로 바꾸되, D-8-4 항목 제목이 p107에 있으므로 p107을 빼지 않고 근거에 함께 둔다(부분 수정본은 p107을 p108로 바꿨다).",
        "open_issues": ["기록된 답은 p108을 보지 못한 실행에서 나왔으므로 v2로 다시 채점할 수 없다(비교 불가). 모델을 다시 돌려야 한다.", "p107과 p108의 같은 문장 중 어느 쪽을 인용해야 하는지는 쪽 경계에 따른 판단이며 사람 확인이 필요하다."],
        "recorded_answer_comparable": False,
    },
}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _key(set_name: str, case_id: str) -> str:
    return f"{set_name}/{case_id}"


def _load_sources() -> Dict[str, Dict[str, Any]]:
    """What each reviewer said, by case key. Missing files simply give no entry."""
    out: Dict[str, Dict[str, Any]] = {}
    live = REVIEWS / "live_review_export_2026-10-27.json"
    if live.exists():
        data = json.loads(live.read_text(encoding="utf-8"))
        for r in data["reviews"]:
            d = r["data"]
            out.setdefault(d["key"], {})["saved_verdict"] = {
                "verdict": d.get("verdict"), "provenance": r.get("provenance_per_handoff_index"),
                "doc_version": r.get("version"), "updated_at": d.get("updated_at"),
                "note": "검토표 reviews 저장소의 판정. 출처 구분은 인계 기록에만 근거한다.",
            }
    first = REVIEWS / "ai_first_pass_2026-10-27.json"
    if first.exists():
        for r in json.loads(first.read_text(encoding="utf-8"))["reviews"]:
            out.setdefault(r["key"], {})["ai_first_pass"] = {"verdict": r["verdict"], "confidence": r.get("confidence")}
    partial_dir = REVIEWS / "second_opinion_chatgpt_2026-10-27" / "partial-v2"
    for p in sorted(partial_dir.glob("*_cases.v2-partial.json")):
        set_name = p.name.replace("_cases.v2-partial.json", "")
        frozen = {c["id"]: c for c in json.loads((HERE / f"{set_name}_cases.json").read_text(encoding="utf-8"))["cases"]}
        for c in json.loads(p.read_text(encoding="utf-8"))["cases"]:
            if c != frozen.get(c["id"]):
                out.setdefault(_key(set_name, c["id"]), {})["chatgpt_partial_v2"] = {
                    "file": p.name, "proposed_expect": c.get("expect"),
                    "proposed_evidence": c.get("evidence") if c.get("evidence") != frozen[c["id"]].get("evidence") else None,
                }
    return out


def build(write: bool = True) -> Dict[str, Any]:
    sources = _load_sources()
    decisions: List[Dict[str, Any]] = []
    files: Dict[str, Dict[str, Any]] = {}
    seen = set()
    for set_name in SETS:
        src = HERE / f"{set_name}_cases.json"
        raw = json.loads(src.read_text(encoding="utf-8"))
        v2_cases = []
        for case in raw["cases"]:
            key = _key(set_name, case["id"])
            dec = DECISIONS.get(key)
            new = copy.deepcopy(case)
            if dec:
                seen.add(key)
                for field in dec.get("drop_expect", []):
                    new["expect"].pop(field, None)
                new["expect"].update(copy.deepcopy(dec.get("set_expect", {})))
                if "set_evidence" in dec:
                    new["evidence"] = copy.deepcopy(dec["set_evidence"])
            v2_cases.append(new)
            decisions.append({
                "key": key, "set": f"{set_name}_cases.json", "id": case["id"],
                "changed": new != case,
                "decision": dec["decision"] if dec else "pending",
                "original": {"expect": case["expect"], "evidence_ids": [e["id"] for e in case["evidence"]]},
                "v2": {"expect": new["expect"], "evidence_ids": [e["id"] for e in new["evidence"]]} if new != case else None,
                "sources": sources.get(key, {}),
                "raised_by": dec.get("raised_by", []) if dec else [],
                "page_evidence": dec.get("page_evidence") if dec else None,
                "rationale": dec.get("rationale") if dec else "v2에서 아직 검토하지 않았다. 원본 라벨을 그대로 둔다.",
                "not_adopted": dec.get("not_adopted") if dec else None,
                "open_issues": dec.get("open_issues", []) if dec else [],
                "recorded_answer_comparable": dec.get("recorded_answer_comparable", True) if dec else True,
                "verification": VERIFICATION,
            })
        files[set_name] = {
            "version": f"{raw.get('version', set_name)}-label-v2",
            "derived_from": {"file": src.name, "sha256": _sha(src)},
            "label_version": "v2",
            "notice": "동결 원본의 라벨 버전 2. 같은 140개 ID와 순서를 유지하며, decisions.v2.json의 결정만 반영했다. "
                      "검증 보류: 라벨을 제공된 매뉴얼 쪽에 맞춘 것이며 법률 검증이나 사람 검토 완료가 아니다.",
            "cases": v2_cases,
        }
    missing = set(DECISIONS) - seen
    if missing:
        raise SystemExit(f"decisions name cases that do not exist: {sorted(missing)}")
    ledger = {
        "kind": "artemis_label_v2_decisions", "label_version": "v2",
        "warning": "140 rows = 140 cases, not 140 legal reviews. 'changed' rows were checked against the supplied page text only.",
        "counts": {
            "cases": len(decisions),
            "changed": sum(d["changed"] for d in decisions),
            "by_decision": {k: sum(1 for d in decisions if d["decision"] == k) for k in ("adopted", "adopted_modified", "not_adopted", "pending")},
        },
        "decisions": decisions,
    }
    if write:
        OUT.mkdir(exist_ok=True)
        for set_name, data in files.items():
            (OUT / f"{set_name}_cases.v2.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (OUT / "decisions.v2.json").write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"files": files, "ledger": ledger}


def regrade(write: bool = True) -> Dict[str, Any]:
    """Recorded answers graded against the frozen label and the v2 label. Post hoc:
    v2 was written after reading these answers, so this is not a model evaluation."""
    built = build(write=False)
    rows = []
    for set_name in SETS:
        frozen = manual_ledger.resolve_cases(json.loads((HERE / f"{set_name}_cases.json").read_text(encoding="utf-8"))["cases"])
        v2 = manual_ledger.resolve_cases(built["files"][set_name]["cases"])
        rec = HERE / "runs" / RUNS[set_name] / "run_record.json"
        results = {r["case"]: r for r in json.loads(rec.read_text(encoding="utf-8"))["results"]}
        dec = {d["id"]: d for d in built["ledger"]["decisions"] if d["set"] == f"{set_name}_cases.json"}
        for old, new in zip(frozen, v2):
            r = results.get(old["id"])
            if r is None:
                continue
            shown = r.get("final_output") or r.get("parsed")
            text = json.dumps(shown, ensure_ascii=False) if shown is not None else r.get("output", "")
            a, b = smoke_grader.grade(old, text), smoke_grader.grade(new, text)
            rows.append({
                "key": _key(set_name, old["id"]), "changed": dec[old["id"]]["changed"],
                "comparable": dec[old["id"]]["recorded_answer_comparable"],
                "original": {"passed": a["passed"], "failures": a["failures"]},
                "v2": {"passed": b["passed"], "failures": b["failures"], "flags": b.get("flags", [])},
            })
    report = {
        "kind": "artemis_label_v2_regrade", "post_hoc": True,
        "warning": "v2 labels were written after reading these recorded answers; this is a label check, not a model score.",
        "runs": RUNS,
        "summary": {
            "cases": len(rows),
            "passed_original": sum(r["original"]["passed"] for r in rows),
            "passed_v2": sum(r["v2"]["passed"] for r in rows if r["comparable"]),
            "not_comparable": [r["key"] for r in rows if not r["comparable"]],
            "flipped_to_pass": [r["key"] for r in rows if r["comparable"] and not r["original"]["passed"] and r["v2"]["passed"]],
            "flipped_to_fail": [r["key"] for r in rows if r["comparable"] and r["original"]["passed"] and not r["v2"]["passed"]],
            "flagged_for_human": [r["key"] for r in rows if r["v2"]["flags"]],
        },
        "rows": rows,
    }
    if write:
        OUT.mkdir(exist_ok=True)
        (OUT / "regrade_recorded_answers.v2.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def check() -> List[str]:
    """Committed v2 files that differ from a fresh build (should be none)."""
    built = build(write=False)
    stale = []
    for set_name, data in built["files"].items():
        p = OUT / f"{set_name}_cases.v2.json"
        if not p.exists() or json.loads(p.read_text(encoding="utf-8")) != data:
            stale.append(p.name)
    p = OUT / "decisions.v2.json"
    if not p.exists() or json.loads(p.read_text(encoding="utf-8")) != built["ledger"]:
        stale.append(p.name)
    return stale


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("command", choices=("build", "regrade", "check"))
    args = p.parse_args(argv)
    if args.command == "build":
        print(json.dumps(build()["ledger"]["counts"], ensure_ascii=False))
    elif args.command == "regrade":
        print(json.dumps(regrade()["summary"], ensure_ascii=False, indent=1))
    else:
        stale = check()
        print(json.dumps({"stale": stale}))
        return 1 if stale else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
