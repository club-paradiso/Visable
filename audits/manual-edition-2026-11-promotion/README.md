# 2026.11 판 체류 매뉴얼 승격 (2026-11-03)

소유자가 2026-11-03에 채팅으로 체류 매뉴얼의 기준 판본을 정했습니다. 사증 매뉴얼은 이번에 새로 받지 않았으므로 2026.10(2026-10-19) 그대로입니다.

| 구분 | 판본 | 원본 파일 |
| --- | --- | --- |
| 체류 | 외국인체류 안내매뉴얼 2026.11 (파일 날짜 2026-11-02, 813쪽) | `docs/source-manuals/2026-11-02/stay_manual_261102.hwp` · `.pdf` |
| 사증 | 사증발급 안내매뉴얼 2026.10 (파일 날짜 2026-10-19, 519쪽) | 변경 없음 |

이 문서는 법령 재검증이 아닙니다. 승격 기록, 확인한 것과 확인하지 못한 것, 사람이 검토해야 할 항목을 정리한 것입니다.
"2026-11-02"는 파일 이름의 날짜입니다. 표지 "2026. 11."은 확인했지만 시행일은 확인하지 못했습니다.

## 1. 원본과 PDF

| 파일 | 바이트 | SHA-256 |
| --- | ---: | --- |
| `stay_manual_261102.hwp` | 3,266,560 | `cb9f30f76effdb6fc8aeaae1b41b0fd115b7ba1aa2378fcd9dff9e4af9c52d1c` |
| `stay_manual_261102.pdf` | 15,509,885 | `00037cc5c47d23b21c26dbd9f679a75af41a0b0bdea98342dcb49758e44dc933` |

