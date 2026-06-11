# 백엔드 스모크 노트 (PHASE 13 보조)

본 패치의 백엔드 코드 변경: **없음** (backend/data/visas.json은 scripts/sync_visa_data.py로만 갱신).
ai.html 프런트 변경(출처 패널 경고/테마)은 백엔드 계약을 바꾸지 않음.

이 환경에서 실행한 검증:
- `python3 -m json.tool backend/data/visas.json` ✓
- `python3 scripts/sync_visa_data.py --check` (check_repo.sh 단계 [11/14]) ✓
- `bash scripts/check_repo.sh` 전체 통과 ✓ (회귀 게이트 gq_* 포함)

수동 스모크 대상 (배포 환경에서):
- [ ] ai.html에서 채팅 전송 → /api/ask 응답 수신
- [ ] OpenRouter 실패 시 이해 가능한 오류 카드
- [ ] 법령/매뉴얼 검색 실패 시 크래시 없음 + **NO SOURCE 경고 행 표시** (신규)
- [ ] 검색 성공 시 출처 메타데이터 표시 (기존 패널)
- [ ] 프런트 HTML/로그/커밋에 비밀값 부재 (본 감사에서 레포 기준 확인 완료)
- [ ] Railway: LAW_GROUNDING_MODE / LAW_API_OC / OPENROUTER_API_KEY 존재 여부를
      /health · /api/debug/law-grounding/preflight 불리언으로 확인
