#!/usr/bin/env node
/*
 * Static checks for exact-code search accessibility, URL ?q= support, and
 * QA data-testid hooks added in the fix/exact-code-search-accessibility-qa-hooks PR.
 *
 * Reads index.html as text — no browser runtime required.
 * Failures are real invariant breaks (non-zero exit).
 */
'use strict';

const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

const ROOT = path.resolve(__dirname, '..');
const HTML = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');

const failures = [];
const passed = [];
function check(name, cond, detail) {
    if (cond) passed.push(name);
    else failures.push(name + (detail ? ' — ' + detail : ''));
}

/* 1. Search input carries data-testid */
check('1. search input has data-testid="visa-search-input"',
    HTML.includes('data-testid="visa-search-input"'));

/* 2. Search submit button carries data-testid */
check('2. search submit has data-testid="visa-search-submit"',
    HTML.includes('data-testid="visa-search-submit"'));

/* 3. data-testid attributes are on the correct element types */
check('3. visa-search-input testid is on an <input> element',
    /\binput\b[^>]*data-testid="visa-search-input"/.test(HTML) ||
    /data-testid="visa-search-input"[^>]*>/.test(HTML));

check('4. visa-search-submit testid is on a <button> element',
    /\bbutton\b[^>]*data-testid="visa-search-submit"/.test(HTML) ||
    /data-testid="visa-search-submit"[^>]*>/.test(HTML));

/* 5. Procedure tabs rendered with data-testid and data-procedure-key */
check('5. procedure tabs carry data-testid="procedure-tab"',
    HTML.includes('data-testid="procedure-tab"'));

check('6. procedure tabs carry data-procedure-key attribute',
    HTML.includes('data-procedure-key='));

/* 7. data-procedure-key uses template interpolation (not a literal key) */
check('7. data-procedure-key is dynamically set from p.key',
    HTML.includes('data-procedure-key="${p.key}"'));

/* 8. Result cards rendered with data-testid="visa-result-card" */
check('8. result cards carry data-testid="visa-result-card"',
    HTML.includes("dataset.testid = 'visa-result-card'") ||
    HTML.includes('dataset.testid="visa-result-card"'));

/* 9. Result cards carry data-visa-code */
check('9. result cards carry data-visa-code attribute',
    HTML.includes('dataset.visaCode = v.code'));

/* 10. Result cards carry data-visa-subcode (conditionally set) */
check('10. result cards set data-visa-subcode from subcodes',
    HTML.includes('dataset.visaSubcode'));

/* 11. ?q= URL parameter is read in initUI */
check('11. initUI reads ?q= URL parameter via URLSearchParams',
    HTML.includes("URLSearchParams(window.location.search).get('q')") ||
    HTML.includes('URLSearchParams(window.location.search).get("q")'));

/* 12. ?q= support applies normalizeCodeLikeQuery for code-like inputs */
check('12. ?q= path uses isCodeLikeQuery / normalizeCodeLikeQuery normalization',
    HTML.includes('isCodeLikeQuery(qParam)') && HTML.includes('normalizeCodeLikeQuery(qParam)'));

/* 13. ?q= triggers renderResults with the normalized query */
check('13. ?q= path calls renderResults with the normalized value',
    HTML.includes('renderResults(normalized)'));

/* 14. ?q= path transitions to searched state without landing animation */
check('14. ?q= path removes landing class and sets searched',
    HTML.includes("classList.remove('landing'") && HTML.includes("classList.add('searched')"));

/* 15. normalizeCodeLikeQuery handles lowercase hyphenated codes (d-2 → D-2) */
{
    // Inline-evaluate the function from the HTML source
    let ok = false;
    try {
        const match = HTML.match(/function normalizeCodeLikeQuery\(value\)\s*\{[\s\S]*?\n\}/);
        if (match) {
            // eslint-disable-next-line no-new-func
            const fn = new Function('value', match[0].replace(/^function normalizeCodeLikeQuery\(value\)\s*/, ''));
            ok = fn('d-2') === 'D-2' && fn('g-1-5') === 'G-1-5' && fn('f4') === 'F-4';
        }
    } catch (e) { ok = false; }
    check('15. normalizeCodeLikeQuery correctly normalizes d-2→D-2, g-1-5→G-1-5, f4→F-4', ok);
}

/* 16. Existing D-2 golden path checks still pass */
{
    let ok = false;
    try { execFileSync('node', [path.join(ROOT, 'scripts', 'check_d2_student_journey.js')], { stdio: 'ignore' }); ok = true; }
    catch (e) { ok = false; }
    check('16. D-2 golden path checks still pass', ok);
}

/* 17. Existing all-status audit still runs */
{
    let ok = false;
    try {
        const audit = require('./audit_procedure_journeys.js');
        const r = audit.runAudit();
        ok = r.records.some((x) => x.statusCode === 'D-2') && r.records.some((x) => x.statusCode === 'E-7');
    } catch (e) { ok = false; }
    check('17. all-status audit still runs', ok);
}

/* 18. Exact-code result filtering uses current numeric ranks */
check('18. renderResults filters exact top-level matches with numeric rank >= 10000',
    HTML.includes('v._exactRank >= 10000'));

check('19. renderResults filters exact subcode matches with numeric rank >= 5000',
    HTML.includes('v._exactRank >= 5000') && HTML.includes('v._exactRank < 10000'));

check('20. renderResults no longer checks stale exact ranks 6 and 5',
    !HTML.includes('v._exactRank === 6') && !HTML.includes('v._exactRank === 5'));

/* ---- report ---- */
console.log('Exact-code search accessibility and QA hook checks:');
for (const n of passed) console.log('  PASS ' + n);
for (const n of failures) console.log('  FAIL ' + n);
console.log('');
console.log(`${passed.length} passed, ${failures.length} failed`);
process.exit(failures.length ? 1 : 0);
