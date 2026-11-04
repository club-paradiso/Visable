# Visable Legal Corpus — 한·영 출입국 법령 코퍼스

한국 출입국·체류·사범처리 관련 주요 법령의 **공식 한국어 원문**과 **공식 영문 번역본의 메타데이터**를 버전별로 저장하는 데이터 인프라입니다. Visable의 법령 검색, 법적 근거 인용, 범칙금 계산 검증, 향후 AI 분석의 근거 자료로 쓰입니다.

기준일: **2026-11-04**. 모든 법령은 국가법령정보센터(law.go.kr)에서 직접 수집·검증했습니다.

## 무엇을 저장하는가

| 구분 | 저장 방식 | 이유 |
| --- | --- | --- |
| 한국어 법령 본문 | **전문 저장** (Markdown + 조문별 JSON) | 법령은 저작권법 제7조상 보호받지 못하는 저작물이고, 국가법령정보센터 법령정보는 공공데이터로 자유 이용이 보장됨 (출처 표시 필수) |
| 공식 영문 번역본 | **메타데이터만 저장** (대응 버전·조문 제목·조문별 해시·공식 링크) | 번역 저작권은 한국법제연구원(또는 소관부처)에 있고 무단 복제·배포가 금지됨. `en.md`를 만들지 않으며, 없는 번역을 있는 것처럼 표시하지 않음 |
| 별표 7 (범칙금 양정기준) | **공식 PDF 원본 + 추출 텍스트 + 구조화 JSON** | 법령정보와 동일하게 자유 이용 가능. 금액은 검증된 결정론적 계산 엔진만 다루며, 이 코퍼스는 비교·검증만 수행 |
| 법무부 고시 | 전문 저장 (행정규칙 본문) | 법령정보와 동일 |

자세한 원칙은 [SOURCE_POLICY.md](SOURCE_POLICY.md)를 보십시오.

## 구조

```
backend/data/legal-corpus/
├── README.md                  # 이 문서
├── SOURCE_POLICY.md           # 출처·재사용·저작권 원칙
├── SYNC_GUIDE.md              # 수집·동기화 운영 방법
├── ENGLISH_ALIGNMENT.md       # 한·영 대응 상태와 근거
├── COVERAGE_REPORT.md         # 확보율 (사람이 읽는 보고서)
├── INTEGRATION_PLAN.md        # 기존 사범처리 계산기와의 연동 방안
├── manifest.json              # 전체 법령·버전 색인 (기계 판독)
├── coverage-report.json       # 확보율 (기계 판독)
├── sources/                   # 제공처별 엔드포인트·이용조건 기록
├── schemas/                   # metadata / articles / manifest / annex7 JSON Schema
├── laws/
│   ├── immigration-act/versions/<시행일>/
│   │   ├── metadata.json      # 공포·시행·출처·해시·번역 상태 (스키마 검증 대상)
│   │   ├── ko.md              # 한국어 원문 (의역·축약 없음)
│   │   ├── articles.ko.json   # 조문별 구조화 데이터
│   │   ├── translation.json   # 영문 대응 상태와 조문 대응표 (메타데이터만)
│   │   ├── source.json        # 수집 경로·원본 HTML 해시
│   │   └── changes.json       # 직전 버전과의 조문 단위 diff (최초 수집본은 INITIAL_IMPORT)
│   ├── immigration-decree/versions/…
│   └── immigration-rule/versions/… (+ annexes.json: 별표·서식 목록)
├── notices/moj-notice-2020-212-workplace-report-eligibility/   # 법무부고시 제2020-212호
├── annexes/immigration-rule-annex-7/versions/2026-01-23/
│   ├── annex7.pdf             # 공식 PDF 원본 그대로
│   ├── annex7.txt             # PDF 텍스트층 추출본
│   ├── annex7.json            # 구조화 개별기준 (기간/인원/횟수/참조)
│   └── annex7-vs-legal-rules.json  # 기존 계산 규칙과의 비교 결과
├── indexes/articles-index.json  # 전 법령 조문 색인
├── rules/annex7-vs-legal-rules.diff.json  # 비교 보고서 (코퍼스 레벨 사본)
└── validation/                # 검증 실행 결과
```

