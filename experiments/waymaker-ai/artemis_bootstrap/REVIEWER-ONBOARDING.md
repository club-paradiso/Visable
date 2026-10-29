# 아르테미스(Artemis) 법률 검토자 온보딩 및 독립 검토 지침
## Artemis Legal Reviewer Onboarding & Evidence Verification Handbook

- **문서 버전**: 1.0 (Mission 005-A)
- **적용 대상**: 출입국관리법 전문 행정사, 변호사 및 공인 법률 검토위원
- **주무 부서**: Artemis Legal Verification & AI Safety Team
- **시스템 상태**: 비인가 로컬 프로토타입 (Non-Authoritative Evaluation Prototype)

---

## 1. 개요 및 검토 목적

본 지침은 출입국관리법령 및 법무부 행정지침을 질의응답하는 AI 시스템(Artemis/Waymaker)의 벤치마크 후보 문항에 대해, 공인된 자격을 갖춘 법률 전문가가 독립적이고 엄격하게 증거 원천을 검증할 수 있도록 표준 절차와 윤리 기준을 제공합니다.

> [!IMPORTANT]
> **신뢰 경계 및 Fail-Closed 원칙**
> 1. 인공지능이 생성한 요약문이나 검색 스니펫은 법적 효력이 있는 1차 증거가 아닙니다.
> 2. SHA-256 무결성 해시는 텍스트의 불변성을 증명할 뿐, 법적 정확성이나 유효성을 증명하지 않습니다.
> 3. 본 시스템의 로컬 검토 워크벤치는 **초안(Draft) 작성 및 감사 이력 기록용 도구**이며, 독립적인 공인인증/PKI 서명 검증 절차 없이 공인 골드(`official_gold`)로 자동 승격되지 않습니다.

---

## 2. 검토자 독립성 및 이해충돌 방지 선언 (COI Declaration)

모든 법률 검토자는 검토를 시작하기 전 다음의 독립성 및 이해충돌 방지 기준을 준수해야 합니다.

1. **독립성 원칙**: 검토 대상 모델의 개발자, 프롬프트 엔지니어 또는 상업적 이해관계자로부터 독립적이어야 합니다.
2. **이해충돌 공개**: 특정 체류자격(예: E-7, F-2-R 등) 관련 지자체 추천 컨설팅이나 특정 단체와의 직·간접적 이해관계가 있는 경우 이를 사전 신고하고 해당 항목 검토를 회피해야 합니다.
3. **위조 및 자동 서명 절대 금지**: 자동화 스크립트, 대리 서명, 가공의 검토자 식별자를 사용한 승인 기록은 무효이며 감사 로그에서 차단됩니다.

### 2.1 검토자 선언문 규격 (Reviewer Declaration Schema)
```json
{
  "reviewer_id": "REV-LICENSED-2026-001",
  "full_name": "홍길동",
  "professional_title": "공인행정사 / 출입국민원대행기관",
  "organization": "○○행정사사무소",
  "license_number": "제2024-XXXXX호",
  "independence_confirmed": true,
  "conflict_of_interest_statement": "본인은 본 평가 데이터셋 제작 및 모델 개발과 상업적·인사적 이해관계가 없음을 엄숙히 선언합니다.",
  "declaration_date": "2026-10-29"
}
```

---

## 3. 권위 있는 1차 출처 검증 계층 (Verification Hierarchy)

검토자는 반드시 다음의 공인 1차 출처 원문을 기준으로 사실관계를 대조해야 합니다.

| 우선순위 계층 | 대상 공인 문서 | 공인 원천 경로 |
|:---:|:---|:---|
| **Tier 1 (법령)** | 대한민국 출입국관리법, 시행령, 시행규칙 | 국가법령정보센터 (`law.go.kr`) |
| **Tier 2 (고시·훈령)** | 법무부 공식 고시 (외국인 유학생 재정능력, F-2-R 기준고시 등) | 전자관보 (`gwanbo.go.kr`) 및 법제처 행정규칙 |
| **Tier 3 (지침·편람)** | 하이코리아 공식 공개 매뉴얼 (체류관리 업무편람, 사증발급 매뉴얼) | 하이코리아 (`hikorea.go.kr`) 알림마당 공개자료실 |

