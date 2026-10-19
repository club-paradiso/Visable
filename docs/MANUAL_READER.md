# 매뉴얼 원문 읽기 (`manual.html`)

법무부 「사증발급 안내매뉴얼」(2026. 9. 1.)과 「외국인체류 안내매뉴얼」(2026. 9. 18.) 원문을
체류자격(장)과 업무(항목)별로 나눠 보여 주는 화면이다. 기존 `관련 원문` 검색(PDF 쪽 단위 발췌)이
"어느 쪽에 있나"를 찾는 도구라면, 이 화면은 그 장·항목을 처음부터 끝까지 읽는 도구다.

## 데이터 흐름

| 단계 | 파일 |
| --- | --- |
| 원본 (Markdown 변환본 + 그림) | `docs/source-manuals/2026-09/markdown/` |
| 빌드 | `python3 scripts/build_manual_reader.py` (의존성: `scripts/requirements-manual-reader.txt`) |
| 산출물 | `data/manual-reader/catalog.json`, `chapters/<v\|s>/<장>.json`, `search.json`, `assets/manual-reader/img/*.webp` |
| 편집 설명(사람이 씀) | `data/manual-reader/editorial.json` |
| 딥링크 규칙 | `assets/js/manual-reader-route.js` |
| 검사 | `node scripts/check_manual_reader.mjs`, `python3 scripts/build_manual_reader.py --check`, `tests/e2e/manual-reader.spec.mjs` |

빌더가 하는 일은 구조화뿐이다. HWP 레이아웃 표(항목명 칸 | 내용 칸)를 항목 단위로 나누고, 줄머리 기호
(1. 가. ① ❍ - ※ \*)에 따라 들여쓰기 클래스를 붙이고, `제출서류`·`첨부서류` 뒤의 ①②③ 줄을 체크리스트로
표시한다. 원문 문장은 고치거나 줄이거나 순서를 바꾸지 않는다. 빠지는 것은 쪽 넘김 때문에 반복된 항목명,
`목차` 되돌아가기 링크, 장 제목 줄, 표지·로고 그림뿐이며, 그 양(전체 글자의 약 0.3%)은
`catalog.json`의 `preservation`에 장별로 기록되고 검사가 상한(0.5%, 추가 글자 0)을 강제한다.

## 출처 검증

- Markdown 변환본의 SHA-256이 `catalog.json`에 고정되어 있다.
- 같은 판본 PDF에서 따로 추출한 텍스트(`docs/source-manuals/2026-09/extracted/*.txt`)와 줄 단위로 대조해
  사증 98.4%, 체류 98.6%가 일치한다(나머지는 PDF 줄바꿈 차이). 검사 하한은 97%.
- 내용 검토 전이므로 `approval_state`는 `needs_review`이고, 화면에도 `원문 발췌 · 검토 전`을 표시한다.

## 편집 설명의 경계

`editorial.json`의 자격 소개, 쉬운 말 항목 제목, 용어 풀이, 바로가기는 이해를 돕는 Visable 편집 안내다.
요건·서류·기간을 새로 만들지 않으며, 화면에서 `Visable 편집` 표시로 원문과 구분한다.
요건은 항상 장 본문(원문)을 따른다.

## 딥링크

`manual.html#c-<장>.<v|s>[.<항목>]` — 예: `#c-F-6.s.extend`, `#c-D-2.s.parttime`, `#c-dongpo.v.consul`.
세부 약호(F-6-1)는 상위 장(F-6)으로 연결하고, 사증(v)과 체류(s) 항목은 섞지 않는다.
civic 검색의 `관련 원문` 패널은 안내가 해석한 체류자격·업무로 이 링크를 만든다.

## 판본이 바뀌면

1. 새 Markdown·그림을 `docs/source-manuals/<판>/markdown/`에 넣고 `SOURCES`·장 시작 줄(`CHAPTERS_V/S`)을 갱신한다.
2. `python3 scripts/build_manual_reader.py` → `npm run test:manual-reader` → e2e.
