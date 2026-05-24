# STITCH PROTOTYPE FIX REPORT
*Generated: 2026-05-24 · Branch: claude/affectionate-einstein-lJc0f*

---

## Context

No pre-existing Stitch output was found in the repository. This report documents the corrected prototype built from scratch in `prototype/` to represent what a Stitch-generated Paradiso redesign **should** look like — and what problems the brief warned against.

The prototype lives entirely in `prototype/index.html` and `prototype/ai.html`. The live app files (`index.html`, `ai.html`) were **not touched**.

---

## 1. What Was Fixed

### Product Identity
| Problem | Fix |
|---|---|
| Generic "Jeju Residency Guide" branding | Product name is `Paradiso` everywhere — header title, page `<title>`, footer, AI page |
| "Residency Guidance Desk" as AI name | AI page title is `Paradiso AI — 비자·체류 정보 AI 도우미` |
| "Official Residency Guidance" copy | Replaced with `체류 정보 안내` (informational framing, not official claim) |
| Favicon used as visible UI logo | Hero uses only `paradiso-wordmark-brush-white.png`; favicon is browser-tab only |

### Visual Anchors Preserved
- Cherry blossom bus photo (`ws-chae--jVX4mW1Uac-unsplash.jpg`) is the hero background image.
- Dark overlay uses `#085E48` emerald gradient — maintains Paradiso brand colour.
- White wordmark centered in hero, not the green favicon.

### Design Tokens
All tokens from `DESIGN.md` are correctly applied:
- Primary: `#0EA37B` / Primary Deep: `#085E48` (buttons use deep+neutral per WCAG AAA rule)
- Neutral paper: `#F4EEE0`
- Dark mode surfaces: `#0B2A24` / `#113B32`
- Radius system: xs=4px, sm=8px, md=12px, lg=16px, xl=20px, pill=9999px (no flat 32px everywhere)
- Pretendard Variable font; weight hierarchy 800→700→600→400 (not 900 everywhere)

### Actual Paradiso Functions Preserved
| Feature | Prototype Location |
|---|---|
| Main search input | `index.html` → Hero section, glass pill bar |
| Direct visa/status code search | Search bar placeholder + code hint (`D-10`, `E-7-1`, `F-4`) |
| Keyword chips | Hero → `kchip` buttons (7 chips: D-2, E-7, F-2, F-6, C-3, 취업비교, 연장) |
| Language selector | Top controls: KO/한국어 pill with dropdown arrow |
| City/time control | Top controls: 제주 · live clock |
| Light/dark mode toggle | Top controls: moon icon, `[data-theme="dark"]` toggle |
| Visa/stay pathway selector | Section B: 6-card pathway grid (유학·연구, 취업·특정활동, 가족·결혼, 영주·귀화, 단기체류, 자격변경) |
| Search results | Section C: result count, filter chips, collapsed/expanded cards |
| Expanded result cards | Section C: D-10 card with code badge, name KO/EN, domain badge |
| Required document tabs/checklist | Section C: proc-tabs (신청서류 / 연장서류 / 변경절차) + checkbox list |
| HiKorea reservation/help CTA | Section C: banner strip; card action button |
| Paradiso AI CTA | Section E: dark strip with "AI 도우미 시작" button → `ai.html` |
| Jurisdiction/office lookup | Section D: 시/도 + 구/군 selects → office name, address, hours |
| Job-code lookup | Section D: E-7 직종코드 text search |
| Source/verification notices | Every card: `source-block` with `출처 참고 / 공식 확인 필요` |
| Legal/admin disclaimers | Footer + every answer card + input area |
| Mobile responsiveness | Responsive breakpoints at 768px and 480px |
| AI chat: answer cards | `ai.html` → `answer-card` with kicker, grounding badge, context pills |
| AI chat: source panel | `ai.html` → `source-panel` with source title + file reference |
| AI chat: grounding status | `ai.html` → `grounding-badge` (grounded / ungrounded states) |
| AI chat: disclaimer | `ai.html` → `msg-disc` + `answer-note` in every answer |
| AI chat: copy actions | `ai.html` → copy button with clipboard API |
| AI chat: composer input | `ai.html` → auto-resize textarea |
| AI chat: send button | `ai.html` → styled send button, Enter key support |

