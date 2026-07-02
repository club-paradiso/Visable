# Post-submission stabilization pass — 2026-07-02

Manual-first, data-second, UI-third 순서로 진행한 제출 후 안정화 감사·수정 기록.
모든 수정은 현재 파일·라인 근거를 확인한 뒤에만 적용했고, 근거가 없는 주장은
`needs manual review`로 남겼다.

## 0. 기준 상태 (수정 전, main = d40f4d0)

- `npm run validate` 통과. 개별 스위트(employment/waymaker/hikorea/i18n/legal-search 등) 전부 통과.
- 실브라우저(Chromium) 콘솔 스모크: index/ai/form-helper/new-home/nationality-hub 5개 페이지
  **JS 예외 0건** (외부 CDN 차단으로 인한 리소스 오류는 샌드박스 환경 요인).
- Playwright e2e 91건 중 10건 실패 — 전부 `new-home.spec.mjs`의 `consoleErrors == []` 단정이
  샌드박스의 외부망 차단(Pretendard CDN css)으로 실패한 **환경 요인**. 제품 결함 아님.
- GitHub Pages는 최신 main(d40f4d0)을 2026-07-01 13:06 UTC에 정상 배포(성공 기록 확인).
  라이브 사이트가 "롤백"된 흔적은 git/Actions 어디에도 없음.
- 단, `scripts/visa/build_visa_data.py --check`는 **실패** (아래 1번), 그리고 실브라우저 검색
  실측에서 다수의 0건 검색이 확인됨 (아래 4번) — 사용자가 체감한 "오류난 시절" 증상과 일치.

## 1. 저작 레이어 ↔ 생성 파일 불일치 복구 (E-7-M)

- 증상: PR #506이 E-7-M(K-CORE) 세부자격을 생성 파일(`visa_data.json`)에만 추가하여
  `build_visa_data.py --check` 실패 (저작 레이어에서 재생성하면 E-7-M이 사라지는 상태).
- 수정: 동일한 E-7-M 레코드를 `backend/data/visa_authoring/statuses/E-7.json` `subcodes[12]`에
  이식. 재생성 결과 체크인본과 byte-identical → `--check` 통과.
- 근거: `backend/data/sources/manuals/260629_kcore_manual.hwp` (K-CORE 매뉴얼, 2026.6).

## 2. 동포 매뉴얼 단독본 소스 등록 (업로드 파일)

- 업로드 4개 중 3개(260617 사증 HWP·260623 체류 HWPX·260629 K-CORE HWP)는 저장소 원본과
  **해시 동일** — 이미 등록되어 있음.
- 신규: 「알기쉬운 외국국적동포 업무 매뉴얼」(2026.2, 붙임 배포 단독본, 2-up PDF 32쪽)
  → `backend/data/sources/manuals/260421_dongpo_manual.pdf`로 설치,
  `scripts/extract_dongpo_manual_2026_02.py`(sha256 고정 페이지맵)로 전문 추출(50,151자),
  섹션 32건 색인, `docs/source-manuals/source_manifest.json` `special_program_manuals`에 등록.
- 동일 계열 내용이 2026-06-23 체류 매뉴얼 pp.529-579에 내장되어 있고 기존 manualRefs는
  내장본을 가리키므로, 단독본은 **별첨 1–10 원문 대조용 corroborating source**로 등록
  (충돌 시 최신 체류 매뉴얼 내장본 우선을 manifest에 명시).
- `check_source_manuals.py`·`check_source_grounding_metadata.py` 통과.

## 3. 매뉴얼 근거 데이터 수정

### 3-1. F-1-72 상태 수정 (active → abolished)
- 증상: 이름부터 "(폐지)"인 F-1-72가 `status: "active"`로 남아 있어
  `check_exact_code_search_coverage.py`가 FAIL (main에서 잠복해 있던 실패).
- 근거: 2026-06-23 체류 매뉴얼 p.547 "기존에 영주(F-5-7) 신청자의 배우자와 미성년 자녀에게
  부여하던 방문동거(F-1-72)는 폐지" (원문 확인).
- 수정: 저작 `F-1.json`에서 status=abolished + statusNote(매뉴얼 인용) 부여 후 재생성.

