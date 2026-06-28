# Claude Design 프롬프트 — Visable by Paradiso 리브랜드 테마 재구성

이 문서는 Claude Design(또는 Claude Code의 디자인 패스)에 **그대로 붙여넣는 프롬프트**다.
세 토스 가이드(`consumer-ux-guide.md`, `ux-writing.md`, `components.md`)와
리브랜드 Design.MD(`docs/design/REBRAND_VISABLE_DESIGN.md`)를 입력으로 함께 첨부/지정한 뒤 실행한다.

사용법: 아래 `── PROMPT START ──` ~ `── PROMPT END ──` 사이를 복사 → Claude Design 세션에 입력.
참조 파일 3종과 Design.MD를 같은 세션에 첨부하면 가장 정확하다(미첨부 시에도 프롬프트가 핵심을 자체 포함).

---

── PROMPT START ──

너는 Paradiso 디자인 시스템을 담당하는 시니어 프로덕트 디자이너다. 지금 **House-of-Brands 리브랜드**의 비주얼·UX를 재구성한다. 장식 복제가 아니라 *원칙*을 옮기는 작업이다.

## 컨텍스트 (브랜드 전환)
- 기존: Branded House — 모든 게 "Paradiso X".
- 신규: House-of-Brands.
  - **Club Paradiso** = 스튜디오/하우스(감성·디아스포라→낙원 서사).
  - **Visable by Paradiso** = 비자·체류 정보 제품(이성·명료). 구 "Paradiso" 본체 = `index.html`.
  - **New Home by Paradiso** = 국적·귀화(`new-home.html`).
  - **Waymaker by Paradiso** = AI 도우미(`ai.html`, 표기 유지).
- 핵심: "Paradiso가 비자 플랫폼으로 안 와닿는다"를 *이성 제품(Visable) / 감성 하우스(Paradiso)* 분업으로 푼다.

## 반드시 먼저 읽을 입력
1. `docs/design/REBRAND_VISABLE_DESIGN.md` — 토큰·테마·락업·라이팅 규칙(이 작업의 단일 진실원본).
2. `consumer-ux-guide.md`(TDS) — 브랜딩·다크패턴·UX라이팅·그래픽·해상도.
3. `ux-writing.md`(TDS) — 보이스톤 5원칙.
4. `components.md`(TDS) — 컴포넌트 규율.
5. `docs/design/PARADISO_UX_DIRECTION_LOCK.md` §2 — 절대 보존 계약.

## 해야 할 일 (Deliverables)
1. **테마 토큰**: Design.MD의 코어 토큰 + `visable`/`paradiso-warm`/`visable-dark` 테마 변형을 CSS 커스텀 프로퍼티로 산출. 기존 변수에 **additive**(접두사 충돌 없이), 아무 것도 삭제·리네임하지 않는다.
2. **락업 적용**: 히어로·푸터·About·출처 블록에 `Visable by Paradiso`(워드마크 800/-0.02em + endorser 0.8125rem/500/opacity .72). 협소 UI만 단독 `Visable`. 한글 디스크립터 `Visable · 비자·체류 안내` 병기.
3. **Visable = clarity-forward 재구성**: 토스식 정보 위계·여백·컴포넌트 규율 적용. 한 화면 = 하나의 주행동. 브러시 워드마크·아나그램·kitsch 장식은 제품 표면에서 제거하고 **About/하우스(Club Paradiso) 섹션으로 이동**.
4. **UX 라이팅 하이브리드 패스**(아래 체크리스트): UI·안내는 토스 해요체로, 면책·경고는 현 공식 톤 보존.
5. **다크패턴 5종 차단** 검증.
6. **New Home / 하우스**는 warm editorial(종이+잉크·브러시·아나그램) 유지.

## 토스 가이드에서 가져오는 것 (원칙 — 자체 포함 체크리스트)
**UX 라이팅 (ux-writing.md):**
- 해요체 일관 적용 (예: "조회하십시오"→"찾아볼게요").
- 능동형 ("검색되었습니다"→"찾았어요").
- 긍정형 ("결과가 없습니다"→"다른 키워드로 찾으면 나올 수 있어요").
- 캐주얼 경어, 과도한 '~시/께' 제거.
- '명사+명사' 풀어쓰기.
- 다이얼로그 왼쪽 버튼 = **닫기**(취소 아님).
**다크패턴 (consumer-ux-guide.md):**
- 진입 즉시 바텀시트/알림동의 금지, 뒤로가기 트랩 금지, 탈출구 항상 제공, 예상 못한 광고 금지.
- **CTA는 다음 행동을 말한다** — 버튼에 가치문구 반복 금지, 모호한 "확인" 대신 "서류 목록 보기".
**그래픽 (consumer-ux-guide.md):**
- 한 화면 핵심 그래픽 1개, 문맥 적합, 장식 파티클·과한 그라데이션 금지, 라이트/다크 중간 명도.
**컴포넌트 (components.md):**
- 커스텀 UI보다 일관된 소수 컴포넌트. 탭바 사용 시 플로팅·2~5개 형태 원칙.

