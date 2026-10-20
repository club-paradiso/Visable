# Visable 디자인 감사 — 2026-10-20 (universal UX/UI 프롬프트 적용 1차)

## 프로젝트 정보
- 대한민국 비자·체류 정보 안내 플랫폼 (civic-tech), 공식 출처 기반
- 핵심 사용자: 디지털 리터러시가 낮고 스트레스를 받는 체류 외국인
- 기존 시각 언어: 따뜻한 종이+잉크 (warm paper + ink) — DESIGN.md에 이미 체계화됨
- 토큰: primary #177366 / deep #0B4F44 / accent #D95C47 / paper #F7F4EF·#FFFCF5 / text #1C1F29
- 타이포: Pretendard Variable 단일 패밀리

## 판정: 리디자인 불필요, 폴리시 대상으로 확정
- 이미 DESIGN.md 디자인 시스템 + 2026-09 design-qa 통과 + WCAG 토큰 체크 스크립트 보유
- Anti-slop 스캔 결과 (10개 페이지):
  - "Inter" 히트 → 전부 "Interview" 오탐. 실제 Inter 사용 없음
  - linear-gradient → nationality-interview-hub 1건 (맥락상 허용 범위)
  - ALL-CAPS 키커 ("IMMIGRATION DOCUMENTS", "DOCUMENT GUIDE") → 공문서 질감의 의도적 선택으로 판정, 유지
  - middot(・) / em-dash(—) → 한국어 카피의 정상 구두점, 문제 없음
  - H1 "서류," 줄바꿈 → 의도된 타이포그래피, 오탐이었음

## 적용된 수정 (이번 패스)
1. `immigration-checklists.html` — mode-nav의 장식용 이모지(✨/🔍)를 인라인 SVG(sparkles/search, Lucide 스타일, currentColor)로 교체. 기존 `aria-hidden` 유지.
2. `new-home.html` — 모달 닫기 버튼 3개의 ✕ 텍스트를 SVG x 아이콘으로 교체 (aria-label="닫기" 유지).

## 다음 패스 후보 (미적용)
- index.html (1.4MB) 히어로 카피 "답이 보이는 한국 생활." — 현 상태 양호, 손댈 필요 없음
- ai.html (Waymaker) 네비 라벨/설명 구조 — 정상 확인됨
- 이모지 259건(index.html) 중 기능적 이모지(⚠️ 경고, ✅/❌ 체크리스트 상태)는 유지가 맞음
