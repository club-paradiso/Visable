# AI 페이지 테마 패리티 보고서 (PHASE 10)

생성: 2026-06-11

## 변경
1. **테마 패리티**: ai.html에 `paradiso:editorial-theme`를 읽는 무플래시 부트스트랩 추가 →
   `<html data-editorial-theme>`. civic_editorial이면 기존 다크 콘솔 그대로(무변경),
   archive_diary면 Kitsch 콘솔 팔레트 적용.
2. **Kitsch 콘솔**: 종이 배경+괘선, 흰 카드+잉크 보더 답변 버블, 파란 전송 버튼(라운드 필),
   와시 칩 예시 질문, 헤더 브러시 워드마크는 invert 필터로 잉크 톤 표시.
3. **진지함 보존**: source-panel/disclaimer/grounding-badge/모달은 팔레트만 조정 —
   문구·크기·의미 무변경. NO SOURCE 경고행은 양 테마에서 고대비.
4. **접근성**: ambient 배경·status-dot 애니메이션에 prefers-reduced-motion 가드 추가(전 테마).
5. **Waymaker 표시 리네임**: 키치에서만 타이틀/헤더/웰컴/답변 카드의 Paradiso AI →
   Waymaker by Paradiso (표시 전용; 쿼터·전송·API 로직 무변경).

## 무변경 확인
- AI 공급자/엔드포인트/쿼터/전송 동작, 법적 고지 문구: 변경 없음.
- PHASE 11 범위의 변경은 출처 패널의 소스-불가 경고 행 1건뿐(ai_grounding_audit.md 참조).
