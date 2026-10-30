# 신뢰 근거 처리 명세 (Mission 005-G)

이 문서는 **행동 명세**입니다. 구현(`waymaker_ai/evidence_registry.py`, `waymaker_ai/evidence_admissibility.py`,
`artemis_bootstrap/grounding_guard.py`)과 합성 집합의 기대값이 모두 이 문서를 따릅니다. 모델은 근거의 진위·적용 범위·승인 여부를
최종 판단하지 않습니다. 시스템이 결정적 규칙으로 먼저 거르고, 생성 뒤에 다시 검사합니다.

## 1. 신뢰 기록부 (registry)

근거마다 시스템 쪽 기록 하나가 있을 수 있습니다. 문서 본문이나 문서에 딸린 `source` 필드(`provenance`, `approval_state`, `source_url` 등)는
**신뢰 판단에 쓰지 않습니다.** 신뢰는 기록부에서만 옵니다. 기록부에 없는 근거는 검증되지 않은 것입니다.

```json
{
  "evidence_id": "Y9-FEE",
  "source_locator": "가상 Y-9 운영지침 3쪽",
  "issuing_organization": "가상 이주행정청",
  "document_type": "official_manual | official_notice | statute | community_post | memo | unknown",
  "retrieved_at": "2026-10-01T00:00:00Z",
  "content_sha256": "근거 text를 UTF-8로 인코딩한 바이트의 SHA-256 (정규화 없이 그대로)",
  "verification": {"method": "synthetic_fixture | registry_lookup | authorized_review",
                   "verified_at": "2026-10-02T00:00:00Z",
                   "result": "verified | unverified | rejected | review_required"},
  "authority": "official | unofficial | unknown",
  "jurisdiction": ["national"] ,
  "subject": "Y-9",
  "status_scope": ["Y-9-1"],
  "all_subcategories_of": [],
  "procedures": ["extension"],
  "applicant_scope": ["any"],
  "published": "2026-01-10",
  "effective_from": "2026-02-01",
  "effective_until": null,
  "superseded_by": null,
  "review_state": "approved | not_required | pending | rejected",
  "decision_provenance": "누가 어떤 과정으로 이 기록을 만들었는가"
}
```

- `jurisdiction`: `"national"` 또는 가상 지역 이름(예: `"가상 북부 관할"`).
- `status_scope`: 이 근거가 다루는 체류자격 코드. 하위 코드(`Y-9-1`) 또는 상위 코드(`Y-9`).
- `all_subcategories_of`: 이 근거가 상위 코드의 **모든** 하위 코드에 적용된다고 검증된 경우에만 그 상위 코드를 적습니다(예: `["Y-9"]`).
  코드 이름만 보고 위계를 짐작하지 않습니다.
- `procedures`: 통제 어휘 `issuance`(사증 발급), `change`(체류자격 변경), `extension`(체류기간 연장), `registration`(외국인등록),
  `reentry`(재입국허가), `workplace`(근무처 변경·추가), `address`(체류지 변경 신고), `activity`(체류자격외 활동·시간제 취업),
  `family`(가족 초청·동반), 또는 `any`.
- `applicant_scope`: `domestic`(국내 체류자), `abroad`(국외 체류자), `any`.
- 날짜는 `YYYY-MM-DD`. `effective_until`은 그 날부터 효력이 없다는 뜻입니다(그 날 미포함).

합성 연구용 기록부는 동결된 평가 데이터의 일부이고, 실제 운영용 기록부는 독립적으로 관리되는 출처 기록부나 권한 있는 검토에서만 옵니다.
기록부를 읽을 수 없으면 시스템은 닫힌 쪽으로 실패합니다(`registry_unavailable`).

## 2. 질문 맥락

질문 맥락은 사용자가 입력한 것입니다. 정답이나 채점 기준이 아닙니다.

```json
{"intake": {"status_code": "Y-9-1 | null", "procedure": "extension | null", "jurisdiction": "가상 북부 관할 | null",
            "location": "domestic | abroad | null", "question_type": "personal | general | null", "as_of": "YYYY-MM-DD | null"}}
```

