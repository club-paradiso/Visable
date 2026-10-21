# VISABLE 이민 서류 체크리스트: 편집 및 검증 가이드

자료 기준: 2026년 9월 매뉴얼을 기반으로 만든 사용자 제공 통합 정리본. 법무부가 각 행을 개별 인증한 원본은 아니며 관할관서의 최신 안내를 대체하지 않습니다.

## 파일 구성

- extension-202609.json: 체류기간 연장 224개 신청 상황.
- change-202609.json: 자격변경 251개 신청 상황. 코드는 변경 *후* 목표자격이며 현재 자격에서 변경 가능한지 먼저 확인해야 합니다.
- registration-202609.json: 최초등록 및 국내거소신고 172개 신청 상황.
- reference-notes-202609.json: 본인·대리 신청의 공통 원칙, 24개 대리 유형, 개별 예외, 원문 충돌 사항.
- snapshot-202609.md: 원본 통합표의 앞 859행. JSON source_line 번호와 일치하므로 이 파일은 수정하지 마세요.
- local-overrides.json: 관서별 *검증된 차이*만 표시하는 장부.

원문 Markdown의 후반 원문대조 부록 전체는 저장소에 이관하지 않았습니다. 공식 원문은 기존 backend/data/knowledge_deploy/manual-corpus 폴더의 2026년 9월 자료와 대조하세요. 검토 없이 전국 공통 서류로 확정하거나 빈 서류목록을 허가조건 없음으로 해석하면 안 됩니다.

## 전국 공통 문구를 수정하려면

1. immigration-checklists.html에서 체류자격·업무·신청상황을 찾아 워딩 수정 버튼을 누릅니다.
2. '전국 기준 문구 초안'으로 서류와 조건부·생략 규정, 대리 신청, 주의 문구를 구분해서 수정합니다. 반드시 출처·검토 메모를 기입하세요.
3. '공통 수정본 JSON'으로 해당 업무 전체 자료를 내보내고 동일한 이름의 원본 데이터 파일을 GitHub PR에서 교체합니다.
4. source_line, id, status_code 및 수집 상태를 임의로 바꾸지 않습니다. 원문 대조와 검토 후에만 머지하세요.

편집 화면은 누구나 접근할 수 있지만 수정 초안은 브라우저 localStorage에만 저장됩니다. GitHub 및 서버에는 자동 게시되지 않습니다. 기존 Visa Authoring Pipeline의 생성물인 visa_data.json과 backend/data/visas.json은 직접 수정하지 마세요. 이번 자료는 기존 자격별 authoring source를 교체하는 것이 아닌 추가적인 상황별 출처 레이어입니다.

## 관서별 서류 차이를 수정하려면

1. 같은 카드에서 '특정 관서의 서류 차이 초안'을 선택한 뒤 관할 출입국관서를 지정합니다.
2. 추가 요구서류, 생략서류, 방문·대리접수 차이를 구분해서 입력합니다.
3. 날짜가 표시된 관서 공식 안내문 또는 검증된 독립 제보의 근거·메모를 남깁니다.
4. '관서별 초안 JSON'을 내보내 운영자 검토 후 local-overrides.json의 overrides 배열에 편입합니다.

관서 ID는 data/local-practice-202609.json 의 offices[].id를 사용하세요. 상위 청의 안내가 자동으로 산하 출장소까지 적용된다고 추측하지 않습니다. 실제로 검증하지 않은 제주·서울 등 관서별 서류 요구는 미리 생성하지 않았습니다.

### 관서 차이 공개 기준

- DRAFT/SUBMITTED/UNDER_REVIEW: 공개 금지.
- OFFICIAL_LOCAL_GUIDANCE: evidence 배열 안에 공식 관서 자료 {type: office_notice, url: https 주소}가 있어야 공개.
- VERIFIED_LOCAL_PRACTICE: 독립적인 일치 제보 최소 2건 및 운영자 검토 후 evidence 배열에 {type: corroborated_reports, count: 2 이상}을 기록할 때에만 공개.
- CONFLICTING_REPORTS/STALE_REPORT: 공개 금지.
- expires_on 경과: 공개 금지.

전국 기준과 관서별 내용을 나란히 보여줄 뿐, 지역 자료로 전국 공통 기준을 덮어쓰지 않습니다. 기존 data/local-practice-202609.json 진실성 계층 및 승격정책을 함께 적용하세요. 무분별하게 승인 상태만 바꿔 신뢰도를 높여서는 안 됩니다.

### 편집 예시 (검토 전, 특정 관서의 실제 요구를 뜻하지 않음)

입력 객체 속성: id, office_id, item_id, procedure, review_state="DRAFT", changes={required_text, conditional_text, application_text, note_text}, evidence=[], editor_note, expires_on.

## 알려진 원문상 주의

E-7 연장 소득증빙 표현 차이, 제주 광역형 유학 재정기준 불일치, F-3-19·20 혼용, F-2-7S 경로 차이, F-1-12 취소선, 등록·지문·면담 예외를 임의로 단순화하지 않습니다. '목록 미제시'는 서류 없음이 아닙니다. 심사기간이나 허가 가능성을 이 목록에서 추론하지 않습니다.

## 테스트

node scripts/check_immigration_checklists.mjs

npm run test:immigration-checklists
