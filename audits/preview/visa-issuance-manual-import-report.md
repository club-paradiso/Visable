# PreView 사증발급 매뉴얼 임포트 감사 보고서 — 2026-07-04

> 범위 한정: 이 보고서는 PreView의 '매뉴얼 기준 참고' 레이어를 위한 최소 추출 기록이다. 법적 정확성 전수 재검증이 아니며, 매뉴얼은 PreView의 주 소스가 아니라 참고 레이어다. 면책·주의·출처 경고 문구는 어떤 단계에서도 약화하지 않는다.

## 입력
- 입력 파일: `backend/data/sources/manuals/260617_visa_manual_readable.txt`
- 추출 방법: `text_read_utf-8`
- 상태: **ok**

## 도구 가용성 로그
- dedicated HWP extraction skill: not available in this repo
- HWP->DOCX conversion skill: not available in this repo

## 추출 통계
- 텍스트 길이: 458,881 chars
- 한글 비율: 0.595
- 감지된 매뉴얼 버전: 2026.6

## 생성 레코드

| code | purposeCategory | headingKo | page | 발급 경로 단서 |
|---|---|---|---|---|
| C-3 | short_visit | 단기방문(C-3) | 27 | 매뉴얼 해당 절에서 확인된 발급 경로 단서: 사증발급인정서 관련 절, 전자사증 관련 절, 제출서류 절 — 적용 대상과 세부 요건은 매뉴얼 원문과 |
| C-4 | business | 단기취업(C-4) | 51 | 매뉴얼 해당 절에서 확인된 발급 경로 단서: 첨부서류 절 — 적용 대상과 세부 요건은 매뉴얼 원문과 관할 재외공관 공식 안내 확인 필요 |
| D-2 | study | 유학(D-2) | 62 | 매뉴얼 해당 절에서 확인된 발급 경로 단서: 사증발급인정서 관련 절, 첨부서류 절, 제출서류 절 — 적용 대상과 세부 요건은 매뉴얼 원문과 관할 |
| D-4 | study | 일반연수(D-4) | 73 | 매뉴얼 해당 절에서 확인된 발급 경로 단서: 사증발급인정서 관련 절, 첨부서류 절 — 적용 대상과 세부 요건은 매뉴얼 원문과 관할 재외공관 공식 |

## 산출물
- 스냅샷: `/home/user/Paradiso/data/preview/visa-issuance-manual.snapshot.json` — 기록됨

## 경계 확인
- 매뉴얼 원문 전체를 저장하지 않았다 (헤딩·경로 단서만 기록).
- 요구서류 목록을 새로 만들지 않았다.
- 모든 레코드는 `evidenceLevel: manual_reference`와 `requiresOfficialMissionCheck: true`를 갖는다.
- 최종 판단은 관할 재외공관 공식 안내를 따른다 (공식 원문 확인 필요).