### 3-2. F-4 "장관고시 21개국 별도 첨부서류" 문구 완화
- 증상: F-4 newReq의 "장관고시 21개국(…) 국민은 별도 첨부서류 기준 적용." 문장이
  2026.6 사증/체류 매뉴얼의 **F-4 절에서는 확인되지 않음** (동일 21개국 목록은 유학
  D-2/D-4-3, E-6-2 맥락에서만 존재; 동포 매뉴얼 C-3-8 절은 "국가…에 관계없이 신청 가능").
- 수정: 사실 단정을 "설치된 2026.6 공식 매뉴얼의 F-4 절에서는 확인되지 않는 항목 →
  재외공관·HiKorea·1345 확인 필요"로 완화 (이 레코드의 기존 2026.1.1 연령 항목과 동일 패턴).
  목록 자체는 보존(삭제 아님), 불확실성만 명시.

## 4. 검색 복구 (실브라우저 실측 기반, PARADISO_SEARCH_QUERY_FIX_20260702)

수정 전 실측(28개 질의): 압축 세부코드(G15/D21/E74/F442/D10T) 전부 0건,
"난민"·"난민신청"·"불법체류" 0건, 앱 자체 추천칩 다수("체류지 변경(주민센터)",
"숙련기능(E-7-4)", "체류기간 연장" 등) 0건.

근본 원인 및 수정 (`index.html`):
1. `renderResults`가 **모든** 질의를 공백 제거·압축해 한 토큰으로 만들던 문제
   → 코드형 질의일 때만 압축형을 사용.
2. `ALIAS_MAP`의 죽은 대상: 난민→RF-1, 불법체류→OVS-1 (존재하지 않는 레코드, AND 모드에서
   해당 검색을 0건으로 만듦) → 난민류는 실존 세부코드 G-1-5(난민신청자)로 재매핑,
   불법체류류 별칭은 제거(본문 키워드 검색으로 폴백), 인도적체류→G-1-6 추가.
3. 전체 질의가 ALIAS_MAP에 걸리면 정확코드 경로로 라우팅 (별칭 토큰이 AND 필수 토큰이
   되어 영원히 매칭 불가하던 구조 해소). FAQ-0(방문예약 예외 안내)가 이제 실제로 도달 가능.
4. 압축 세부코드: `getExactQueryMatchRank`에 대시 제거 compact 동등 비교 추가
   (G15↔G-1-5, D21↔D-2-1, F442↔F-4-42, D10T↔D-10-T, D42K↔D-4-2K …).
5. `getPrimaryCodeLikeQuery`가 질의 중간의 코드도 인식 ("숙련기능(E-7-4)" → E-7-4).
6. 0건이 확정인 추천어 3건("체류지 변경(주민센터)"·"여권 갱신(비예약)"·"만료 당일/임산부 등"·
   "오버스테이")을 해석 가능한 문구로 교체.
7. FAQ-0 주입 레코드 문구를 사용자 친화적으로 보강 (법적 단정 없음, 1345/관할 확인 안내).

수정 후 실측: 위 실패 질의 전부 해석(기대 카드 일치), 추천칩(landing/quick/predef) 전수 1건 이상.

