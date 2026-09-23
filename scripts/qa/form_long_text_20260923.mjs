// Long-text visual QA (release sign-off 2026-09-23): fills every template's name, address,
// institution, employer and e-mail cells with long, hyphenated, apostrophe and mixed Korean/Latin
// values, records the fit decision (size, SHRUNK, OVERFLOW, FONT) per cell and writes the PDFs
// for rasterized review.   node scripts/qa/form_long_text_20260923.mjs [outDir]
import fs from 'node:fs'; import path from 'node:path'; import { createRequire } from 'node:module';
const ROOT = process.cwd(); const require = createRequire(import.meta.url); const OUT = process.argv[2] || 'artifacts/form-long-text-20260923'; fs.mkdirSync(OUT, { recursive: true });
const E = require(ROOT + '/assets/js/form-engine.js');
const PDFLib = require(ROOT + '/assets/forms/vendor/pdf-lib.min.js'); const fontkit = require(ROOT + '/assets/forms/vendor/fontkit.umd.min.js');
const S = JSON.parse(fs.readFileSync(ROOT + '/data/form_schemas.json', 'utf8')).forms;
const charset = JSON.parse(fs.readFileSync(ROOT + '/assets/forms/fonts/NanumGothic-Regular.charset.json', 'utf8'));
const glyphs = E.makeGlyphChecker(charset);
const fontBytes = fs.readFileSync(ROOT + '/assets/forms/fonts/NanumGothic-Regular.ttf');
const font = fontkit.create(fontBytes); const measure = (t, s) => font.layout(t).advanceWidth * s / font.unitsPerEm;
const SUR = 'WOLFESCHLEGELSTEINHAUSEN', GIV = 'MARIA-ALEXANDRA JOSEPHINE', APOS = "O'CONNOR-SMITH SEAN PATRICK";
const AKO = '경기도 성남시 분당구 판교역로 235, 에이치스퀘어 엔동 7층 701호 (삼평동)';
const AEN = 'Apt 12B, 1234 North Lakeshore Boulevard, Springfield, IL 62704, USA';
const INST = '서울글로벌국제고등학교 부설 영재교육원', EMP = '주식회사 에이비씨 글로벌 테크놀로지 코리아', MIX = 'Samsung Electronics 삼성전자(주) Suwon';
const MAIL = 'maria.alexandra.wolfeschlegelstein@example-university.edu';
const REASON = '해외 대학원 입학 전형 면접 일정이 연기되어 출국일이 늦어졌기 때문에 재입국허가 기간 연장이 필요합니다';
const F0 = { surname: SUR, given: GIV, addr_korea: AKO, home_addr: AEN, school_name: INST, workplace_cur: EMP, workplace_new: MIX, email: MAIL };
const F4 = { surname: SUR, given: GIV, korean_name: '김마리아알렉산드라', residence_korea: AKO, overseas_addr: AEN, workplace: EMP, school_name: INST, email: MAIL };
const cases = {
  F01: F0, F02: F0, F03: F0, F04: F4, F05: F4,
  F06: { rcpt_name: APOS, rcpt_address: AKO, prov_name: '김민수', prov_company: EMP, prov_sign_name: '김민수' },
  F07: { app_surname: SUR, app_given: GIV, app_addr: AKO, g_name: APOS, g_addr: AEN, g_workplace: EMP, g_work_addr: AKO, app_purpose: MIX },
  F08: { name: APOS, new_address: AKO + ' ' + AEN, agent_name: APOS },
  F09: { name: APOS, applicant_name: APOS },
  F10: { p_name: APOS, a_name: APOS, purpose: MIX + ' 인사팀 제출용 재직 확인', applicant_name: APOS },
  F11: { name: APOS, address: AKO, email: MAIL, applicant_name: APOS },
  F12: { name: APOS, employment: EMP + ' / ' + MIX, address_korea: AKO, address_home: AEN, ext_reason: REASON },
  F13: { name: APOS, address: AKO, email: MAIL, prev_name: EMP, cur_name: MIX },
  F14: { company: EMP, email: MAIL, incident: REASON + ' ' + REASON, w1_name: APOS },
  F15: { name: APOS, name_en: APOS, applicant_name: APOS, applicant_name_en: APOS, q9_text: INST },
};
const report = {};
for (const [fid, vals] of Object.entries(cases)) {
  const spec = S[fid]; const lay = E.layout(spec, vals, measure, glyphs, {});
  const sizes = {}; for (const o of lay.ops) if (o.type === 'text') sizes[o.key] = Math.min(sizes[o.key] ?? 99, o.size);
  report[fid] = { issues: lay.issues.map((i) => `${i.kind}:${i.key}${i.size ? '@' + i.size : ''}${i.chars ? ' chars=' + i.chars.join('') : ''}`), sizes };
  const doc = await PDFLib.PDFDocument.load(fs.readFileSync(ROOT + '/' + spec.pdf)); doc.registerFontkit(fontkit);
  const pf = await doc.embedFont(fontBytes); const pages = doc.getPages(); const H = spec.pageHeight; const ink = PDFLib.rgb(0.1, 0.1, 0.45);
  for (const op of lay.ops) if (op.type === 'text') pages[op.page].drawText(op.text, { x: op.x, y: H - op.y, size: op.size, font: pf, color: ink });
  fs.writeFileSync(`${OUT}/${fid}.pdf`, await doc.save()); fs.writeFileSync(`${OUT}/${fid}-ops.json`, JSON.stringify({ form: fid, edition: fid, ops: lay.ops }));
}
console.log(JSON.stringify(report, null, 1));