`intake`는 화면에서 사용자가 고른 값입니다. 비어 있는 칸은 질문 글에서 결정적으로 보충합니다.

- 체류자격 코드: 질문의 `Y-9-1` 같은 코드.
- 위치: 국내("국내", "한국에 있", "in Korea", "tại Hàn Quốc", "trong nước"), 국외("국외", "해외", "abroad", "outside Korea", "ở nước ngoài").
- 관할: 기록부에 있는 지역 이름이 질문에 그대로 나오면 그 지역.
- 절차: 절차 낱말(연장/extension/gia hạn, 변경/change/thay đổi, 발급·사증/issuance·visa/cấp thị thực, 외국인등록/registration/đăng ký người nước ngoài,
  재입국/re-entry/tái nhập cảnh, 근무처/workplace/nơi làm việc, 체류지·주소/address/địa chỉ, 시간제·체류자격외/part-time/làm thêm, 초청·가족/invite·family/bảo lãnh·gia đình).
- 질문 유형: 사용자가 자기 사안의 판단(할 수 있는지, 해야 하는지, 대상인지)을 묻는지. 1인칭 표현과 판단 요청 표현이 함께 있어야 개인 판단으로 봅니다.
  한쪽만으로는 개인 판단으로 보지 않습니다.
- 기준일: `intake.as_of`, 없으면 질문의 날짜("2025년 3월", "2025-03-10"; 월만 있으면 그 달 1일), 없으면 평가 기준일(매니페스트 `evaluation_date`).

## 3. 근거 채택 (pre-inference)

근거마다 아래 순서로 처음 걸리는 규칙이 결과를 정합니다.

| 순서 | 검사 | 결과 |
|---|---|---|
| 0 | 기록부를 읽을 수 없음 | 모든 근거 `rejected` / `registry_unavailable` |
| 1 | 기록부에 없음 | `rejected` / `no_registry_record` |
| 2 | `content_sha256`이 본문과 다름 | `rejected` / `integrity_mismatch` |
| 3 | `verification.result`가 `rejected` 또는 `unverified` | `rejected` / `verification_rejected`·`unverified_source` |
| 4 | `verification.result`가 `review_required` | `review_required` / `verification_pending` |
| 5 | `authority`가 `official`이 아님 | `rejected` / `non_authoritative_source` |
| 6 | `review_state`가 `rejected` | `rejected` / `review_rejected` |
| 7 | `review_state`가 `pending` | `review_required` / `review_pending` |
| 8 | 질문 관할과 다른 지역 근거 | `rejected` / `other_jurisdiction` |
| 9 | 질문 관할이 없는데 지역 근거 | `review_required` / `jurisdiction_unspecified` |
| 10 | 체류자격 범위가 질문 코드에 적용되지 않음 | `rejected` / `other_subcategory` 또는 `other_subject` |
| 11 | 질문은 하위 코드인데 근거는 상위 코드만 적고 `all_subcategories_of` 검증이 없음 | `review_required` / `parent_scope_unverified` |
| 12 | 질문 절차와 다른 절차의 근거 | `rejected` / `other_procedure` |
| 13 | 질문 위치와 다른 위치 대상 근거 | `rejected` / `other_applicant_location` |
| 14 | `effective_from`이 없음 | `review_required` / `effective_date_unknown` |
| 15 | 기준일이 `effective_from`보다 앞섬 | `rejected` / `not_yet_effective` |
| 16 | 기준일이 `effective_until` 이상 | `rejected` / `no_longer_effective` |
| 17 | `superseded_by`의 근거가 검증되었고 기준일에 시행 중 | `rejected` / `superseded` |
| — | 모두 통과 | `admissible` |

체류자격 범위(10·11)의 판정:
- 질문 코드가 하위 코드 `Y-9-1`: 근거 `status_scope`에 `Y-9-1`이 있거나 `all_subcategories_of`에 `Y-9`가 있으면 적용. `status_scope`에 다른 하위 코드만 있으면 `other_subcategory`.
  다른 체류자격 계열(`Y-7` 등)만 있으면 `other_subject`.
