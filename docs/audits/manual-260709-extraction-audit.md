# 260709 사증·체류 안내매뉴얼 — 배포용 HWP 복호·추출 감사

## 요약
2026.7.(260709) 사증발급/외국인체류 안내매뉴얼 HWP 2종은 **배포용(distribution) 문서**로,
BodyText에는 안내문구만 있고 본문은 `ViewText/Section*`에 암호화되어 있었다(기존 hwp5txt 실패 원인).
공개된 배포용 복호 절차(XOR 언스크램블 → AES-128-ECB → raw zlib)로 **전 섹션(13/13, 21/21) 완전 추출**했다.

## 원본 식별 (SHA-256)
| 파일 | SHA-256 |
| --- | --- |
| 260709 사증민원(사증발급 안내매뉴얼 2026.7) | fdb8b5e824d64ed7515a3ac6a7aae4bf812c4cb5588cdcf8d73be8d3273529d7 |
| 260709 체류민원(외국인체류 안내매뉴얼 2026.7) | a9e925b3dd90c1d92f7906e6a9a373be68c30932d438607c4c1ff5ed23065d3b |

(HWP 원본은 Codex 로컬 `backend/data/sources/manuals/260709_*.hwp` 보관분과 동일 해시 계열 — 본 저장소에는 추출 텍스트만 추가)

## 추가된 소스
- `backend/data/sources/manuals/260709_visa_manual_extracted.txt` (484,798자)
- `backend/data/sources/manuals/260709_stay_manual_extracted.txt` (740,926자)

## 복호 방법 (재현용)
1. OLE(`olefile`)에서 `ViewText/Section*` 스트림 읽기
2. 첫 레코드(HWPTAG_DISTRIBUTE_DOC_DATA, 256B): seed=첫 4바이트(LE),
   MSVC LCG(`seed*214013+2531011`)로 idx≥4 바이트 XOR 언스크램블
3. `offset = 4 + (seed & 0xF)`에서 16바이트 = AES-128-ECB 키
4. 잔여 스트림 AES-ECB 복호 → raw zlib(-15) 해제 → HWP 레코드 파싱(PARA_TEXT=67, 확장컨트롤 8워드 스킵, 서러게이트 쌍 결합)

## E-7 집중 대조 (체류매뉴얼 11264–17534행)
- 세부코드 분류표: E-7-1 전문(67직종)·E-7-2 준전문(10)·E-7-3 일반기능·E-7-4 숙련기능(점수제3) — 본문에 E-7-S/S1/S2·E-7-T·E-7-91도 등장
- 공통 첨부서류(11492~): [피초청] 여권사본, 반명함판 칼라사진 1매, 고용계약서, 자격요건 입증(학위증·경력증명서·자격증) /
  [초청] 설립관련서류, 고용 필요성 입증(초청사유서·고용추천서), 신원보증서(제한직종 한정), 국세·지방세 납세증명
- **고용추천서 = "고용추천 필수 직종에 한해" 징구** → 세부코드/직종별 추가서류 UI 분리(P0-c·subcodeAdditionalDocs) 방향과 정합
- 백엔드 `statuses/E-7.json` 대조: 세부코드 집합은 상위집합(±FTA·4R·Y 포함), 핵심 서류 키워드(고용추천서/신원보증서/납세증명/고용계약서) 존재 — **명백한 결손 미발견**

## 미반영·후속 (수동 검수 필요)
- 260709 vs 260623 diff(scripts/diff_manual_versions.py) 전 코드 실행 → 변경 조항 목록화
- 직종별(세부코드별) 추가서류 표를 구조화해 statuses/*.json `subcodeAdditionalDocs` 보강
- `manualRefs`를 260709로 갱신하는 것은 위 diff 검수 후에만 (버전 과대표기 방지)
