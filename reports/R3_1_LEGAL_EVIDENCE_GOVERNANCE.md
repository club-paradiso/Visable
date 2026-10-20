# VISABLE R3.1: Legal Evidence Governance & Grounding Model
## Administrative Evidence Integrity Beyond Bare URLs

- **Milestone**: VISABLE R3.1 (Production Publishing Recovery, Data Integrity & Operational Readiness)
- **Branch**: `feat/visable-r3-1-publishing-recovery`
- **Date**: 2026-10-20
- **Lead**: Immigration Information Quality & Regulatory Engineering Lead
- **Status**: Approved & Integrated

---

## 1. Problem Statement: The Inadequacy of Bare URLs

In immigration document guidance, directing an applicant to submit the wrong document—or failing to advise them of a mandatory document—can lead to application rejection, loss of legal residency status, departure orders, or administrative litigation.

Previous iterations enforced an **Evidence Gate** requiring an `https://` prefix for official links. While this prevented completely ungrounded modifications, relying solely on raw URLs introduces serious legal and operational risks:

1. **Link Rot & Domain Reorganization**: Government portal URLs (e.g. `hikorea.go.kr` notice pages) frequently shift during annual site revamps or CMS migrations, turning active links into 404 pages.
2. **Ambiguity of Administrative Authority**: A URL does not specify *who* issued the rule, *which edition* of the manual applies, or *which exact paragraph* governs the case.
3. **Temporal Validity Conflicts**: Immigration policies change frequently (e.g. student financial guarantee amounts update semi-annually). Without explicit effective dates, an outdated document requirement can linger indefinitely.

---

## 2. The R3.1 Legal Evidence Metadata Schema

To make immigration requirements legally auditable, defensible, and traceably grounded in Korean administrative law, R3.1 expands the evidence model into a structured metadata governance framework:

| Metadata Field | Type | Description | Example Value |
|---|---|---|---|
| `evidence_url` | String (URL) | Official HTTPS web address to the decree, notice, or manual | `https://www.hikorea.go.kr/board/BoardNtcDetailR.pt?bbsSeq=1&ntcBbsSeq=1234` |
| `evidence_title` | String | Official title of the regulation, decree, or manual | `외국인 체류안내 매뉴얼 (체류자격별 구비서류)` |
| `evidence_issuer` | String | Official issuing authority | `법무부 출입국·외국인정책본부 체류관리과` |
| `evidence_date` | ISO Date | Promulgation or publication date | `2026-10-15` |
| `source_edition` | String | Formal edition or revision version of the guidance manual | `2026년 하반기 개정판` |
| `source_section` | String | Specific chapter, article, or section designation | `제3장 유학(D-2) 체류자격 관리 / 제2절 체류기간 연장허가` |
| `source_locator` | String | Precise page number, decree number, or paragraph pointer | `p.142~144 (고시 제2026-88호)` |
| `effective_start` | ISO Date | Date on which the rule takes legal effect | `2026-10-20` |
| `effective_end` | ISO Date (Opt) | Sunset or expiration date (if applicable) | `2027-02-28` |

---

## 3. Hierarchy of Korean Immigration Norms

The Content Operations Studio enforces strict separation between statutory requirements, ministerial guidance, and local office practices:

```
┌─────────────────────────────────────────────────────────────┐
│ 1. 출입국관리법 (Statute)                                     │
│    - 국회 제정 법률 (예: 제17조, 제24조, 제25조)               │
├─────────────────────────────────────────────────────────────┤
│ 2. 출입국관리법 시행령 (Presidential Decree)                   │
│    - 대통령령 (별표 1 체류자격별 활동 범위)                      │
├─────────────────────────────────────────────────────────────┤
│ 3. 출입국관리법 시행규칙 (Ministry Ordinance)                  │
│    - 법무부령 (별표 5 및 별지 서식 규정)                         │
├─────────────────────────────────────────────────────────────┤
│ 4. 법무부 고시 및 훈령 (Ministerial Public Notice / Orders)    │
│    - 특정 체류자격 고시 (예: E-7 특정활동 고시, D-2 사증발급 지침) │
├─────────────────────────────────────────────────────────────┤
│ 5. 출입국·외국인 체류관리 지침 / 매뉴얼 (Guidance Manual)      │
│    - 전국 26개 관서 공통 실무 기준 (2026년 최신판)              │
├─────────────────────────────────────────────────────────────┤
│ 6. 관서별 특이사항 및 자체 실무 (Local Office Overrides)         │
│    - 26개 관서별 특화 서류 (예: 제주청 유학생 재정 특례)        │
│    - 국가 표준 데이터와 완전 분리 (checklist_office_overrides) │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Operational Invariant: Zero Fabrication Policy

1. **Mandatory Corroboration**: No scenario may have its requirements loosened or restricted based solely on an operator's subjective recollection.
2. **Four-Eyes Verification**: A reviewer must verify that the cited `evidence_issuer`, `source_edition`, and `source_locator` physically match the text in the authoritative source manual.
3. **Office Override Isolation**: Local office variations (such as specific regional bank account statement durations or additional accommodation confirmation forms) must be recorded exclusively in the `checklist_office_overrides` table. They are barred from mutating the 647 national baseline items.
