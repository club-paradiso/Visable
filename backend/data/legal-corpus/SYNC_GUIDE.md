# SYNC GUIDE — 수집·동기화 방법

## 실행

```bash
# 저장소 루트에서
python3 -m backend.services.legal_corpus.sync            # 동기화
python3 -m backend.services.legal_corpus.sync --check    # 변경 감지만 (쓰기 없음)
python3 -m backend.services.legal_corpus.sync --law immigration-act   # 특정 법령만
```

의존성: Python 3.11+ 표준 라이브러리만 사용합니다. 단, 별표 7 PDF 텍스트 추출에는 `pdftotext`(poppler-utils)가 필요합니다 (없으면 동기화가 오류로 중단되고 기존 저장본은 건드리지 않습니다).

## 동작 방식

1. **현행 버전 발견**: 각 법령의 공식 페이지(`law.go.kr/법령/<법령명>`)가 가리키는 현행 법령일련번호(MST)와 시행일을 읽습니다. 레지스트리(`backend/services/legal_corpus/registry.py`)의 과거 MST 목록과 합쳐 수집 대상 버전을 정합니다.
2. **본문 수집**: 버전별 본문 HTML(`lsInfoR.do`)을 받아 조문 단위로 파싱하고, `metadata.json` / `ko.md` / `articles.ko.json` / `source.json` / `changes.json`(직전 버전과 diff)을 생성합니다.
3. **영문 점검**: 버전별 영문 페이지(`engLsInfoR.do`)를 조회합니다. 조문이 실제로 존재하는 경우에만 번역이 있는 것으로 판정합니다 (헤더만 있는 빈 껍데기는 번역 없음으로 처리). 본문은 저장하지 않고 대응표(`translation.json`)만 만듭니다.
4. **별표 7**: 현행 시행규칙의 별표 목록에서 별표 7의 공식 파일을 내려받아 형식을 매직 바이트로 판정하고, PDF를 보존·추출·구조화한 뒤 기존 계산 규칙과 비교한 보고서를 생성합니다. **금액은 절대 자동 반영하지 않습니다.**
5. **고시**: 법무부고시 제2020-212호 본문(`admRulInfoR.do`)을 수집합니다.
6. **색인 갱신**: `manifest.json`, `coverage-report.json`, `indexes/articles-index.json`을 다시 씁니다.

## 멱등성과 안전장치

- 내용이 같으면 파일을 다시 쓰지 않고 최초 수집 시각을 유지합니다. 변경 없는 재실행은 빈 diff를 만듭니다 (`--check`의 `changedFiles: []`로 확인됨).
- 수집·파싱이 실패하면 해당 법령의 동기화를 중단하고 오류를 분류해 보고합니다. 기존 버전 디렉터리는 삭제·수정하지 않습니다.
- 새 버전이 발견되면 새 디렉터리를 만들고 구버전은 그대로 보존합니다.

## API 인증 (선택)

기본 경로는 인증이 필요 없는 공식 웹 엔드포인트입니다. DRF Open API 교차 검증은 `LAW_API_OC` 환경변수가 있을 때만 의미가 있습니다.

- OC는 open.law.go.kr에서 본인이 지정하는 식별자이며, **호출 서버의 IP/도메인을 함께 등록**해야 합니다. 미등록 서버에서 호출하면 "사용자 정보 검증에 실패하였습니다" 오류가 반환됩니다 (2026-11-04 실측).
- GitHub Actions에서는 Secrets에 `LAW_API_OC`를 등록하되, GitHub 호스티드 러너의 IP를 등록할 수 없으므로 교차 검증은 실패할 수 있고, 그 경우에도 웹 경로 수집은 계속됩니다. OC 값을 로그·아티팩트·PR에 남기지 마십시오.

## 자동화 (GitHub Actions)

`.github/workflows/legal-corpus-sync.yml`:

- 매주 월요일 03:00 KST 정기 실행 + 수동 실행(`workflow_dispatch`) 지원.
- 변경이 있으면 동기화 결과를 커밋해 **초안 PR**을 엽니다. 자동 병합은 없습니다.
- 검증 테스트(`test_legal_corpus_*`)가 실패하면 PR을 열지 않습니다.

## 새 법령 추가 방법

1. `registry.py`에 법령ID·법령명·확인된 MST를 등록합니다 (법령ID/MST는 공식 페이지에서 확인 — 추측 금지).
2. 동기화를 실행하고, 생성된 메타데이터의 공포번호·시행일이 공식 표시와 일치하는지 눈으로 대조합니다.
3. 검증 테스트의 법령 목록은 manifest를 기준으로 동작하므로 별도 수정이 필요 없습니다.