수집·검증 코드는 `backend/services/legal_corpus/`에 있습니다 (`client`, `parser`, `markdown`, `alignment`, `annex7`, `diffing`, `validator`, `adapter`, `sync`).

## 현재 수록 현황 (2026-11-04 검증)

| 법령 | 저장 버전 (시행일) | 조문 수 | 영문 상태 |
| --- | --- | --- | --- |
| 출입국관리법 (법령ID 001707) | 2026-01-23 (법률 제20992호), 2026-10-02 (법률 제21857호, **현행**) | 각 188 | 2026-01-23본 ALIGNED (188/188), 현행본은 OLDER_TRANSLATION |
| 출입국관리법 시행령 (법령ID 005256) | 2025-06-01 (대통령령 제35540호), 2026-10-02 (대통령령 제36728호, **현행**) | 각 185 | 2025-06-01본 ALIGNED (185/185), 현행본은 OLDER_TRANSLATION |
| 출입국관리법 시행규칙 (법령ID 008494) | 2026-01-23 (법무부령 제1106호), 2026-10-23 (법무부령 제1172호, **현행**) | 191 / 192 | NOT_AVAILABLE (공식 영문본 없음 — 확인 근거는 ENGLISH_ALIGNMENT.md) |
| 법무부고시 제2020-212호 | 시행 2020-06-22 (현행 확인) | — | 고시는 영문 제공 대상 아님 |
| 시행규칙 별표 7 | 개정 2026-01-23 | 개별기준 60개 목 | — |

- 한국어 조문 총 **1,129개** 저장. 공식 영문과 조문 단위로 대응이 확인된 조문 **373개** (본문은 저장하지 않음).
- 별표 7과 기존 계산 규칙(`backend/data/enforcement/legal_rules.json`)의 기간 기준 5개 항목 비교: **5/5 일치**. 상세는 COVERAGE_REPORT.md.
- 버전 간 diff: 출입국관리법 2026-01-23 → 2026-10-02에서 변경된 조문은 제4조, 제4조의4, 제4조의6, 제29조의2, 제85조 5개뿐이며, 사범처리 핵심 조문(제18·20·21·25·46·67·68·94·95·100조)은 변경되지 않았습니다.

## 안전장치

- **검증 실패 시 표시 금지**: 메타데이터 스키마·해시·우선 조문 존재 여부를 검증(`validator`)하고, 실패한 버전은 `VERIFICATION_REQUIRED`로 남깁니다. 로컬 스냅샷을 실시간 검증 완료(`LIVE_VERIFIED`)로 표시하지 않습니다 — 상태 어휘는 [INTEGRATION_PLAN.md](INTEGRATION_PLAN.md) 참조.
- **금액 자동 변경 금지**: 별표 7과 계산 규칙이 달라도 자동 반영하지 않고 diff 보고서만 생성합니다.
- **비밀정보 금지**: API 인증값(OC)은 환경변수로만 주입되며 저장소·로그 어디에도 기록하지 않습니다. 검증기에 비밀 패턴 스캔이 포함되어 있습니다.
- **멱등 동기화**: 변경이 없으면 어떤 파일도 다시 쓰지 않습니다 (`sync --check`로 확인 가능).

## 사용법 요약

```bash
# 변경 감지만 (쓰기 없음)
python3 -m backend.services.legal_corpus.sync --check

# 동기화 실행
python3 -m backend.services.legal_corpus.sync

# 코퍼스 검증
python3 -m pytest backend/tests/test_legal_corpus_data.py backend/tests/test_legal_corpus_units.py
```

주간 자동 점검은 `.github/workflows/legal-corpus-sync.yml`이 담당하며, 변경이 있을 때만 **초안(draft) PR**을 엽니다. 자동 병합·자동 배포는 하지 않습니다.
