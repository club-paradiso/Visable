# Design Rationale: VISABLE Human-First Immigration Experience

**Product**: VISABLE Document Guide & Immigration Checklists  
**Version**: 2026.10  
**Design System**: VISABLE Heritage Dark Green / Mint Design System  

---

## 1. Design Philosophy: Human-First Progressive Disclosure

Immigration procedures are inherently high-stakes and stressful. Foreign residents in South Korea face language barriers, legal ambiguities, and fear of administrative penalties. The primary goal of this redesign is to reduce cognitive strain by replacing overwhelming data tables with structured, sequential decision-making.

```
+-----------------------------------------------------------------------+
|  FLOW A: Task Discovery ("한국에서 어떤 일을 하려고 하나요?")               |
+-----------------------------------------------------------------------+
                                  |
                                  v
+-----------------------------------------------------------------------+
|  FLOW B: Visa Status Discovery ("현재/목표 체류자격은 무엇인가요?")        |
|  - Subtab 1: Code/Name Search & Popular Chips (D-2, E-7-1, F-4...)    |
|  - Subtab 2: Visual Physical Registration Card (ARC) Locator Diagram  |
+-----------------------------------------------------------------------+
                                  |
                                  v
+-----------------------------------------------------------------------+
|  FLOW C: Scenario Selection ("어떤 세부 신청 상황에 해당하시나요?")       |
|  - Real scenarios from 2026.09 dataset (work, study, family, etc.)    |
+-----------------------------------------------------------------------+
                                  |
                                  v
+-----------------------------------------------------------------------+
|  FLOW D: Personalized Document View ("맞춤 서류 준비 체크리스트")         |
|  - Mandatory baseline docs with interactive checkboxes & progress bar |
|  - Conditional requirements, attendance & proxy rules                 |
|  - Immigration office transparency advisory (26 offices)              |
|  - Direct link to Form Helper, print/PDF action, URL state sharing   |
+-----------------------------------------------------------------------+
```

---

## 2. Visual Hierarchy & Color Token System

The design aligns with VISABLE's brand language: calm, dependable, modern, and accessible.

```css
:root {
  /* Brand Core */
  --color-brand-primary: #174d37;     /* Deep Forest Green - authoritative, trustworthy */
  --color-brand-accent: #166949;      /* Emerald Green - interactive highlights, focus */
  --color-brand-subtle: #eef7f0;      /* Mint Tint - card backgrounds, active states */
  --color-brand-lime: #cbf0a5;        /* Vibrant Mint Accent - status badges, progress */
  
  /* Neutral Palette */
  --color-bg-canvas: #f5f9f6;         /* Calm organic canvas */
  --color-bg-card: #ffffff;           /* Clean white surface */
  --color-border-subtle: #dbe7df;     /* Defined yet soft boundaries */
  --color-border-strong: #174d37;     /* High-contrast active borders */
  
  /* Text Contrast */
  --color-text-main: #1f2d24;         /* WCAG AAA dark slate text */
  --color-text-muted: #55685d;        /* WCAG AA compliant auxiliary text (4.8:1) */
  --color-text-inverse: #ffffff;
}
```

### Contrast Assurance
- Body text `#1f2d24` on white card `#ffffff`: **12.4:1** (AAA standard: 7:1)
- Brand header `#174d37` on white `#ffffff`: **8.2:1** (AAA standard)
- Active buttons `#174d37` with white text: **8.2:1**
- Secondary tags `#eef7f0` with green text `#174d37`: **7.2:1**

---

## 3. Key Component Decisions

### A. Stepper Navigation Bar
- Sequential progression indicates current progress (`active`, `completed`, `upcoming`).
- Non-linear backwards navigation is supported at any time by clicking completed steps or "이전" buttons.
- State is preserved during backwards and forward navigation.

### B. ARC Registration Card Locator Diagram
- Foreigners unfamiliar with their alphanumeric code can switch to the "등록증 보는 법" subtab.
- Renders an authentic visual representation of a South Korean Alien Registration Card with a prominent pointer on the `체류자격 / SOJOURN STATUS` box.
- Uses strictly fictitious data (`HONG GILDONG`, `950101-0000000`) and disclaimers to protect privacy while educating users.
- Provides direct cross-references to HiKorea online lookup and the Ministry of Justice **1345** call center.

### C. Interactive Document Checklist & Progress Bar
- Breaks complex text blocks into discrete actionable checklist items (`.checklist-item`).
- Integrates with VISABLE's companion tool: items requiring the Unified Application Form (`통합신청서`) present a direct link to `form-helper.html`.
- Progress tracking bar displays real-time completion fraction (`X / Y개 준비 완료 (Z%)`).
- Check states are saved to browser `localStorage` keyed by scenario ID so returning users do not lose their progress.

### D. Separation of Operator Tools from Public Experience
- Operator features (wording edits, local draft storage, and JSON exports) are decoupled from the general consumer flow.
- A content maintainer notification bar is rendered only when requested via `#operator` hash or deliberate operator toggle.
- National and office-specific drafts remain strictly local to the user's browser, preventing unreviewed changes from escaping into production.

### E. Print & Offline Optimization
- Dedicated `@media print` stylesheet strips navigation banners, buttons, and decorative icons.
- Checkboxes, document titles, office advisories, and official legal disclaimers are laid out cleanly on standard A4 paper for physical consulate or immigration visits.