### Copy Corrections Applied
| Old (wrong) | New (correct) |
|---|---|
| `Jeju Residency Guide` | `Paradiso` |
| `Residency Guidance Desk` | `Paradiso AI — 비자·체류 정보 AI 도우미` |
| `Official Residency Guidance` | `체류 정보 안내` |
| `Verified against HiKorea Portal` | `공식 확인 권장` |
| `Official Source Verification` | `출처 참고 / 공식 확인 필요` |

---

## 2. What Was Removed (Fake Features / Wrong Copy)

| Removed | Reason |
|---|---|
| `Check Status` navigation item | No real Paradiso function with this name |
| `Download Document Kit` CTA | Not a real Paradiso function |
| `Visas / Work / Life / Settlement` nav tabs | Fake categories not in the real app |
| Government-official-sounding copy | Paradiso is **not** a government service |
| Travel-brochure tone | Hero is now product-focused (search-first), not lifestyle marketing |

---

## 3. What Should NOT Be Directly Applied to the Real App

| Item | Why Not |
|---|---|
| Prototype nav (floating bottom bar) | Prototype-only wayfinding; not part of real UX |
| `state-label` orange chips | Prototype annotation markers only |
| Static dummy data (office address, doc list) | Must be wired to real `visas.json` / backend data |
| Hard-coded clock | Real app uses JS bound to user's selected city timezone |
| `scrollTo()` prototype nav functions | Different from real app's searched-state transition |
| Anchor links (`href="#"`) | Real app uses router / JS navigation |
| `prototype/` relative asset paths (`../assets/`) | Real app references `assets/` directly |
| Section B pathway grid layout | Real app uses a different entry rail; needs integration review |
| Prototype answer card data | Real AI page pulls from backend; static copy is illustrative only |

---

## 4. Patterns Safe to Migrate into `index.html` and `ai.html`

These patterns are clean and can be lifted into the live app:

| Pattern | File | Notes |
|---|---|---|
| Hero glass search bar styling (`.sbar` with `backdrop-filter`) | `index.html` | Already partially in live app; prototype refines button size and colour |
| Keyword chip styles (`.kchip`) | `index.html` | Matches `.lh` / `.qb` in live app; prototype has cleaner dark-overlay variant |
| HiKorea banner layout (flex, sub-text, CTA button) | `index.html` | Live app has `.hikorea-banner` but prototype adds the disclaimer sub-text |
| `visa-code-badge` + `domain-badge` combo in card header | `index.html` | Matches DESIGN.md spec; prototype shows correct visual scan order |
| Proc-tabs + doc checklist card structure | `index.html` | Already in live app; prototype shows the correct radius (16px not 32px) |
| `source-block` copy (`출처 참고 / 공식 확인 필요`) | `index.html` | Direct copy replacement for official-sounding source label |
| AI page title/subtitle (`Paradiso AI` + sub) | `ai.html` | Already correct in live app; prototype confirms correct pattern |
| `answer-note` disclaimer inside answer card | `ai.html` | Adds structured in-card disclaimer below source panel |
| `input-meta` row with disclaimer below composer | `ai.html` | Adds persistent legal reminder in input zone |
| Dark-mode ambient background (`body::before/::after`) | `ai.html` | Already in live app; confirmed as correct pattern |
| Jurisdiction lookup layout (select-row → result card) | `index.html` | New pattern not yet in live app; safe to adapt |
| Job-code text search input pattern | `index.html` | Simpler than existing modal; review against live modal |
| Footer copy (3-line legal + 1345 reference) | Both | Matches legal requirements; prototype has clean layout |

---

*End of report. Prototype files: `prototype/index.html`, `prototype/ai.html`.*
*Live app files untouched: `index.html`, `ai.html`.*