- HWP의 해시는 먼저 들어와 있던 검토 전 기록(PR #740)과 같습니다.
- 공식 PDF는 없었습니다. 한컴오피스 한글 Viewer 12.31로 HWP를 인쇄해 저장한 PDF를 소유자가 보냈습니다. 쪽 번호는 이 PDF 기준입니다.
- 이 PDF는 **813쪽**입니다. 2026.10 PDF(812쪽)보다 한 쪽 많습니다. 공식 PDF의 쪽 수는 확인하지 못했습니다.

### PDF 검증 결과

- 쪽 수 813쪽, 표지 "2026. 11." 확인. 모든 쪽에 글자층이 있고 깨진 글자(U+FFFD)는 없습니다.
- HWP 추출본과의 전체 글자 일치율은 판별력이 없었습니다. 표 안의 글이 HWP 추출본에서는 문단으로 풀려 순서가 다르기 때문에, 이미 승인된 2026.10 쌍(PDF와 HWP)에서도 같은 수준(약 82%)이 나옵니다. 그래서 일치율로 PDF가 HWP와 같다고 말하지 않습니다.
- 대신 변경 부분을 맞춰 봤습니다. 2026.10 PDF와 2026.11 PDF를 줄 단위로 비교하고(쪽 번호 줄 제외), 같은 방식 HWP 비교(`audits/manual-refresh-20261102/README.md`)의 16개 변경과 대조했습니다.
  - 16개 변경이 모두 PDF에 있습니다. 문단 두 개는 줄바꿈이 달라 첫 검색에서 빠졌지만 직접 찾아 확인했습니다("한국어능력 미제출자 … 특례를 적용받아 …", 추천서의 "확실하인 것이 확실하며" 겹침 오탈자).
  - 그 밖에 바뀐 곳은 줄바꿈, 쪽 번호, 붙임 번호가 한 칸씩 밀린 것, 쪽 경계에서 "목차" 링크 위치가 옮겨진 것뿐입니다. 서류나 요건 문구가 더 바뀐 곳은 찾지 못했습니다.
  - 2026.10 PDF에는 있던 E-7-4R 연장 서류 목록(12개 필수 + 5개 추가)이 줄고 8개 필수로 바뀐 것도 PDF에서 확인했습니다.
- **하지 않은 것:** 2026.10에서 사증 PDF로 했던 것 같은 재현 시험(같은 방법으로 이미 승인된 판을 다시 뽑아 기존 PDF와 쪽마다 비교)은 체류 PDF에 대해 하지 않았습니다. 이 PDF가 한글 Viewer 12.31의 출력이라는 것은 소유자 설명에 따른 것입니다.

## 2. 승인 기록

- `data/manual_approval_index.json`
  - `stay_manual_2026_11_02_pdf`(새), `stay_manual_2026_11_02_hwp`를 `approved`로 기록했습니다. 검토자 michaelcool1009@gmail.com, 날짜 2026-11-03.
  - `stay_manual_2026_10_19_pdf`, `stay_manual_2026_10_19_hwp`는 `superseded`(`superseded_by`, `superseded_date` 2026-11-02)로 바꿨습니다.
  - 파생 Markdown `stay_manual_2026_11_02_md`는 `needs_review`입니다. 2026.10 Markdown은 그대로 `needs_review`이고 색인에서는 이전 판이라 직접 근거가 아닙니다.
- 이 승인은 **판본 선택**을 기록한 것입니다. 원문을 한 줄씩 대조했다는 뜻이 아닙니다. 파일 날짜는 법적 시행일 확인이 아닙니다. 두 승인 기록의 `approval_note`에도 같은 내용이 있습니다.
- `data/source_registry.json`: 2026.11 PDF·HWP를 `active`로, 2026.10 PDF·HWP를 `deprecated`와 `superseded_by`로 바꿨습니다. 검증기가 같은 키워드의 첫 항목을 고르므로 PDF 항목을 HWP 항목 앞에 두었습니다.
- `docs/source-manuals/source_manifest.json`: `current`의 체류 항목을 2026.11 PDF(HWP는 `alternate_source_files`, Markdown은 `derived_texts`)로 바꾸고, 2026.10 항목은 `archived_previous_current`로 옮겼습니다. 검토 전 목록(`pending_review_editions`)에서 2026.11 HWP를 뺐습니다.
- `data/schemas/source_grounding_schema.json`의 체류 판본 불변식을 2026.11 / 2026-11-02로 올렸습니다.
- 배포용 사본(`backend/data/knowledge_deploy/`)은 `scripts/sync_visa_data.py`로 맞췄습니다.

## 3. 말뭉치, 색인, 쪽 대응

- `scripts/build_current_manual_corpus.py`: 2026.11 PDF를 쪽별로 읽어 `data/manual-corpus/stay_manual_2026_11_02_pdf.json`(813쪽)을 만들었습니다. 카탈로그는 사증 519 + 체류 813 = 1,332쪽입니다.
- Markdown: 소유자가 Markdown을 보내지 않아 `npx kordoc@4.24.1`로 HWP를 변환했습니다(`docs/source-manuals/2026-11-02/markdown/`). 같은 변환기로 2026.10 HWP를 변환하면 저장소의 2026.10 체류 Markdown과 바이트까지 같습니다(그림 폴더 이름만 다름). `scripts/build_manual_markdown_corpus.py`로 쪽에 대응시켜 1,507조각 중 1,137조각이 직접 근거 후보(쪽 779/813)입니다. 2026.10의 1,175/1,531과 비슷한 수준입니다.
- `scripts/build_manual_search_index.py`: 색인을 다시 만들었습니다. 2026.11 체류 PDF와 Markdown이 `approved`, 2026.10 체류 PDF와 Markdown은 `superseded`입니다. 사증은 그대로 `approved`입니다.
- `scripts/crosswalk_manual_pdf_pages.py`: 2026.10 → 2026.11 쪽 대응(`stay_page_crosswalk.json`). 812쪽 중 783쪽이 대응됩니다. 301쪽 이하는 그대로이며 그 뒤는 대체로 +1쪽입니다(E-7-4 사회통합 경과조치가 302쪽에 들어와 한 쪽 밀림).
- 매뉴얼 읽기 화면(`manual.html`): 체류 탭을 2026.11 Markdown으로 다시 만들었습니다. 바뀐 장은 체류 E-7, G-1, 지역특화(regional)뿐입니다. 장 시작 줄 번호는 추가된 글만큼 밀려서 새 줄 번호로 고쳤습니다. PDF 대조 프로브 일치율은 체류 98.58%, 사증 98.38%입니다.

## 4. Waymaker 근거와 구조화 요건 HIGH 18건

인용한 발췌문의 모든 줄이 2026.11 본문에 그대로 있는지, 어느 쪽에 있는지 확인했습니다(`scripts/verify_grounding_excerpts_edition.py`, 결과 `audits/manual-refresh-20261102/grounding_excerpt_check.json`). 21건 모두 그대로였고 서류 목록은 한 글자도 바뀌지 않았습니다.

- 쪽이 움직인 것은 한 건뿐입니다: E-10 외국인등록 341쪽 → **342쪽**. 나머지(D-2 44, D-4-1·D-4-7 90–92, E-7 연장 228, D-2 등록 44–45 등)는 301쪽 이하이거나 같은 쪽입니다.
- `stay_manual_grounding_2026_05.json`과 `structured_requirements_2026_06_01.json`은 파일·판본·쪽·해시 필드와 확인 기록 문구만 바꿨습니다. 서류 목록과 발췌문은 그대로입니다. 평가 시드(`eval_corpus_seed.json`)도 같습니다.

## 5. 상태별 안내와 화면 표기

- `scripts/status_guidance/author_rules.py`와 `scripts/build_status_coverage_manifest.py`를 2026.11 체류 판 기준으로 다시 돌렸습니다. 안내 규칙에 적힌 원문 인용이 새 본문에서 전부 찾아졌습니다(하나라도 없으면 빌드가 실패합니다). 규칙 파일의 바뀐 줄은 매뉴얼 id뿐이고 요건·서류 문구는 바뀌지 않았습니다.
- 동포 편람 쪽 고정값(H-2 근무처 변경 532→533, H-2 취업개시 신고 535→536, F-4 체류자격 부여 532→533)을 새 쪽에서 문구를 찾아 확인한 뒤 고쳤습니다.
- 화면: 첫 화면의 기준일·PDF 링크(체류 2026.11.02), 14개 언어 기준일 문구, 안내 면책 문구의 판 이름, `ai.html`의 출처 판본과 근거 id, 매뉴얼 읽기 화면의 표기와 PDF 링크를 바꿨습니다. 사증은 2026.10으로 남아 있습니다.
- `assets/js/status-guidance.js`에 2026.10 체류 id가 두 군데 고정돼 있어(증거 버튼의 쪽 열기) 같이 바꿨습니다.

## 6. 고정된 테스트와 바꾼 것

테스트를 약하게 하거나 지운 것은 없습니다. 새 판·새 쪽에 맞게 값만 바꿨습니다.

- 판본 id·표기: `2026.10` → `2026.11`(체류만), 승인·대체 관계(2026.10 쌍은 `superseded`로 단언), 정제된 근거 파일 경로.
- 쪽 번호: F-6 연장 말뭉치 확인 498→499·답변 인용 500→501, F-4 연장 540→541, E-10 등록 341→342, F-4 체류자격 부여 532→533(H-2 쪽 537→538).
- 말뭉치 고정 개수: 1,331 → 1,332쪽, 체류 812 → 813쪽, Markdown 체류 `stay_manual_2026_11_02_md` [1,507, 1,137].
- Waymaker 브라우저 고정 파일(`tests/fixtures/waymaker/`)은 `scripts/build_waymaker_answer_fixtures.py`로 다시 만들었습니다. 바뀐 것은 판 표기뿐입니다.

## 7. 실행한 검사 (2026-11-03)

| 명령 | 결과 |
| --- | --- |
| `python -m pytest backend/tests` (Python 3.11, 저장소 루트) | 2403 passed, 1 skipped |
| `npm run test:current-manuals`, `test:status-guidance`, `test:manual-reader`, `test:i18n`, `test:immigration-checklists`, `test:search-tools`, `test:search-waymaker` | 모두 통과 |
| `package.json`의 브라우저를 쓰지 않는 `test:*` 26개 | 모두 통과 |
| `python3 scripts/check_source_manuals.py` | OK (PDF 쪽 수 확인은 `pdfinfo`가 없어 건너뜀. 쪽 수는 PyMuPDF로 813쪽 확인, 말뭉치 확인 스크립트가 쪽 수와 해시를 고정함) |
| `python3 scripts/check_source_grounding_metadata.py` | OK |
| `python3 scripts/sync_visa_data.py --check` | OK |

**실행하지 못한 것:** Playwright 브라우저 테스트(`npm run test:e2e` 등). 실행을 시도하지 않았습니다(작업 중 이 맥의 Playwright 브라우저 캐시를 비웠습니다). 아래 e2e 파일은 같은 값 변경을 글자로만 반영했고 돌려 보지 않았습니다: `tests/e2e/result-hierarchy.spec.mjs`(532쪽 → 533쪽), `tests/e2e/waymaker-answer-card.spec.mjs`(2026.10 → 2026.11). 실제 화면에서 눈으로 확인하는 일도 하지 않았습니다.

## 8. 사람이 검토해야 할 항목 (needs manual review)

1. **E-7-4 / E-7-4R 바뀐 요건은 이 승격에 반영하지 않았습니다.** `audits/manual-refresh-20261102/README.md`의 "영향이 있을 수 있는 기존 데이터" 목록을 그대로 검토 항목으로 둡니다.
   - E-7-4, E-7-4R: 체류자격 변경·연장 요건, 제출서류, 점수제 기준(장기근속 3년 이상 5년 미만 / 5년 이상, 감점 벌금 100만원 → 300만원, 연장 제출서류 목록 신설, 한국어능력·사회통합 요건 특례 경과조치, 시행일 2026-11-02). `visa_data.json`, `doc_master.json`, `backend/data/visas.json`, 체류자격 안내 데이터는 수정하지 않았습니다.
   - G-1-3 / 체류자격외 활동허가(성폭력 피해자 등) 대상에 인지청구소송 진행 중인 사람 한 줄 추가.
   - E-7-4 시행 일자(`‘26. 11. 2.`), F-4-R 시행일(`2026. 11. 2.`) 표기.
   - 같은 문서 안의 붙임 번호 참조가 일부만 갱신된 곳(E-7-4 붙임 7·8·9·10·12 참조 줄)은 쪽 이미지로 확인해야 합니다.
   - 상태별 안내 규칙은 위 변경을 새로 쓰지 않았습니다. 안내 규칙이 이미 다루던 곳은 원문 인용이 그대로 찾아졌지만, 내용이 바뀐 곳(E-7-4 점수·서류)은 이전 요약이 남아 있을 수 있습니다.
2. **`visa_data.json`의 매뉴얼 인용**(2026.10 체류 쪽으로 재표기된 956건)은 그대로입니다. 대량 수정 금지 규칙에 따라 손대지 않았습니다. 301쪽 이하는 쪽이 같지만 그 뒤는 2026.11에서 대체로 한 쪽 밀립니다. 2026.10 PDF는 저장소에 남아 있어 인용 자체는 이전 판 기준으로 유효합니다. 2026.11 기준으로 다시 표기하려면 `scripts/visa/manual_ref_promotion_2026_10.py`와 같은 별도 검토 작업이 필요합니다.
3. 체류 PDF는 위 1항대로 재현 시험을 하지 않았고 공식 PDF 쪽 수(813쪽인지)를 확인하지 못했습니다.
4. 읽기 화면과 검색용 Markdown은 기계 변환(kordoc)입니다. 사람이 한 줄씩 대조하지 않았습니다.
5. `experiments/waymaker-ai/artemis_bootstrap/`의 Artemis 실험 자료와 `data/immigration-checklists/`(2026.9 매뉴얼 기준 정리본), `.github/workflows/hikorea-october-search-index.yml`은 이전 판 기준 기록이라 바꾸지 않았습니다.
6. 출력 파일 이름(`*-202609.json`)과 상태 코드 `SEPT_2026_ORIGINAL_UNREVIEWED`는 그대로 뒀습니다. 이름만 옛 시점을 가리킵니다.