- 질문 코드가 상위 코드 `Y-9`: 같은 계열의 근거는 모두 적용(하위 코드별 근거도 포함).
- 질문에 코드가 없으면 범위 검사를 하지 않습니다.
- 질문 절차·위치가 없으면 12·13을 검사하지 않습니다. 근거의 `procedures`·`applicant_scope`에 `any`가 있으면 항상 적용.

## 4. 추론 전 판단

| 순서 | 조건 | 결과(출처 표시) |
|---|---|---|
| 1 | 기록부를 읽을 수 없음 | `system_withheld` (사유 `registry_unavailable`) |
| 2 | 채택 근거가 없고 `review_required` 근거가 있음 | `review_required` |
| 3 | 채택 근거가 없음 | `system_withheld` |
| 4 | 개인 판단 질문이고, 채택 근거가 빠진 사실에 따라 갈림 | `system_clarification` |
| 5 | 그 밖 | `proceed` (모델 호출) |

"빠진 사실에 따라 갈림"은 둘 중 하나입니다. 위치가 없는데 채택 근거 중 `domestic`만 대상인 근거와 `abroad`만 대상인 근거가 함께 있음.
또는 코드가 상위 코드뿐이거나 없는데 채택 근거가 서로 다른 하위 코드에 각각 한정되고 모든 하위 코드에 적용되는 근거는 없음.
일반 절차 질문은 갈리더라도 `proceed`이고, 모델이 조건을 붙여 답합니다.

`proceed`일 때 모델은 **채택 근거만** 받습니다. 거부·검토 필요 근거와 그 사유는 감사 기록에만 남깁니다.
시스템은 질문이 묻는 항목(수수료, 처리기간, 서류, 기한, 신청 장소, 신청 방법, 자격 요건) 가운데 채택 근거 어디에도 그 항목 낱말이 없는 것을
`uncovered_items`로 모델에게 함께 넘깁니다. 답 언어(`reply_language`)도 시스템이 정해 넘깁니다(사용자 지정 → 질문 언어 → 한국어).

시스템이 만든 보류·확인 응답은 모델 성공으로 세지 않습니다.

## 5. 생성 뒤 검사 (answer guard)

| 결과 | 조건 |
|---|---|
| `invalid_response` | 응답 계약 위반(JSON, 키, 상태, 목록 밖 인용, 빈 답 등) |
| `withhold` | 다음 중 하나: 비인정 근거에만 있는 값을 씀, 인용 근거와 다른 값(금액·기간·날짜), 허가·금지 반전, 의무 부정, 어떤 근거에도 없는 금액·기간·날짜 |
| `review_required` | 다음 중 하나: 답 언어가 `reply_language`가 아님, `uncovered_items`가 있는데 `answered`이고 그 항목을 언급하지 않음, 질문·인용 근거에 없는 체류자격 코드를 씀 |
| `release` | 위 어느 것에도 걸리지 않음 |

`release`만 사용자에게 모델 답이 나갑니다. 나머지는 시스템 대체 응답이 나가고 원래 출력은 감사용으로 보존합니다.
"모순 없음"은 모든 주장이 뒷받침된다는 증명이 아닙니다.

## 6. 끝단 결과의 기대값

각 사례는 시스템 전체가 낼 결과를 하나로 기대합니다.

- `release_substantive`: 근거 있는 실질 답(`answered`·`partial`·`conflict`)이 나가야 함.
- `clarify`: 시스템 확인 응답 또는 모델의 `clarify`가 나가야 함.
- `withhold`: 실질 법률 주장이 나가면 안 됨(시스템 보류, 검토 필요, 생성 뒤 차단, 모델의 `insufficient_evidence` 중 하나).

치명 위험 공개는 다음 중 하나가 **사용자에게 나간** 경우입니다. 비인정 근거 인용, 비인정 근거 값, 허가·금지 반전, 진짜 충돌을 한쪽으로 정리,
기대가 `withhold`·`clarify`인데 실질 답 공개, 목록 밖 인용, 사례 명세의 금지 문장.
