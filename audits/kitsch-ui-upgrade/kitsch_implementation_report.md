# Kitsch 테마 구현 보고서 (PHASE 9)

생성: 2026-06-11 · 슬롯: 기존 `archive_diary` (신규 테마 ID 없음)

## 테제
"Paradiso Kitsch is a beloved administrative scrapbook." — 차가운 행정 서류를
아끼는 시민 진(zine)/행정 스크랩북처럼. 장난감 사이트 아님.

## 구현 위치
- `index.html` 스타일시트 말미 `PARADISO_KITSCH_EDITORIAL_THEME_20260611` 블록
  (`:root[data-theme="archive_diary"]` 스코프 전용 — civic_editorial 기본값 무변경).
- `ai.html` `PARADISO_KITSCH_AI_CONSOLE_20260611` 블록 (`html[data-editorial-theme="archive_diary"]`).
- 퍼시스턴스: 기존 `paradiso:editorial-theme` 키 그대로 (부트스트랩/토글 로직 무변경,
  ai.html에 동일 키 읽는 부트스트랩 추가).

## 디자인 시스템
- 표면: 클라우드/크림 종이(`--kit-paper/--kit-cloud`) + 28px 가로 괘선(정적).
- 잉크: `--kit-ink #26221B` 아웃라인 + 하드 오프셋 섀도(스티커/전표 느낌).
- 액션: 파랑 `--kit-blue #2E5C9E` (검색 버튼, 링크, vc 헤더 엣지, FAB 스파크).
- 핑크 `--kit-pink #D8527C`: **Waymaker/AI 표면에만** (게이트웨이 AI 카드 탭, FAB 강조어,
  ai.html answer-kicker). 그 외 사용 금지 유지.
- 버터 `--kit-butter #F2D272`: 주의/검토 시맨틱 전용 (상황별 그룹 엣지, 재량 노트 배경, 보관철 탭).
- 페이퍼워크 아티팩트: 인덱스 탭(히어로 메모카드·doc-group-title), 메모 슬립(서류 그룹),
  영수증 스트립+바코드형 디바이더(stat 카드, 푸터 CTA), 파일-폴더 카드(게이트웨이),
  와시테이프 칩(추천 키워드), 공식출처 태그는 기존 배지 유지.
- 금지 준수: 특정 인물/레이블/앨범/사이트 모방 없음, 무지개/글리터 없음, 무한 장식 루프 없음
  (호버 리프트는 유한 트랜지션), 법령·출처·경고 블록 장식 없음.

## Waymaker 표시 리네임
- index.html: `paradisoApplyWaymakerDisplayBranding()` — 텍스트 노드만 스왑, 원본 innerHTML을
  dataset에 보관해 시빅 복귀 시 복원. 적용 트리거: 테마 적용 시, `paradiso-language-applied`
  이벤트, `#rlist` MutationObserver(동적 시나리오 버튼). href/API/스토리지 키/식별자 불변.
- ai.html: 동일 원리의 단독 스크립트(타이틀·헤더·웰컴·동적 답변 카드, chatHistory 옵저버).

## 모션
- 신규 키프레임 0개. 키치 인터랙션은 유한 transform 트랜지션만, reduced-motion에서 해제.
- 기존 IntersectionObserver 리빌(initScrollReveal)은 무변경 유지(콘텐츠 미표시 방지 워치독 포함).

## 다크 모드
- archive_diary × body dark: 본문 콘텐츠는 기존 다크 토큰 우선(가독성 회귀 방지),
  키치 종이면은 다크 토큰으로 강등(보더/섀도 해제). 라이트/다크 토글·퍼시스턴스 무변경.
