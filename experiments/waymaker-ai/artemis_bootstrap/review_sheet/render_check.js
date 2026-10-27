// Render the published review page with the published cases.json and a fake db,
// then check what a reviewer would see. Usage: node render_check.js <page.html> <cases.json> <legacy_dir>
const fs = require("fs");
const path = require("path");
const { JSDOM } = require("jsdom");

const [pagePath, casesPath, legacyDir] = process.argv.slice(2);
const html = fs.readFileSync(pagePath, "utf8");
const cases = JSON.parse(fs.readFileSync(casesPath, "utf8"));
const legacy = {};
for (const f of fs.readdirSync(legacyDir)) legacy[f.replace(/\.json$/, "")] = JSON.parse(fs.readFileSync(path.join(legacyDir, f), "utf8"));

const writes = [];
const stores = { reviews: legacy, reviews_v2: {}, ai_reviews: {} };
function collection(name) {
  const q = {
    limit: () => q,
    onSnapshot(next) {
      const emit = () => next({ docs: Object.entries(stores[name] || {}).map(([id, d]) => ({ id, exists: true, data: () => d })) });
      setTimeout(emit, 0);
      (q._subs = q._subs || []).push(emit);
      collection._subs[name] = emit;
      return () => {};
    },
    doc(id) {
      return { set: async (body) => { writes.push({ collection: name, id, body }); stores[name][id] = body; collection._subs[name] && collection._subs[name](); } };
    },
  };
  return q;
}
collection._subs = {};

const dom = new JSDOM(`<!doctype html><html><head></head><body>${html}</body></html>`, {
  runScripts: "dangerously",
  pretendToBeVisual: true,
  beforeParse(window) {
    window.fetch = async (url) => ({ ok: true, json: async () => JSON.parse(JSON.stringify(cases)) });
    window.matchMedia = () => ({ matches: false, addEventListener() {}, removeEventListener() {} });
    window.HTMLElement.prototype.scrollIntoView = () => {};
    window.claude = { use: async (name) => name === "db" ? { collection } : name === "user" ? { id: async () => "u_test", can: async () => true } : null };
  },
});
const { window } = dom;
const doc = window.document;
const results = [];
const check = (label, ok, detail = "") => results.push({ label, ok: !!ok, detail });
const wait = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
  await wait(300);
  const counts = doc.getElementById("counts").textContent;
  check("counts show v2 verdicts, read-only legacy count 140/140 and no legal completion", /v2 기준 새 판정 0 \/ 140/.test(counts) && /기존 저장 판정 140 \/ 140 \(읽기 전용\)/.test(counts) && /법률 검증 완료: 확인된 것 없음/.test(counts) && /v2에서 바뀐 라벨 9/.test(counts), counts);
  const items = [...doc.querySelectorAll("#list .item")];
  check("list has all 140 cases in bundle order", items.length === 140 && items[0].dataset.key === cases.cases[0].key && items[139].dataset.key === cases.cases[139].key, String(items.length));

  const open = async (key) => { doc.querySelector(`#list .item[data-key="${key}"]`).click(); await wait(50); return doc.getElementById("case").textContent; };
  let t = await open("manual_oracle/M-10-d10t-stay-cap");
  check("M-10 shows label v2 decision and structural rules", t.includes("v2 수정 채택") && t.includes("총 체류기간 상한 3년") && t.includes("1회 기간을 3년으로 씀(뒤바뀜)") && t.includes("검증 보류"), "");
  check("M-10 shows saved human verdict read-only with provenance", t.includes("기존 저장 판정 (읽기 전용") && t.includes("기존 사람 판정(인계 기록 기준)"), "");
  check("M-10 shows the post-hoc regrade (실패 → 통과)", t.includes("원본 실패 → v2 통과"), "");

  t = await open("manual_misclick/K-14-d8-4-where-to-apply-misclick");
  check("K-14 shows new evidence page and 'not comparable'", t.includes("visa_manual_2026_10_19_pdf#p108") && t.includes("비교 불가(근거 쪽이 바뀜)") && t.includes("열린 쟁점"), "");
  check("K-14 renders the p108 page text", t.includes("나. 신청기관"), "");

  t = await open("manual_clarify/Q-11-e9-change-jobs-count");
  check("Q-11 shows the flag-only rule and ChatGPT proposal note", t.includes("사람 확인 표시만") && t.includes("ChatGPT 부분 수정본 제안이 있었음") && t.includes("ChatGPT 2차 의견(인계 기록 기준)"), "");

  t = await open("manual_routing/N-01-c1-visa-attachments");
  check("an unchanged case says pending / original kept", t.includes("v2 보류(원본 유지)") && !t.includes("v2 있어야 할 사실 구조"), "");

  // Save a verdict: it must go to reviews_v2 and never to reviews.
  await open("manual_oracle/M-10-d10t-stay-cap");
  doc.getElementById("v_ok").checked = true;
  doc.getElementById("reviewForm").dispatchEvent(new window.Event("submit", { cancelable: true, bubbles: true }));
  await wait(100);
  check("saving writes only to reviews_v2", writes.length === 1 && writes[0].collection === "reviews_v2" && writes[0].body.label_version === "v2", JSON.stringify(writes.map((w) => w.collection)));
  check("legacy M-10 verdict object untouched in the fake store", stores.reviews["manual_oracle_M-10-d10t-stay-cap"].verdict === legacy["manual_oracle_M-10-d10t-stay-cap"].verdict);
  const counts2 = doc.getElementById("counts").textContent;
  check("counts update to 1 new verdict while legacy stays 140", /v2 기준 새 판정 1 \/ 140/.test(counts2) && /기존 저장 판정 140 \/ 140/.test(counts2), counts2);

  for (const r of results) console.log(`${r.ok ? "PASS" : "FAIL"}  ${r.label}${r.ok ? "" : "  -- " + r.detail}`);
  const failed = results.filter((r) => !r.ok).length;
  console.log(`${results.length - failed}/${results.length} passed`);
  process.exit(failed ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(2); });
