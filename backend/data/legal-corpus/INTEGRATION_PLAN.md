# INTEGRATION PLAN — 기존 Visable 법령 엔진과의 연동 방안

## 현재 상태 (이 PR에서 구현한 것)

읽기 전용 어댑터 `backend/services/legal_corpus/adapter.py`를 추가했습니다. 기존 파일은 **하나도 수정하지 않았습니다**.

- `backend/data/enforcement/legal_rules.json` — 읽기만 함 (별표 7 비교 대상). 교체·변경 없음.
- `backend/services/enforcement_rules.py`, `lib/enforcement-fallback.js`, `lib/enforcement-law-grounding.js`, `lib/enforcement-law-validity.js`, `lib/enforcement-precedent-grounding.js` — 분석만 했고 변경 없음.
- 기존 처분 예측의 금액·처분 결과는 어떤 경로로도 변경되지 않습니다.

## 어댑터가 제공하는 것

`LegalCorpus` 클래스가 두 가지 조회를 제공합니다.

- `get_article(slug, article_id, on_date)`: 특정 날짜에 시행 중이던 버전의 조문 원문과 확실성 상태를 반환합니다.
  1. 날짜를 커버하는 **한국어 법령 버전**을 코퍼스에서 고릅니다.
  2. 커버하는 버전이 없거나 해당 조문이 없으면 추측하지 않고 `VERIFICATION_REQUIRED`를 반환합니다.
  3. 조문 텍스트는 해당 버전의 `articles.ko.json`에서만 가져옵니다.
  4. 영문 대응 상태를 함께 반환하고, 영문본이 해당 버전보다 오래됐으면 `TRANSLATION_OUTDATED` 노트를 붙입니다.
- `version_coverage(slug, start, end)`: 위반 기간 [start, end]를 커버하는 저장 버전 목록을 반환합니다. 기간이 두 버전에 걸치면 두 버전을 모두 반환하고, 시작점 이전에 공백이 있으면 `hasGap: true`와 함께 `VERIFICATION_REQUIRED`를 반환합니다.

반환 상태 어휘 (기존 grounding 모듈의 표시 관례와 충돌하지 않도록 코퍼스 전용으로 정의):

| 상태 | 의미 |
| --- | --- |
| `LOCAL_OFFICIAL_SNAPSHOT` | 적용 버전이 최신 저장 스냅샷이며 공식 출처로 검증됨 (실시간 재검증은 아님) |
| `HISTORICAL_VERSION_VERIFIED` | 적용 버전이 보존된 과거 버전이며 검증됨 (과거 위반 사건의 일반적 경우) |
| `COVERED_BY_STORED_VERSIONS` | 위반 기간 전체가 저장 버전들로 커버됨 (`version_coverage`) |
| `VERIFICATION_REQUIRED` | 커버되지 않는 기간이 있어 확정적 근거를 제시할 수 없음 |
| `TRANSLATION_OUTDATED` | (부가 표시) 대응 영문본이 해당 한국어 버전보다 오래됨. 한국어 원문이 기준 |

`LIVE_VERIFIED`는 이 어댑터가 반환하지 않습니다. 실시간 API 검증은 별도 단계이며, 로컬 스냅샷만으로 실시간 검증이 끝난 것처럼 표시하지 않습니다.

금액 계산은 어댑터의 책임이 아닙니다. 금액은 기존의 검증된 결정론적 계산 엔진(`enforcement_rules.py` + `legal_rules.json`)이 계속 담당하고, 코퍼스는 **근거 조문과 기준 버전의 일치 여부**만 제공합니다.

## 기존 파일 분석 메모

- `legal_rules.json`의 근거 표기(시행규칙 제86조·별표 7, 개정 2026-01-23, flSeq 161124779)는 이번에 수집한 현행 별표 7(flSeq 170813013, 같은 개정일)과 금액이 일치함을 확인했습니다. flSeq가 다른 것은 파일 교체 때문으로 보이며, 금액 차이는 없습니다. 기록 정합성을 위해 향후 규칙 파일 갱신 시 새 flSeq로 출처를 갱신할 것을 권합니다 (이 PR에서는 변경하지 않음).
- `enforcement_rules.py`에는 이미 시행령 제26조의2 + 법무부고시 기반의 E-1~E-7 신고 구분 로직이 있습니다. 이번에 수집한 고시 원문(법무부고시 제2020-212호)이 그 로직의 근거 문서와 일치함을 확인했습니다.

## 다음 단계 (별도 PR로 제안)

1. **근거 표시 연결**: 사범처리 결과 화면의 근거 조문을 어댑터 경유로 가져오고, 상태(`LOCAL_OFFICIAL_SNAPSHOT` 등)를 사용자에게 그대로 표시합니다. 불확실한 기간은 기존 불확실성 안내를 약화하지 않는 방향으로 표시합니다.
2. **버전 일치 게이트**: 계산 규칙 파일의 `effectiveFrom`과 코퍼스 별표 7의 개정일이 어긋나면 CI에서 경고를 냅니다 (자동 차단은 하지 않음).
3. **실시간 대조 (선택)**: 운영 환경에서 DRF OC를 발급·등록할 수 있게 되면, 주간 동기화에 더해 사건 조회 시점의 현행 MST 대조를 `korean_law_client.py`와 연결합니다. 그 전까지 `LIVE_VERIFIED` 표시는 사용하지 않습니다.
4. **P1 확장**: 난민법·국적법 등은 레지스트리 등록 + 우선 조문 지정만으로 같은 파이프라인에 태울 수 있습니다.
