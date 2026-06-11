# Short-stay checker scenarios + existing-page regression — browser QA (2026-06-11T07:56:00.591Z)

## A. Short-stay checker scenarios
- ✅ PASS — 베트남/ordinary/tourism/jeju_only/30d → expected copy present
- ✅ PASS — 베트남/tourism/jeju_only: no weak wording
- ✅ PASS — 베트남/tourism/jeju_only: no entry-guarantee wording
- ✅ PASS — 베트남/ordinary/tourism/mainland/30d → expected copy present
- ✅ PASS — 베트남/tourism/mainland: no weak wording
- ✅ PASS — 베트남/tourism/mainland: no entry-guarantee wording
- ✅ PASS — 베트남/ordinary/tourism/jeju_then_mainland/30d → expected copy present
- ✅ PASS — 베트남/tourism/jeju_then_mainland: no weak wording
- ✅ PASS — 베트남/tourism/jeju_then_mainland: no entry-guarantee wording
- ✅ PASS — 일본/ordinary/tourism/mainland/30d → expected copy present
- ✅ PASS — 일본/tourism/mainland: no weak wording
- ✅ PASS — 일본/tourism/mainland: no entry-guarantee wording
- ✅ PASS — United States/ordinary/tourism/mainland/90d → expected copy present
- ✅ PASS — United States/tourism/mainland: no weak wording
- ✅ PASS — United States/tourism/mainland: no entry-guarantee wording
- ✅ PASS — 중국/ordinary/tourism/mainland/30d → expected copy present
- ✅ PASS — 중국/tourism/mainland: no weak wording
- ✅ PASS — 중국/tourism/mainland: no entry-guarantee wording
- ✅ PASS — 홍콩/ordinary/tourism/mainland/30d → expected copy present
- ✅ PASS — 홍콩/tourism/mainland: no weak wording
- ✅ PASS — 홍콩/tourism/mainland: no entry-guarantee wording
- ✅ PASS — 대만/ordinary/tourism/mainland/30d → expected copy present
- ✅ PASS — 대만/tourism/mainland: no weak wording
- ✅ PASS — 대만/tourism/mainland: no entry-guarantee wording
- ✅ PASS — 태국/ordinary/tourism/mainland/30d → expected copy present
- ✅ PASS — 태국/tourism/mainland: no weak wording
- ✅ PASS — 태국/tourism/mainland: no entry-guarantee wording
- ✅ PASS — 인도/ordinary/business/mainland/30d → expected copy present
- ✅ PASS — 인도/business/mainland: no weak wording
- ✅ PASS — 인도/business/mainland: no entry-guarantee wording
- ✅ PASS — 칠레/ordinary/business/mainland/90d → expected copy present
- ✅ PASS — 칠레/business/mainland: no weak wording
- ✅ PASS — 칠레/business/mainland: no entry-guarantee wording
- ✅ PASS — 싱가포르/ordinary/transit/transit_only/1d → expected copy present
- ✅ PASS — 싱가포르/transit/transit_only: no weak wording
- ✅ PASS — 싱가포르/transit/transit_only: no entry-guarantee wording
- ✅ PASS — 몽골/ordinary/medical/mainland/20d → expected copy present
- ✅ PASS — 몽골/medical/mainland: no weak wording
- ✅ PASS — 몽골/medical/mainland: no entry-guarantee wording
- ✅ PASS — 미국/ordinary/overseas_korean/mainland/60d → expected copy present
- ✅ PASS — 미국/overseas_korean/mainland: no weak wording
- ✅ PASS — 미국/overseas_korean/mainland: no entry-guarantee wording
- ✅ PASS — unknown country typo → not-found guidance
- ✅ PASS — no country entered → prompt
- ✅ PASS — autocomplete suggests for "베트": 베트남 · Vietnam
- ✅ PASS — fetch failure → fallback warning, no silent eligibility claim
- ✅ PASS — fetch failure → rest of the page (search results) unaffected

## D. Representative existing visa/status pages
- ✅ PASS — F-6: renders ≥1 result with manual layout
- ✅ PASS — F-6: no new console errors
- ✅ PASS — F-5: renders ≥1 result with manual layout
- ✅ PASS — F-5: no new console errors
- ✅ PASS — F-2: renders ≥1 result with manual layout
- ✅ PASS — F-2: no new console errors
- ✅ PASS — F-4: renders ≥1 result with manual layout
- ✅ PASS — F-4: no new console errors
- ✅ PASS — D-2: renders ≥1 result with manual layout
- ✅ PASS — D-2: no new console errors
- ✅ PASS — D-4: renders ≥1 result with manual layout
- ✅ PASS — D-4: no new console errors
- ✅ PASS — D-8: renders ≥1 result with manual layout
- ✅ PASS — D-8: no new console errors
- ✅ PASS — D-10: renders ≥1 result with manual layout
- ✅ PASS — D-10: no new console errors
- ✅ PASS — E-7: renders ≥1 result with manual layout
- ✅ PASS — E-7: no new console errors
- ✅ PASS — E-9: renders ≥1 result with manual layout
- ✅ PASS — E-9: no new console errors
- ✅ PASS — G-1: renders ≥1 result with manual layout
- ✅ PASS — G-1: no new console errors
- ✅ PASS — H-2: renders ≥1 result with manual layout
- ✅ PASS — H-2: no new console errors
- ✅ PASS — C-3: renders ≥1 result with manual layout
- ✅ PASS — C-3: no new console errors
- ✅ PASS — B-1: renders ≥1 result with manual layout
- ✅ PASS — B-1: no new console errors
- ✅ PASS — B-2: renders ≥1 result with manual layout
- ✅ PASS — B-2: no new console errors
- ✅ PASS — archive_diary theme: checker card still renders with theme tokens

## Console errors captured
- console.error: Failed to load resource: net::ERR_CERT_AUTHORITY_INVALID

(Note: `ERR_CERT_AUTHORITY_INVALID` is the PRE-EXISTING backend-first data fetch (`API_BASE/api/visas`, index.html:17607) being blocked by the sandbox TLS proxy; the page falls back to static `visa_data.json` as designed. Not introduced by this change.)
