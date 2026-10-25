# Mission 002 Phase 1 — 법령 데이터 수리

후속 재검토: [Phase 1.1 검증 범위·최신 시행규칙·서식 영향](legal-phase-1-1-review.ko.md).
아래 표는 최초 수리 내역이며, 시행규칙은 후속 검토에서 MST 291289 / 2026-10-23으로 갱신했다.

2026-10-25 · 기준 main `601b514e1ef08829a1df7b164dfe63eccbc073d0`에서 독립 분기.
`CLAUDE.md`, Mission 001 보고서, `17-mission-002-plan.md`, `law-identity.md`,
2026.10 매뉴얼 승격·manualRef 감사 기록을 먼저 확인했다.
2026.10 승격, 인용 956건 재표기, 제73조 수수료 수리는 반복하지 않는다.

## 공식 식별 정보 재확인과 변경 전후

| 위치/법령 | 변경 전 | 변경 후 | 공포일 / 시행일 | 공식 원문 |
|---|---|---|---|---|
| author_rules 출입국관리법 | MST 272921, 시행 2026-01-23 | MST 290729, 법률 21857호 | 2026-08-04 / 2026-10-02 | [법제처](https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq=290729) |
| author_rules 출입국관리법 시행령 | MST 289697, 시행 2026-09-15 | MST 290501, 대통령령 36728호 | 2026-09-29 / 2026-10-02 | [법제처](https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq=290501) |
| nationality registries 시행령 | 243829, 2022-07-12 | 246165, 대통령령 33082호 | 2022-12-20 / 2022-12-20 | [법제처](https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq=246165) |
| nationality registries 시행규칙 | 262177, 2024-04-29 | 291055, 법무부령 1161호 | 2026-10-02 / 2026-10-02 | [법제처](https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq=291055) |
| document_help 시행규칙 링크 | 266161 | 289833 + efYd=20260915 | 2026-09-15 / 2026-09-15 | [법제처](https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq=289833) |
| D-3 작성자 요약의 규칙 제목 | …관한 지침 | …관한 훈령 (1414호) | 2022-04-14 / 2022-04-14 | [법무부 공표](https://www.moj.go.kr/bbs/moj/154/558261/artclView.do) |
| 동포 매뉴얼 추출기의 작성자 쪽 제목 | 제2026-35호를 단독 정답처럼 표기 | 원문 제2026-35호와 공식 제2026-65호의 불일치 명시 | 공식 2026-02-12 / 2026-02-12 | [공식 고시](https://www.law.go.kr/LSW/admRulInfoP.do?admRulSeq=2100000275060&chrClsCd=010201) |

국적법 두 registry의 링크를 함께 고쳤다. 새 확인은 **표제·식별자·시행일 확인**이며
조문/서식 재검증이 아니다. `contentVerified`는 false로 내려 과장하지 않는다.
`checkedAt`은 이 확인일을 기록하고, author_rules의 `checked_on=2026-09-22`는
기존 조문 요약 검토일이므로 임의로 새 날짜를 찍지 않는다.

고시 본문은 공개 법제처 자료를 법령mcp로 조회해 번호·시행일을 확인했다.
외부 구현 코드는 읽거나 복사하지 않았다. 직접 웹 경로 일부가 본문을 못 반환한 사실과
대체 공개 원문 조회 방법은 [legal-evidence.json](legal-evidence.json)에 기록했다.

## 보존한 것과 생성 파일

- 원본 매뉴얼 HWP/PDF·원문 인용·raw 전사·코퍼스의 제2026-35호 표기를 그대로 둔다.
  공식 고시와의 충돌을 원문 수정으로 덮어 쓰지 않는다.
- D-3에서는 사람이 작성한 extension notes의 **제목 한 단어**만 바꿨다.
  연수기간, 요건, raw extReq/summary 전사, 제출서류 목록은 그대로다.
- `author_rules.py` → `guidance-rules-202609.json` → `build_status_coverage_manifest.py`
  → `status-guidance-202609.json` → `sync_visa_data.py` 배포 사본 순으로 생성했다.
- source bundle digest 변화로 stale이 된 search-suggest-index는 전용 빌더로 재생성했다.
- D-3 작성 파일 → `scripts/visa/build_visa_data.py` → visa_data 및 배포 사본으로 반영했다.
  생성된 visa_data 변경도 제목 한 단어뿐임을 diff로 확인했다.
- 2026.10 원본 네 파일 SHA-256을 기록하고 회귀 테스트에서 확인한다.
- 제73조 현행 현금 규칙 및 2027-09-16 KST 자동 전환을 그대로 검증한다.

## 검증과 잔여 위험

회귀 테스트: `backend/tests/test_mission_002_legal_data.py`.
기존 데이터 빌더 --check, 동기화, nationality/document 안내 검증과 전체 check_repo를 실행한다.
테스트·CI의 최종 실행 상태는 이 PR 본문과 check 실행 링크에서 확인한다.
실험 패키지의 오래된 판본 승인 가정 테스트는 main에서 1개 실패함을 별도 확인했고,
B-fixed PR에서 승인 2026.10 / 구판 경고를 함께 검사하도록 수리한다. 데이터 PR은 독립이다.

남는 위험:

1. 공식 헤더만 새로 확인했으므로 국적법 서식 개정·별지 적합성은 확인되지 않았다.
2. 출입국관리법/시행령 조문 요약은 이번에 다시 작성·검증하지 않았다.
   Mission 001의 해당 조문 변경표식 대조와 이번의 버전 식별 재확인은 구분한다.
3. F-4 원문 번호 불일치는 해결된 원문이라고 표시할 수 없다. 추출기 작성자 제목에서는
   공식 번호와 충돌을 명시했지만 기존 원문 코퍼스는 보존한다. 검색 결과의 충돌 노출은 후속 검토 대상이다.
4. 미검토 manualRef 303건, SOURCE_ONLY 변경 곳, 체류 PDF 재현 확인은 기존 감사의 잔여 과제다.
5. 법제처 이력/부칙·시행일별 본문 API 통합은 다음 단계다. 이번 메타데이터 수리가
   모든 법령의 최신성·법적 정확성을 보장하지 않는다.

후속 순서: 원문 충돌 검토 → 서식/인용 사람 검수 → 시행일·부칙 통합 → 검수된 benchmark v1.
이번 PR은 병합·운영 배포하지 않는다.