> [!CAUTION]
> **출처 불인정 대상**:
> - 포털 사이트 메인 홈페이지 (`https://www.hikorea.go.kr` 등 단순 루트 URL)
> - 민간 행정사·유학원 블로그, 카페 게시글, 커뮤니티 답변
> - LLM이 자체 생성한 인용구

---

## 4. 4단계 법률 증거 검증 체크리스트

각 검토 패킷(`review_packets/*.json`)에 대해 다음 4개 항목을 면밀히 검증합니다.

```
[ ] 1. 출처 진정성 (Source Authenticity)
       - 국가법령정보센터/전자관보/공식 매뉴얼의 조·항·호 또는 별표 번호가 정확한가?
       - 포털 첫 페이지가 아닌 세부 규정 원문 URL이 기재되었는가?

[ ] 2. 현행 유효성 (Effective Date & Version)
       - 2026년 10월 현재 기준 유효한 법률·고시인가?
       - 개정 전 과거 구 지침(예: E-7-4 과거 100점 만점 기준, 유학생 일괄 2,000만원 기준 등)이 아닌가?

[ ] 3. 단서 및 예외 완결성 (Exceptions Completeness)
       - "원칙적 금지/제한"에 수반되는 법정 예외(관서장 사전 허가, 부득이한 사유 등)가 누락되지 않았는가?
       - 지자체장의 재량이나 특례 고시 사항이 균형 있게 기술되었는가?

[ ] 4. 법적 수치 및 조동사 충실도 (Wording Fidelity)
       - 금액, 거주기간, 의무기간, 점수 구간 등 핵심 수치가 왜곡되지 않았는가?
       - '허가'와 '신고', '할 수 있다(재량)'와 '하여야 한다(기속)'가 뒤바뀌지 않았는가?
```

---

## 5. 로컬 검토 워크벤치 활용 가이드

검토자는 CLI 환경 또는 로컬 Web GUI를 통해 패킷을 열람하고 의견을 기술할 수 있습니다.

### 5.1 CLI 명령 요약
```bash
# 1. 검토 대기 패킷 목록 조회
python review_workbench.py list --unreviewed-only

# 2. 특정 패킷 상세 열람 (질문, 제안 답변, 법령 근거 및 원문 발췌문)
python review_workbench.py view ARTEMIS-004-HLD-004

# 3. 비인가 검토 의견 초안(Draft) 작성
python review_workbench.py draft ARTEMIS-004-HLD-004 \
  --reviewer "홍길동 행정사" \
  --notes "시행령 별표 1의2 파목 및 법무부고시 제2026-248호 5년 실거주 요건 일치함." \
  --check-authenticity \
  --check-effective-date

# 4. 검토 패키지 내보내기 (JSON 번들)
python review_workbench.py export --out-file my_review_bundle.json
```

### 5.2 반응형 Web GUI 실행
```bash
python review_workbench.py serve --port 8080
```
- 브라우저에서 `http://127.0.0.1:8080` 접속
- Side-by-Side 분할 화면으로 질문, 법령 원문, 제안 답변을 비교 검토
- 저장형 XSS 방어(HTML Escaping) 및 CSRF 방어 토큰이 적용된 보안 세션 제공

---

## 6. 결론 및 책임 한계

본 지침에 따른 인간 법률 검토는 인공지능 모델의 법률 추론 성능을 객관적으로 측정하고 진단하기 위한 **독립 평가 절차**입니다. 
본 시스템의 출력물은 법무부의 공식 유권해석을 대신할 수 없으며, 개별 민원 신청에 대한 최종 허가 여부는 관할 출입국·외국인관서장의 심사에 따릅니다.