## 절대 하지 말 것 (하드 제약 — 위반 시 산출물 폐기)
- ❌ **토스 블루(#3182F6)·토스 로고·토스 그래픽 자산 차용 금지.** 토스에서 가져오는 건 원칙뿐, 자산 아님(파트너 구분). Emerald(#0EA37B) 단일 강조 유지.
- ❌ 면책·공식출처 경고·불확실성·검토필요 고지를 해요체로 약화 금지. "최종 판단은 HiKorea·1345·관할 출입국·외국인관서에서 확인하세요" 류는 **원문 톤 보존**.
- ❌ 마크업 구조 변경 금지: 모든 `id`를 같은 의미적 위치에 유지, `data-action`·인라인 `onclick`·`data-vcode/-type/-subidx` 유지, `<body class="landing" data-theme="light">` 유지, `<head>`의 `window.PARADISO_BACKEND_URL` 2줄 유지, `<body>` 끝 메인 `<script>` 바이트 보존.
- ❌ 코드 식별자 `PARADISO_*`(예: `PARADISO_BACKEND_URL`) 리네임 금지 — **사용자 표면 문자열만** 교체.
- ❌ 신규 웹폰트·React/Babel·새 외부 런타임 추가 금지(Pretendard 단독, 정적 HTML 유지).
- ❌ `visa_data.json`·`backend/data/visas.json`·`doc_master.json` 편집 금지(데이터 무관 작업).
- ❌ 숫자 접미사(`Visable 39`)·`Moonshot` 등 금칙어 생성 금지.
- ❌ WCAG: Emerald + 흰 텍스트 금지(AA 미달). Primary는 `primary-deep`+`neutral`.

## 산출 형식
1. 변경 파일별 **diff 또는 교체할 블록**(전체 파일 재작성 금지 — additive/표면 교체).
2. 적용한 토스 원칙 ↔ 변경 지점 매핑 표.
3. 보존 계약 셀프 체크리스트(각 항목 ✅).
4. 검증 명령 결과:
   - `bash scripts/check_repo.sh` (4단계 통과)
   - `grep -c '^<!DOCTYPE html>' index.html` = 1, `<html`/`</html>`/`<body` 각 1
   - `grep -nE 'react\.development|babel/standalone|type="text/babel"|id="root"|src/main\.tsx' index.html ai.html` = 빈 결과
   - 금칙어 grep = 빈 결과
5. 미해결·판단 필요 항목은 추측하지 말고 **질문 목록**으로 분리.

먼저 위 입력 5종을 읽고, *변경 계획(파일별 범위)*을 제시한 뒤 승인받고 진행하라. 한 번에 한 파일씩, 작고 되돌릴 수 있게.

── PROMPT END ──

---

## 운영 노트 (프롬프트 밖, 사람용)

- **왜 "패스" 단위인가.** `index.html`은 1.2MB 단일 파일이고 보존 계약이 빡빡하다. 한 번에 재생성하면 깨진다. 위 프롬프트는 *additive 토큰 → 락업 → 카피 하이브리드 패스 → 장식 이동*을 분리 실행하도록 유도한다(기존 `CLAUDE_DESIGN_INTEGRATION_AUDIT.md` §8의 PR 시퀀스와 동형).
- **첨부 우선순위.** Design.MD + 3개 토스 파일을 같은 세션에 넣는 게 최선. 토큰 한도로 어렵다면 Design.MD만 첨부해도 프롬프트가 토스 핵심을 자체 포함한다.
- **검증 게이트.** 각 패스 후 `scripts/check_repo.sh`와 위 grep을 돌려 보존 계약을 확인하기 전엔 다음 패스로 넘어가지 않는다.
- **브랜드 자산 TODO.** `Visable` set-type 워드마크와 `by Paradiso` 엔도서 락업을 `assets/brand/`에 신규 제작해야 한다(현 `paradiso-wordmark-brush-*.png`는 하우스/New Home용으로 잔류). 이 프롬프트는 코드/테마 작업이며, 워드마크 그래픽 제작은 별건(Figma/Canva)으로 분리.
