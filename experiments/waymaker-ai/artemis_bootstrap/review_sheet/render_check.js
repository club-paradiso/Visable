// Render the published review page with the published cases.json and a fake db,
// then check what a reviewer would see. Usage: node render_check.js <page.html> <cases.json> <legacy_dir>
const fs = require("fs");
const path = require("path");
const { JSDOM } = require("jsdom");

const [pagePath, casesPath, legacyDir, factsPath] = process.argv.slice(2);
const html = fs.readFileSync(pagePath, "utf8");
const cases = JSON.parse(fs.readFileSync(casesPath, "utf8"));
const facts = factsPath ? JSON.parse(fs.readFileSync(factsPath, "utf8")) : null;
const legacy = {};
for (const f of fs.readdirSync(legacyDir)) legacy[f.replace(/\.json$/, "")] = JSON.parse(fs.readFileSync(path.join(legacyDir, f), "utf8"));

const writes = [];
const stores = { reviews: legacy, reviews_v2: {}, ai_reviews: {}, facts_review: {} };
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
    window.fetch = async (url) => ({ ok: true, json: async () => JSON.parse(JSON.stringify(String(url).includes("facts") ? facts : cases)) });
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
  check("counts show v2 verdicts, read-only legacy count 140/140 and no legal completion", /v2 기준 새 판정 0 \/ 140/.test(counts) && /기존 저장 판정 140 \/ 140 \(읽기 전용\)/.test(counts) && /법률 검증 완료: 확인된 것 없음/.test(counts) && /v2에서 바뀐 라벨 116/.test(counts) && /사람 판단 필요 0/.test(counts) && /법령과 다름 1/.test(counts) && /기록 답 v2 검토 필요 표시 \d+ \(자동 정답에서 제외\)/.test(counts), counts);
  const items = [...doc.querySelectorAll("#list .item")];
  check("list has all 140 cases in bundle order", items.length === 140 && items[0].dataset.key === cases.cases[0].key && items[139].dataset.key === cases.cases[139].key, String(items.length));

  const open = async (key) => { doc.querySelector(`#list .item[data-key="${key}"]`).click(); await wait(50); return doc.getElementById("case").textContent; };
  let t = await open("manual_oracle/M-10-d10t-stay-cap");
  check("M-10 shows label v2 decision and structural rules", t.includes("v2 수정 채택") && t.includes("총 체류기간 상한 3년") && t.includes("1회 기간을 3년으로 씀(뒤바뀜)") && t.includes("검증 보류"), "");
  check("M-10 shows saved human verdict read-only with provenance", t.includes("기존 저장 판정 (읽기 전용") && t.includes("기존 사람 판정(인계 기록 기준)"), "");
  check("M-10 shows the post-hoc regrade (실패 → 자동 정답)", t.includes("원본 실패 → v2 자동 정답"), "");

  t = await open("manual_misclick/K-14-d8-4-where-to-apply-misclick");
  check("K-14 shows new evidence page and 'not comparable'", t.includes("visa_manual_2026_10_19_pdf#p108") && t.includes("비교 불가(근거 쪽이 바뀜)") && t.includes("열린 쟁점"), "");
  check("K-14 renders the p108 page text", t.includes("나. 신청기관"), "");

  t = await open("manual_clarify/Q-11-e9-change-jobs-count");
  check("Q-11 shows the review-only rule, the review banner and ChatGPT proposal note", t.includes("v2 검토 필요로 돌리는 표현") && t.includes("검토 필요:") && t.includes("재고용(연장) 기간을 말하면서 2회 상한을 쓰지 않음") && t.includes("v2 실패: 원문과 모순") && t.includes("ChatGPT 부분 수정본 제안이 있었음") && t.includes("ChatGPT 2차 의견(인계 기록 기준)"), "");

  t = await open("manual_routing/N-06-h1-canada-weekly-hours");
  check("N-06 shows the new rule, the post-hoc failure and the guide kept out of the label", t.includes("40시간을 체류기간으로 씀") && t.includes("원본 통과 → v2 실패: 원문과 모순") && t.includes("whic.mofa.go.kr") && t.includes("검증 보류"), "");

  t = await open("manual_buttons/B-16-h1-job-change");
  check("B-16 shows the owner decision, the kept statute difference and its source", t.includes("소유자 결정(매뉴얼 기준)") && t.includes("매뉴얼을 기준으로 판단해서 결정짓자") && t.includes("법령과 다름") && t.includes("제21조") && t.includes("v2 있어야 할 사실 구조"), "");

  t = await open("manual_buttons/B-23-e9-going-home-briefly");
  check("B-23 shows the answer-only rules", t.includes("바로 답한 경우에만 보는 것") && t.includes("재입국허가 면제"), "");

  t = await open("manual_misclick/K-08-multiple-reentry");
  check("K-08 shows the settled label and the re-classified statute note", t.includes("AI 3차 검토로 바뀜") && t.includes("법령과 같음") && t.includes("[재분류]") && t.includes("제44조의2"), "");

  t = await open("manual_routing/N-03-d9-equipment-visa-docs");
  check("N-03 shows the AI round-3 change and the manual-standard note", t.includes("AI 3차 검토로 바뀜") && t.includes("법령에 없는 매뉴얼 운영기준") && t.includes("유의 사항 1") && t.includes("법률 검증 아님"), "");

  // Save a verdict: it must go to reviews_v2 and never to reviews.
  await open("manual_oracle/M-10-d10t-stay-cap");
  doc.getElementById("v_ok").checked = true;
  doc.getElementById("reviewForm").dispatchEvent(new window.Event("submit", { cancelable: true, bubbles: true }));
  await wait(100);
  check("saving writes only to reviews_v2", writes.length === 1 && writes[0].collection === "reviews_v2" && writes[0].body.label_version === "v2", JSON.stringify(writes.map((w) => w.collection)));
  check("legacy M-10 verdict object untouched in the fake store", stores.reviews["manual_oracle_M-10-d10t-stay-cap"].verdict === legacy["manual_oracle_M-10-d10t-stay-cap"].verdict);
  const counts2 = doc.getElementById("counts").textContent;
  check("counts update to 1 new verdict while legacy stays 140", /v2 기준 새 판정 1 \/ 140/.test(counts2) && /기존 저장 판정 140 \/ 140/.test(counts2), counts2);

  if (facts) {
    doc.getElementById("tabFacts").click();
    await wait(300);
    const fc = doc.getElementById("fCounts").textContent;
    check("facts tab loads every candidate and says it is not a legal verification", fc.includes(`후보 ${facts.candidates.length}`) && fc.includes("법률 검증 아님") && doc.body.classList.contains("facts-mode"), fc);
    const items = doc.querySelectorAll("#fList .item");
    check("facts list shows all candidates", items.length === facts.candidates.length, String(items.length));
    const first = facts.candidates[0];
    const fcase = doc.getElementById("fCase").textContent;
    check("a candidate shows its quote and page text", fcase.includes(first.source.quote) && doc.querySelector("#fCase mark") !== null, "");
    const ai = (facts.ai_first_pass || {})[first.candidate_id];
    if (ai) {
      check("the AI first-pass opinion is shown and marked as not a human decision", doc.getElementById("fCase").textContent.includes("AI 1차 의견 (사람 판정 아님)"), "");
      if (doc.getElementById("fxFillAi")) {
        doc.getElementById("fxFillAi").click(); await wait(20);
        check("filling from the AI opinion does not save anything", !writes.some((w) => w.collection === "facts_review") && doc.getElementById("fSaveState").textContent.includes("확인한 뒤"), "");
      }
    }
    const fin = (facts.ai_final || {})[first.candidate_id];
    if (fin) check("the AI final decision is shown as owner-delegated, not a human approval", doc.getElementById("fCase").textContent.includes("AI 최종 결정 (소유자 위임, 사람 승인 아님)"), "");
    doc.getElementById("fx_role").value = "";
    doc.querySelector('#fCase [data-d="approve"]').click();
    await wait(50);
    check("approving without a role is refused", doc.getElementById("fSaveState").textContent.includes("역할을 골라") && !writes.some((w) => w.collection === "facts_review"), "");
    doc.getElementById("fx_role").value = "fee";
    doc.getElementById("fx_house").value = "2";
    doc.querySelector('#fCase [data-d="approve"]').click();
    await wait(100);
    const fw = writes.filter((w) => w.collection === "facts_review");
    check("an edited approval is saved to facts_review only, with source unchanged", fw.length === 1 && fw[0].body.decision === "approved_edited" && fw[0].body.role === "fee" && fw[0].body.subject.qualifiers.household_size === 2 && JSON.stringify(fw[0].body.source) === JSON.stringify(first.source) && !writes.some((w) => w.collection === "reviews"), JSON.stringify(fw.map((w) => w.body.decision)));
    check("label desk carries label-only so facts mode hides it", doc.getElementById("case").closest(".desk").classList.contains("label-only"), "");
  }

  for (const r of results) console.log(`${r.ok ? "PASS" : "FAIL"}  ${r.label}${r.ok ? "" : "  -- " + r.detail}`);
  const failed = results.filter((r) => !r.ok).length;
  console.log(`${results.length - failed}/${results.length} passed`);
  process.exit(failed ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(2); });
