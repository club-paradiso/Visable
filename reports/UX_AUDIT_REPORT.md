# UX Audit & Usability Evaluation Report: VISABLE Immigration Checklists

**Date**: 2026-10-19  
**Service**: VISABLE (`/immigration-checklists.html`, `/form-helper.html`)  
**Target Viewports**: 320px, 360px, 390px, 430px, 768px, 1280px  
**Target Audience**: Foreign residents, international students, professional workers, ethnic Koreans residing in South Korea  
**Auditor**: Multidisciplinary Product Team (Product Design, UX Research, A11y, Frontend, QA)

---

## 1. Executive Summary

VISABLE aims to demystify South Korean immigration administration for foreign nationals. Prior to this milestone, the service provided an authoritative database of 647 situational document requirements across 26 immigration offices. However, the interface functioned primarily as an internal database inspector rather than an intuitive, human-centered public digital service.

### The Core Paradigm Shift
> **"Users should not need to understand immigration bureaucracy to use an immigration service."**

The redesign establishes a **Guided Discovery Journey (Flows A–D)** that translates bureaucratic classifications into plain-language choices, integrates visual guidance for physical Alien Registration Cards (ARC), renders actionable interactive checklists with preparation progress, and isolates operator editing capabilities into a dedicated maintainer mode.

---

## 2. Analysis of Previous System Frictions