회귀 방지:
- `scripts/check_exact_code_search_coverage.py`: compact 스모크 9건 추가 + index.html
  `ALIAS_MAP` 대상 실존 검증(#5) 추가.
- 신규 실브라우저 스펙 `tests/e2e/search-smoke.spec.mjs` (23개 질의 매트릭스 + 추천칩 전수).

## 5. Waymaker 국적 코치 딥링크 복구 (`ai.html`)

- 증상(확인): `new-home.html`·`nationality-interview-hub.html`의
  `ai.html?domain=nationality[&mode=naturalization_interview_prep]` 딥링크가 내비게이터
  마운트로 채팅이 숨어 **광고된 기능(국적 상담·귀화면접 코치)에 도달 불가**.
- 수정: 마운트 게이트에 `domain=nationality`(nav=1 아닌 경우)를 채팅 표면 신호로 추가.
- 실측: 기본 ai.html→내비게이터, domain=nationality→상담 코치 채팅,
  +mode=naturalization_interview_prep→면접 코치 채팅, mode=bogus→안전 폴백(내비게이터),
  nav=1→내비게이터 강제. 5경로 전부 의도대로, JS 오류 0.

## 6. HiKorea 도우미 라이트박스 Escape 버그 수정

- 증상(확인): 모듈의 라이트박스 Escape가 keyup(버블)인데 index.html 전역 핸들러는
  keydown이라 Escape가 **모달 전체를 닫아버림**.
- 수정: keydown 캡처 단계로 이동(`onZoomKeydown`) + preventDefault. 82/82 체크 통과.

## 7. 죽은 i18n 키 정리

- `step0a*` 27키 × 12로케일(총 324키)이 제거된 STEP 0-A UI의 잔재로 남아
  감사 시 "비밀번호 생성기 문자열 존재"로 오독될 수 있던 문제 → 전부 제거.
  (재직렬화 과정에서 한 줄에 여러 키가 있던 비표준 포맷도 표준 포맷으로 정규화됨 —
  파서 의미 동일.) i18n 검사 3종 통과.

## 8. 폼헬퍼 외국인등록번호 P0 (`form-helper.html`, `data/form_schemas.json`)

- 증상(확인): 등록번호가 단일 텍스트런으로 인쇄되어 공식 서식의 13자리 자리칸과 불일치;
  정규화 없음.
- 수정:
  - 입력: `000000-0000000`·`0000000000000` 모두 허용, 숫자만 13자리로 정규화, 6-7 하이픈
    자동 표시 (인메모리 상태만 사용, 저장 없음 — 브라우저 전용 프라이버시 불변).
  - 자리칸 좌표: F01/F03/F04/F05 정본 PDF의 **벡터 구분선에서 직접 실측**
    (F01·F03: 6칸 186.5–307.4 + 7칸 307.4–430.8; F04·F05: 13칸 191.9–436.6 균등).
  - 오버레이 엔진: `digits.cells` 선언 + 13자리 입력 시 자리별 중앙 정렬 인쇄,
    부분 입력은 기존 단일런 폴백.
  - 검증: 실제 엔진으로 F01·F04 PDF 생성 후 pypdf로 각 숫자의 x,y 좌표 추출 —
    13자리 전부 셀 중심과 일치, 5자리 입력은 폴백 확인.
- '현재 체류기간 만료일'을 필수 오류 → 안내용(서식에 인쇄되지 않음 명시, 미입력 허용)으로
  강등. 근거 미확인 시기 문구(4개월)는 쓰지 않고 HiKorea·1345 확인 안내로 처리.

## 9. G-1 재확인 (수정 불요 판정)

- G-1 procedures는 extension/registration/statusChange만 보유 — 사증발급 절차 탭 없음.
- 표준 카드의 사증발급 standalone 섹션은 "세부 사유별 차이가 커서 확정 체크리스트가
  아님·공관 확인 필요·근거 pp.336-342" 경고를 갖춘 제한적 POC 렌더링으로 확인.
- 16개 세부코드가 각자 addReqDocs·manualRefs·group을 유지(일반화 병합 없음),
  전부 needsManualReview 캐빗 유지. → 프롬프트의 G-1 P0 요건 충족 상태로 판정.
- 잔여 리스크: 사증발급 근거가 2026.5 매뉴얼(336-342p) 기준 — 2026.6 재확증은 후속 과제.

## 10. 전 자격 유니버스 감사 산출물

- `scripts/build_status_universe_audit_2026_07.py` (신규, 읽기 전용) →
  `audits/status-universe-2026-07/status_universe_audit.{json,md}`.
- 부모 42 / 세부코드 224 / 총 266 레코드 (하드코딩 없이 계산).
- 상태 분포: active 246, legacy 14+1(labelled), suspended 4, abolished 2, reference_only 1.
- 근거 없음(high-risk) 0건; needs-manual-review 62건(정직한 캐빗 유지 대상).
- 세 저장소(저작/생성/백엔드 미러) 완전 일치.

## 검증 불가 항목 (정직 고지)

- 라이브 백엔드(web-production-14f9a.up.railway.app) 상태: 샌드박스 프록시가 차단(403)하여
  이 환경에서 검증 불가. 라이브 "오류" 체감이 백엔드 다운/슬립에서 왔을 가능성은
  별도 확인 필요 (ai.html은 백엔드 부재 시 로컬 데이터로 폴백함 — 로컬 실측으로는 무예외).
- e2e new-home 10건: 외부 CDN 차단 환경에서만 실패. 네트워크 가능한 환경에서 재확인 권장.
