# F-4 route guide — browser QA (2026-06-11T07:56:00.591Z)

- ✅ PASS — F-4 search: 6 life-situation cards shown
- ✅ PASS — F-4 guide opens with 어떤 상황에 가까우신가요?
- ✅ PASS — F-4: no document wall by default (result+timeline collapsed)
- ✅ PASS — F-4: freshness badge + current-national warning visible
- ✅ PASS — situation former_korean_national → expected content
- ✅ PASS — situation descendant_parent_grandparent → expected content
- ✅ PASS — situation possible_dual_national → expected content
- ✅ PASS — dual-national result never promises F-4 availability
- ✅ PASS — situation domestic_residence_report_after_entry → expected content
- ✅ PASS — situation us_consular_application → expected content
- ✅ PASS — situation fbi_apostille_preparation → expected content
- ✅ PASS — search "F-4 FBI" → guide visible + relevant card auto-selected
- ✅ PASS — search "F-4 거소증" → guide visible + relevant card auto-selected
- ✅ PASS — search "F-4 국적상실" → guide visible + relevant card auto-selected
- ✅ PASS — search "F-4 병역" → guide visible + relevant card auto-selected
- ✅ PASS — search "F-4 미국" → guide visible + relevant card auto-selected
- ✅ PASS — search "F-4 아포스티유" → guide visible + relevant card auto-selected
- ✅ PASS — F-4 거소증: explicitly domestic-only
- ✅ PASS — F-4 mobile 375px: no horizontal overflow (delta 0px)
- ✅ PASS — F-4 mobile: situation cards tappable (78px)

## Console errors captured
- console.error: Failed to load resource: net::ERR_CERT_AUTHORITY_INVALID

(Note: `ERR_CERT_AUTHORITY_INVALID` is the PRE-EXISTING backend-first data fetch (`API_BASE/api/visas`, index.html:17607) being blocked by the sandbox TLS proxy; the page falls back to static `visa_data.json` as designed. Not introduced by this change.)