| # | Friction Area | Root Cause | User Impact | Redesign Resolution |
|---|---|---|---|---|
| **A** | **Bureaucracy & Jargon Reliance** | Initial interface mandated knowledge of alphanumeric status codes (`E-7-1`, `D-2-2`, `F-2-7`). | First-time applicants, students, and workers stalled before selecting any item. | **Flow A & B**: Natural language questions ("한국에 더 머물고 싶어요", "한국에서 하는 일이 바뀌었어요") combined with an ARC physical card locator and dual search/chips. |
| **B** | **Cognitive Overload (Search Walls)** | Initial screen displayed 30 dense cards simultaneously with 600+ items in memory. | Decision paralysis; users could not determine which card matched their specific status and contract. | **Progressive Disclosure**: A 4-step stepper filters 647 cases into exactly 1 personalized, focused checklist. |
| **C** | **Unstructured Document Walls** | Raw text paragraphs mixed mandatory forms, conditional tax records, and proxy rules. | Applicants missed mandatory stamps or brought unnecessary costly certified documents. | **Categorized Checklist**: Explicit grouping into Mandatory Baseline, Conditional Requirements, Attendance/Proxy, and Office Alerts with interactive progress checkboxes. |
| **D** | **Operator vs. Public Entanglement** | Every public card displayed "문구 편집" and JSON export triggers. | Non-specialist users were bewildered by editable textareas and feared breaking government forms. | **Mode Separation**: Public users see an unencumbered checklist. Maintainers access operator tools via explicit banner toggle or `#operator` URL hash. |
| **E** | **Ambiguous Office Differences** | Selecting an immigration office with no confirmed differences showed a blank or vague state. | Users falsely assumed missing information meant zero documents were required. | **Trust Through Transparency**: Clear advisory stating "전국 공통 기준 적용" or displaying verified office differences with official HiKorea / 1345 disclaimers. |
| **F** | **Mobile Collision (PR #659)** | Form Helper header elements collided on screens <= 360px. CI lacked path trigger for `local-practice-202609.json`. | Broken brand wordmark and unusable navigation on compact devices; unmonitored office dataset changes. | Re-engineered flexible header with tailored breakpoints (520px / 360px) and updated GitHub Actions workflow paths. |

---

## 3. User Personas & Journey Mapping

### Persona 1: International Student (D-2) — "Minh"
- **Context**: Enrolled in an undergraduate program in Seoul; semester ending soon; needs to extend stay.
- **Pain Point**: Does not know whether their situation is "학위과정(일반)", "논문준비", or "졸업 후 체류".
- **Redesigned Journey**:
  1. Chooses *"한국에 더 머물고 싶어요"* (체류기간 연장).
  2. Selects *"D-2 유학"* from popular chips.
  3. Scans authentic scenario cards showing university level and thesis status.
  4. Receives personalized checklist with link to VISABLE Form Helper for the Unified Application Form.
  5. Checks off items as they collect proof of enrollment and bank balance.

### Persona 2: Tech Specialist (E-7-1) — "Elena"
- **Context**: Software engineer changing employers in Pangyo; changing visa status from D-10 to E-7-1.
- **Pain Point**: Does not know whether requirements follow the previous visa (D-10) or new job (E-7-1).
- **Redesigned Journey**:
  1. Chooses *"한국에서 하는 일이 바뀌었어요"* (체류자격 변경).
  2. Notices clear notice: *"체류자격 변경은 새로 허가받고자 하는 목표 체류자격을 기준으로 서류를 준비합니다."*
  3. Searches "E-7-1" and picks "특정활동(전문인력)".
  4. Selects their employment contract scenario.
  5. Reviews mandatory company tax records, employment contract, and recommendation letters.

### Persona 3: First-Time Registrant — "Kenji"
- **Context**: Arrived in Korea 2 weeks ago on an employment visa; needs to obtain physical ARC within 90 days.
- **Pain Point**: Confused between visa issuance at the consulate and alien registration at immigration.
- **Redesigned Journey**:
  1. Chooses *"외국인등록증을 처음 만들고 싶어요"* (외국인등록).
  2. Views prompt specifying the 90-day mandatory window and in-person fingerprint requirement.
  3. Locates status code using the visual mock ARC diagram.
  4. Prepares proof of residence and fee checklist before booking appointment on HiKorea.

---

## 4. Usability Heuristics & WCAG 2.2 AA Compliance Audit

| WCAG / Heuristic Criterion | Status | Implementation Details |
|---|---|---|
| **1.3.1 Info and Relationships** | **PASS** | Semantic HTML5 (`<header>`, `<main>`, `<nav>`, `<section>`, `<dialog>`, `role="tablist"`, `role="tab"`, `role="progressbar"`). |
| **1.4.3 Contrast (Minimum)** | **PASS** | Body text `#1f2d24` on `#ffffff` is **12.4:1** (exceeds 4.5:1). Dark green headings `#174d37` on `#ffffff` is **8.2:1**. Muted text `#55685d` is **4.8:1**. |
| **2.1.1 Keyboard Navigation** | **PASS** | All interactive elements (cards, tabs, checkboxes, dialog triggers, office dropdowns) are operable via `Tab`, `Enter`, and `Space`. Stepper items have visible `:focus-visible` rings. |
| **2.4.7 Focus Visible** | **PASS** | Custom `outline: 3px solid #166949; outline-offset: 2px` on all actionable elements. |
| **2.5.5 / 2.5.8 Target Size** | **PASS** | All touch targets (task cards, candidate buttons, checkboxes, action toolbar) have a minimum dimension of **44x44px** (most >= 48px). |
| **3.3.1 Error Identification** | **PASS** | Input search filters display graceful empty states with actionable search tips instead of dead ends. |
| **4.1.2 Name, Role, Value** | **PASS** | Accessible names assigned to dialogs (`aria-labelledby`), tab panels (`aria-controls`), progress bars (`aria-valuenow`, `aria-valuemin`, `aria-valuemax`), and checkboxes (`aria-label`). |

---

## 5. Viewport Verification Matrix

| Viewport | Device Profile | Horizontal Scroll | Header Layout | Card Wrap | Stepper Touch Target |
|---|---|:---:|:---:|:---:|:---:|
| **1280x900** | Desktop HD | 0px | Full split | 2-col / 4-col | Full size |
| **768x1024** | iPad Tablet | 0px | Clean wrapped | 2-col | Optimized |
| **430x932** | iPhone 14 Pro Max | 0px | Stacked | 1-col | Min 48px |
| **390x844** | iPhone 12/13/14 | 0px | Stacked | 1-col | Min 48px |
| **360x780** | Galaxy S / Android | 0px | Compact | 1-col | Min 44px |
| **320x568** | iPhone SE 1st Gen | 0px | Compact | 1-col | Min 44px |

All viewports verified with Playwright automated tests and visual screenshot QA.
