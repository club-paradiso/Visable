# 더미/미완성 텍스트 전수점검 (2026-06)

## 배경
D-2(유학) 검색 결과의 개요(`newReq`) 끝에 닫는 괄호 없이 잘린 단편
`" (체류민원 매뉴얼 기준이므로 재외공관 사증발급 서류는 별도 사증 매뉴얼 확인이 필요합니다."`
이 노출되어 사용자 신뢰를 떨어뜨린다는 제보. 이를 계기로 39개 체류자격 전체의
사용자 노출 프로즈/문서 필드를 전수 스캔하여 더미/미완성 텍스트를 점검.

## 점검 방법
`visa_data.json` 전체를 워킹하며 다음을 스캔:
- 괄호/대괄호/낫표 등 짝 불일치(unbalanced brackets)
- 프로즈/개요 필드 말미의 닫히지 않은 괄호(절단 흔적)
- 더미/플레이스홀더 토큰, 빈 괄호, 단독 구두점, 미완성 꼬리
- 사용자 노출 여부(렌더러 억제 토큰 `DOC_PLACEHOLDER_TOKENS` 제외)

## 조치: 삭제(1건)
| 위치 | 처리 |
|---|---|
| `D-2.newReq` (visa_data.json + backend/data/visas.json) | 말미 단편 제거. 개요 본문(유학 대상·제외 교육기관 설명)은 유지. |

근거(안전성): 동일 경고가 올바른 형태로 다른 필드에 이미 보존되어 있어, 경고를
약화하지 않는 **중복 프로즈 제거**(CLAUDE.md 허용 범위)에 해당.
- `D-2.sourceManualStatus.reviewNotes[1]`: "…체류민원 안내매뉴얼 기준이므로 재외공관 사증발급 서류는 별도 대조가 필요합니다."
- `D-2.documents_initial[4].note`: "재외공관 사증발급 서류는 별도 사증발급 안내매뉴얼 대조 필요"

## 보류: 수동 검토 필요(삭제하지 않음)
아래 항목은 **불완전(절단/분할)하지만 실제 요건/내용이 담긴 OCR 추출 텍스트**로,
삭제 시 요건 손실 위험이 있어 CLAUDE.md(요건 삭제·약화 금지)에 따라 **보존**하고
수동 원문 대조 대상으로 기록함. 본 PR에서는 변경하지 않음.

- `D-8.extReq`, `D-8.procedures.extension.summary` — 연장 제출서류 OCR 덤프가 문장
  중간에서 절단됨(닫힘 괄호 누락). "연장허가 연장허가" 중복 흔적 포함.
- `D-9.extReq`, `D-9.procedures.extension.summary` — 동일하게 말미 절단.
- `D-9.procedures.extension.requiredDocs.requiredDocs[4]/[5]`,
  `E-6.procedures.extension.requiredDocs.requiredDocs[5]/[6]` — 단일 서류 항목의
  괄호가 두 배열 항목으로 분할되어 짝 불일치로 보이나, 내용은 연속된 실제 서류 설명.

## 비노출(조치 불요)
`매뉴얼 확인 필요`, `페이지 확인 필요` 등은 `manualRefs[].pageRange` 및 일부 문서
배열에 데이터로 존재하나, 렌더러 `DOC_PLACEHOLDER_TOKENS`/`isDocPlaceholder`에서
이미 억제되어 사용자에게 표시되지 않음 → 데이터 변경 불요.

## 검증
- JSON 유효성, `scripts/sync_visa_data.py --check`(두 파일 동기화),
  `check_visa_text_corruption.py`, `check_required_documents_coverage.py`,
  `audit_duplicate_render_content.py --check`(0 severe), 대표 스키마 검증 모두 통과.
