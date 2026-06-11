#!/usr/bin/env node
/*
 * Paradiso — repository-wide official-document duplicate & grouping audit.
 *
 * Scans EVERY top-level record, subcode, scenario variant, procedure tab and
 * document array discovered dynamically in visa_data.json (no hardcoded code
 * list). It simulates the index.html render merge (PROCEDURE_CONFIG field
 * aliases + DOC_DICT id resolution) so the report reflects what users would
 * actually see, before and after the render-layer dedupe guard.
 *
 * Modes:
 *   node audit_document_duplicates.js --mode before
 *   node audit_document_duplicates.js --mode after
 *   node audit_document_duplicates.js --mode after --fail-on-unresolved
 *
 * "before" reports duplicates with the pre-patch dedupe behaviour (raw-entry
 * canonical keys; doc_* ids NOT resolved before keying — the regression).
 * "after" reports duplicates with the patched behaviour (ids resolved through
 * DOC_DICT before canonicalization + specificity-preferring merge), mirroring
 * the PARADISO_DOC_RENDER_DEDUPE_HELPERS in index.html. Mirror contract:
 * canonicalization rules here must stay in sync with
 * paradisoCanonicalDocKey20260609 / canonicalDocDedupeKey in index.html.
 *
 * No external dependencies. Never mutates visa_data.json.
 */
'use strict';

const fs = require('fs');
const path = require('path');

const REPO = path.resolve(__dirname, '..', '..');
const OUT = __dirname;

const args = process.argv.slice(2);
function argValue(flag, dflt) {
  const i = args.indexOf(flag);
  return i >= 0 && args[i + 1] ? args[i + 1] : dflt;
}
const MODE = argValue('--mode', 'before');
const FAIL_ON_UNRESOLVED = args.includes('--fail-on-unresolved');
if (!['before', 'after'].includes(MODE)) {
  console.error(`Unknown --mode ${MODE}; expected before|after`);
  process.exit(2);
}

const visaData = JSON.parse(fs.readFileSync(path.join(REPO, 'visa_data.json'), 'utf8'));
const docMaster = JSON.parse(fs.readFileSync(path.join(REPO, 'doc_master.json'), 'utf8'));

/* ── DOC_DICT extraction ────────────────────────────────────────────────────
 * The render layer resolves doc_* ids through index.html's DOC_DICT (richer,
 * hand-maintained labels). Extract that object literal so the audit sees the
 * same labels users see; fall back to doc_master.json ko_name for safety. */
function extractDocDict() {
  const html = fs.readFileSync(path.join(REPO, 'index.html'), 'utf8');
  const m = html.match(/const DOC_DICT = \{[\s\S]*?\n\};/);
  if (!m) return null;
  try {
    // Trusted repo-local source; evaluated in isolation.
    return new Function(`${m[0].replace(/^const /, 'var ')}; return DOC_DICT;`)();
  } catch (e) {
    return null;
  }
}
const DOC_DICT = extractDocDict() || {};
for (const entry of docMaster) {
  if (entry && entry.id && !DOC_DICT[entry.id] && entry.ko_name) DOC_DICT[entry.id] = entry.ko_name;
}

/* Extract the SHIPPED render-guard helpers from index.html (between the
 * PARADISO_DOC_RENDER_GUARD markers) so the "after" simulation measures the
 * exact production logic instead of a hand-kept mirror. */
function extractRenderGuard() {
  const html = fs.readFileSync(path.join(REPO, 'index.html'), 'utf8');
  const m = html.match(/\/\* PARADISO_DOC_RENDER_GUARD_BEGIN[\s\S]*?PARADISO_DOC_RENDER_GUARD_END \*\//);
  if (!m) return null;
  try {
    const factory = new Function('DOC_DICT', 'isDocPlaceholder', `
      ${m[0]}
      return {
        resolveLabel: paradisoResolveDocDisplayLabel,
        splitCompound: paradisoSplitCompoundDocRow,
        familyKey: paradisoCanonicalDocKey20260609,
        isBareGeneric: paradisoIsBareGenericDocLabel,
        dedupeAcross: dedupeDocGroupsAcrossCategories,
        isDiscretionary: paradisoIsDiscretionaryDocText,
        buildDisplayGroups: paradisoBuildDocDisplayGroups,
        mergeTabItems: paradisoMergeDocumentTabItemsForDisplay
      };
    `);
    return factory(DOC_DICT, isPlaceholder);
  } catch (e) {
    console.error('[audit] WARN: render-guard extraction failed:', e.message);
    return null;
  }
}

/* ── Render-merge simulation (mirrors index.html) ─────────────────────────── */
const PROCEDURE_CONFIG = [
  { key: 'visaIssuance', label: '사증발급', docFields: { requiredDocs: ['initialReqDocs', 'newReqDocs', 'reqDocs', 'documents', 'requiredDocs', 'required_documents'], additionalDocs: ['addReqDocs'] } },
  { key: 'certificateOfVisaIssuance', label: '사증발급인정서', docFields: { requiredDocs: ['cviReqDocs'] } },
  { key: 'statusChange', label: '체류자격 변경', docFields: { requiredDocs: ['changeReqDocs', 'chgReqDocs'] } },
  { key: 'extension', label: '체류기간 연장', docFields: { requiredDocs: ['extensionReqDocs', 'extReqDocs'] } },
  { key: 'statusGrant', label: '체류자격 부여', docFields: { requiredDocs: ['statusGrantReqDocs'] } },
  { key: 'registration', label: '외국인등록', docFields: { requiredDocs: ['registrationReqDocs'] } },
  { key: 'activitiesOutsideStatus', label: '자격외활동', docFields: { requiredDocs: ['activitiesOutsideStatusReqDocs'] } },
  { key: 'workplaceChange', label: '근무처 변경·추가', docFields: { requiredDocs: ['workplaceChangeReqDocs'] } },
  { key: 'reentry', label: '재입국', docFields: { requiredDocs: ['reentryReqDocs'] } },
  { key: 'partTimeWork', label: '시간제취업(자격외활동)', docFields: { requiredDocs: [] } },
  { key: 'schoolChange', label: '학교변경(신고)', docFields: { requiredDocs: [] } }
];
const BUCKET_KEYS = ['commonDocs', 'requiredDocs', 'additionalDocs', 'conditionalDocs'];

const PLACEHOLDERS = new Set([
  '매뉴얼 확인 필요', '페이지 확인 필요', 'Manual review needed', 'Page review needed',
  '문서명 미상', '비고 정보 없음', 'DATA_MISSING', 'Document name unknown', 'No note available'
]);
const isPlaceholder = v => PLACEHOLDERS.has(String(v || '').trim());

function toDocArray(value) {
  if (!value) return [];
  if (Array.isArray(value)) return value.flatMap(toDocArray);
  if (typeof value === 'string') {
    const v = value.trim();
    return v && !isPlaceholder(v) ? [v] : [];
  }
  if (typeof value === 'object') {
    const label = value.name || value.label || value.title || value.text || value.description;
    return label ? [String(label).trim()].filter(v => v && !isPlaceholder(v)) : [];
  }
  return [String(value).trim()].filter(v => v && !isPlaceholder(v));
}

function resolveLabel(entry) {
  const s = String(entry || '').trim();
  if (s.startsWith('doc_')) return DOC_DICT[s] || s;
  return s;
}

// Shipped render-guard (always extracted; used for after-mode simulation and
// for semantic family identity in reports).
const GUARD = extractRenderGuard();
if (MODE === 'after' && !GUARD) {
  console.error('[audit] FAIL: could not extract PARADISO_DOC_RENDER_GUARD from index.html');
  process.exit(2);
}

/* After-mode surfaces split compound one-line rows exactly like production
 * toDocArray does (parts inherit the row's bucket/origin). */
function expandItems(items) {
  if (MODE !== 'after' || !GUARD) return items;
  return items.flatMap(it => {
    const parts = GUARD.splitCompound(it.label);
    return parts ? parts.map(p => ({ ...it, label: p })) : [it];
  });
}

/* Canonical duplicate-family key. MIRROR of index.html canonicalDocDedupeKey
 * ("after" behaviour resolves doc_* ids through DOC_DICT first — that ID
 * resolution is exactly the regression fix; "before" keys the raw entry). */
function canonicalKey(entry, resolveIds) {
  // Semantic (resolved) identity comes from the shipped guard when available.
  if (resolveIds && GUARD) return GUARD.familyKey(entry);
  let text = String(entry || '');
  if (resolveIds) text = resolveLabel(text);
  text = text.normalize('NFKC').trim();
  if (!text || isPlaceholder(text)) return '';
  text = text
    .replace(/^\s*[①-⑳0-9]+[.)]?\s*/g, '')
    .replace(/\s+/g, '')
    .replace(/[ㆍ·•]/g, '')
    .replace(/[()［］\[\]{}]/g, '')
    .replace(/별지제?34호서식/g, '')
    .replace(/원본및사본1부/g, '')
    .replace(/원본/g, '')
    .replace(/사본/g, '')
    .trim();

  if (/^통합?신청서|^신청서/.test(text)) return '신청서';
  if (/^사증발급신청서/.test(text)) return '사증발급신청서';
  if (/^여권용사진|^표준규격사진|^사진|^반명함판/.test(text)) return '표준규격사진';
  if (/^여권/.test(text)) return '여권';
  if (/^외국인등록증|^등록증|^거소증/.test(text)) return '외국인등록증';
  if (/^수수료/.test(text)) return '수수료';
  if (/^표준입학허가서/.test(text)) return '표준입학허가서';
  if (/^교육기관사업자등록증|^교육기관고유번호증|^사업자등록증|^고유번호증/.test(text)) return '교육기관사업자등록증';
  if (/^재학증명서|^재학연구생증명서|^재학을입증하는서류/.test(text)) return '재학증명서';
  if (/^성적증명서|^출석확인서|^학업을정상적으로수행|^학업정상수행입증서류/.test(text)) return '학업수행입증서류';
  if (/^재정입증|^재정능력/.test(text)) return '재정입증서류';
  if (/^체류지입증/.test(text)) return '체류지입증서류';
  if (/^가족관계/.test(text)) return '가족관계입증서류';
  if (/^결핵/.test(text)) return '결핵진단서';
  if (/수료증명서.*지도교수|지도교수.*유학담당자|수료증명서.*유학담당자/.test(text)) return '수료증명서·지도교수확인서';
  return text;
}

/* Discretionary catch-all language → 심사 중 추가 요청 가능 (caution note). */
const DISCRETIONARY_RE = /(기타\s*심사에\s*필요(하다고)?\s*(인정)?(하는|되는)?\s*서류|심사\s*(과정)?에서\s*추가\s*서류|추가\s*서류\s*제출을\s*요구|서류.*가감될\s*수|출입국[·\s]*외국인(청|관서)장이\s*.*인정하는\s*서류)/;

const UX_GROUP_BY_BUCKET = {
  commonDocs: '기본 준비서류',
  requiredDocs: '기본 준비서류',
  additionalDocs: '상황별 추가서류',
  conditionalDocs: '상황별 추가서류'
};
function uxGroupFor(bucket, label) {
  if (DISCRETIONARY_RE.test(String(label || ''))) return '심사 중 추가 요청 가능';
  return UX_GROUP_BY_BUCKET[bucket] || 'UNGROUPED_REQUIRES_REVIEW';
}

/* ── Classification overrides for families that legitimately repeat ────────
 * Keys: `${code}|${context}|${canonicalKey}` or `*|*|${canonicalKey}`.
 * Values: DISTINCT_REQUIREMENTS | AMBIGUOUS_TABLE_CONTEXT | OFFICIAL_DUAL_LISTING
 * Populated from the PHASE 4 manual evidence review. */
const FAMILY_CLASSIFICATION_OVERRIDES = {
  // (none required after render-guard merge; kept for future audited cases)
};

/* ── Discovery walk ──────────────────────────────────────────────────────── */
const FLAT_DOC_FIELDS = [
  'newReqDocs', 'extReqDocs', 'initialReqDocs', 'extensionReqDocs', 'changeReqDocs', 'chgReqDocs',
  'addReqDocs', 'cviReqDocs', 'statusGrantReqDocs', 'registrationReqDocs',
  'activitiesOutsideStatusReqDocs', 'workplaceChangeReqDocs', 'reentryReqDocs', 'reqDocs'
];
const OBJECT_DOC_FIELDS = ['documents_initial', 'documents_extension', 'documents_registration'];
// Fields that look documenty but are prose/metadata, never checklists:
const PROSE_FIELD_DENYLIST = new Set([
  'newReq', 'extReq', 'changeReq', 'addReq', 'faq', 'note', 'notes', 'summary',
  'manualRequiredDocAudit', '_source_notes', 'searchAliases', '_searchAliasAudit',
  'structuredRequirementsRef', 'sourceManualStatus', 'commonWarnings', 'manualRefs'
]);

const matrixRows = [];      // every discovered document array
const dupFindings = [];     // duplicate families per render surface
const groupingRows = [];    // bucket → UX group proposals
let totalLabels = 0;
const discoveredBucketNames = new Set();

function addMatrixRow(row) { matrixRows.push(row); }

function scanArraySurface({ code, sub, context, jsonPath, bucketName, entries }) {
  const labels = toDocArray(entries);
  totalLabels += labels.length;
  discoveredBucketNames.add(bucketName);
  const fams = duplicateFamilies(labels.map(l => ({ label: l, bucket: bucketName })));
  addMatrixRow({
    code, sub: sub || '', context, jsonPath,
    sourceBucket: bucketName,
    uxGroup: labels.length ? uxGroupSummary(bucketName, labels) : '(빈 배열)',
    count: labels.length,
    dupFamilies: fams.length,
    action: fams.length ? 'render guard' : (labels.length ? 'render guard (커버됨)' : 'skip: no document array')
  });
  return labels;
}

function uxGroupSummary(bucket, labels) {
  const groups = new Set(labels.map(l => uxGroupFor(bucket, l)));
  return [...groups].join(' + ');
}

/* Find duplicate families inside one merged render surface.
 * Family identity ALWAYS resolves doc_* ids first — that is the semantic
 * truth of what the user sees once DOC_DICT resolution happens at render. */
function duplicateFamilies(items) {
  const byKey = new Map();
  for (const it of items) {
    const key = canonicalKey(it.label, true);
    if (!key) continue;
    if (!byKey.has(key)) byKey.set(key, []);
    byKey.get(key).push(it);
  }
  const fams = [];
  for (const [key, members] of byKey) {
    if (members.length > 1) fams.push({ key, members });
  }
  return fams;
}

/* BEFORE mode: simulate today's production render exactly —
 * (1) dedupeDocs: exact trimmed-string dedupe across the merged list;
 * (2) dedupeDocGroupsAcrossCategories: canonical-key dedupe on the RAW entry
 *     (doc_* ids NOT resolved — the regression under audit). */
function simulateCurrentRender(items) {
  const exactSeen = new Set();
  const rawKeySeen = new Set();
  const kept = [];
  for (const it of items) {
    const exact = String(it.label || '').trim();
    if (!exact || exactSeen.has(exact)) continue;
    exactSeen.add(exact);
    const rawKey = canonicalKey(it.label, false);
    if (rawKey && rawKeySeen.has(rawKey)) continue;
    if (rawKey) rawKeySeen.add(rawKey);
    kept.push(it);
  }
  return kept;
}

/* "After" mode: simulate the render guard — resolve ids, dedupe across the
 * merged surface keeping the most specific label at the earliest position. */
function specificity(label) {
  const s = resolveLabel(label);
  let score = s.length;
  if (/별지\s*제?\d+호|서식/.test(s)) score += 40;
  if (/[(（]/.test(s)) score += 10;
  if (/통합신청서/.test(s)) score += 20;
  return score;
}
function simulateGuard(items) {
  const expanded = expandItems(items);
  const seen = new Map(); // canonical key -> kept item
  const kept = [];
  for (const it of expanded) {
    const key = canonicalKey(it.label, true);
    if (!key) { continue; }
    if (!seen.has(key)) {
      const copy = { ...it };
      seen.set(key, copy);
      kept.push(copy);
      continue;
    }
    const cur = seen.get(key);
    if (GUARD) {
      // Mirror of dedupeDocGroupsAcrossCategories' in-place label upgrade.
      const priorLabel = GUARD.resolveLabel(cur.label);
      const nextLabel = GUARD.resolveLabel(it.label);
      if (
        GUARD.isBareGeneric(priorLabel) &&
        nextLabel.length > priorLabel.length &&
        !(/또는/.test(nextLabel) && !/또는/.test(priorLabel))
      ) cur.label = it.label;
    } else if (specificity(it.label) > specificity(cur.label)) {
      cur.label = it.label;
    }
  }
  return kept;
}

/* ── Walk all records ────────────────────────────────────────────────────── */
const perCodeSummary = [];
for (const rec of visaData) {
  const code = rec.code || '(no code)';
  let arraysFound = 0;
  const surfaceFindings = [];

  // 1) Procedure tabs: simulate the getProcedure merge per tab, preserving
  //    production group order (common → required[raw,legacy] → additional → conditional).
  const procs = rec.procedures && typeof rec.procedures === 'object' ? rec.procedures : {};
  for (const cfg of PROCEDURE_CONFIG) {
    const raw = procs[cfg.key];
    const grouped = { commonDocs: [], requiredDocs: [], additionalDocs: [], conditionalDocs: [] };
    if (raw && raw.requiredDocs && typeof raw.requiredDocs === 'object') {
      for (const bk of BUCKET_KEYS) {
        const arr = toDocArray(raw.requiredDocs[bk]);
        if (Array.isArray(raw.requiredDocs[bk])) {
          arraysFound++;
          scanArraySurface({
            code, context: `절차탭:${cfg.label}`, jsonPath: `procedures.${cfg.key}.requiredDocs.${bk}`,
            bucketName: bk, entries: raw.requiredDocs[bk]
          });
        }
        arr.forEach(label => grouped[bk].push({ label, bucket: bk, origin: `procedures.${cfg.key}.requiredDocs.${bk}` }));
      }
    }
    for (const f of (cfg.docFields.requiredDocs || [])) {
      if (Array.isArray(rec[f])) {
        toDocArray(rec[f]).forEach(label => grouped.requiredDocs.push({ label, bucket: 'requiredDocs', origin: f }));
      }
    }
    for (const f of (cfg.docFields.additionalDocs || [])) {
      if (Array.isArray(rec[f])) {
        toDocArray(rec[f]).forEach(label => grouped.additionalDocs.push({ label, bucket: 'additionalDocs', origin: f }));
      }
    }
    const merged = BUCKET_KEYS.flatMap(bk => grouped[bk]);
    if (!merged.length) continue;

    const items = MODE === 'after' ? simulateGuard(merged) : simulateCurrentRender(merged);
    const fams = duplicateFamilies(items);
    if (fams.length) {
      surfaceFindings.push({ surface: `절차탭:${cfg.label}`, fams });
      for (const fam of fams) {
        dupFindings.push({
          code, context: `절차탭:${cfg.label}`, key: fam.key,
          members: fam.members.map(m => `${resolveLabel(m.label)}  [${m.origin || m.bucket}]`),
          classification: FAMILY_CLASSIFICATION_OVERRIDES[`${code}|절차탭:${cfg.label}|${fam.key}`]
            || FAMILY_CLASSIFICATION_OVERRIDES[`*|*|${fam.key}`] || 'UNRESOLVED'
        });
      }
    }

    // Variants (scenario records) — rendered with parent docs subtracted.
    const variants = Array.isArray(raw && raw.variants) ? raw.variants : [];
    variants.forEach((vt, vi) => {
      const vid = vt.id || vt.statusCode || `variant${vi}`;
      const vitems = [];
      const vrd = vt.requiredDocs && typeof vt.requiredDocs === 'object' ? vt.requiredDocs : {};
      for (const bk of BUCKET_KEYS) {
        if (Array.isArray(vrd[bk])) {
          arraysFound++;
          scanArraySurface({
            code, sub: vid, context: `시나리오:${cfg.label}`, jsonPath: `procedures.${cfg.key}.variants[${vi}].requiredDocs.${bk}`,
            bucketName: bk, entries: vrd[bk]
          });
          toDocArray(vrd[bk]).forEach(label => vitems.push({ label, bucket: bk, origin: `variant.${bk}` }));
        }
      }
      if (!vitems.length) return;
      const parentShown = MODE === 'after' ? simulateGuard(merged) : simulateCurrentRender(merged);
      const parentKeys = new Set(parentShown.map(m => canonicalKey(m.label, MODE === 'after')).filter(Boolean));
      const effective = (MODE === 'after')
        ? simulateGuard(vitems).filter(it => !parentKeys.has(canonicalKey(it.label, true)))
        : simulateCurrentRender(vitems).filter(it => !parentKeys.has(canonicalKey(it.label, false)));
      // Report families still visible (resolved-key identity) PLUS variant rows
      // that semantically repeat a parent row the raw-key subtraction missed.
      const vfams = duplicateFamilies(effective);
      if (MODE === 'before') {
        const parentResolved = new Set(parentShown.map(m => canonicalKey(m.label, true)).filter(Boolean));
        for (const it of effective) {
          const rk = canonicalKey(it.label, true);
          if (rk && parentResolved.has(rk) && !vfams.some(f => f.key === rk)) {
            vfams.push({ key: rk, members: [it, { label: '(부모 절차 패널에 동일 항목 노출)', origin: 'parent-panel' }] });
          }
        }
      }
      if (vfams.length) {
        for (const fam of vfams) {
          dupFindings.push({
            code, context: `시나리오:${cfg.label}/${vid}`, key: fam.key,
            members: fam.members.map(m => `${resolveLabel(m.label)}  [${m.origin}]`),
            classification: FAMILY_CLASSIFICATION_OVERRIDES[`${code}|시나리오:${cfg.key}|${fam.key}`] || 'UNRESOLVED'
          });
        }
      }
    });
  }

  // 2) Flat record-level doc-id arrays (also covered in tab merge above, but
  //    listed individually so no array is silently skipped).
  for (const f of FLAT_DOC_FIELDS) {
    if (Array.isArray(rec[f])) {
      arraysFound++;
      scanArraySurface({ code, context: '기록 직속 배열', jsonPath: f, bucketName: f, entries: rec[f] });
    }
  }

  // 3) documents_* (name/note objects; render in the three-tab strip when the
  //    procedure section owns no documents). After mode applies the shipped
  //    note-preserving family merge (paradisoMergeDocumentTabItemsForDisplay).
  for (const f of OBJECT_DOC_FIELDS) {
    if (Array.isArray(rec[f])) {
      arraysFound++;
      const labels = scanArraySurface({ code, context: '구비서류 탭(documents_*)', jsonPath: f, bucketName: f, entries: rec[f] });
      let stripLabels = labels;
      if (MODE === 'after' && GUARD && typeof GUARD.mergeTabItems === 'function') {
        const itemObjs = rec[f]
          .map(it => (typeof it === 'string' ? { name: it } : (it && typeof it === 'object' ? { name: it.name || it.label || '', note: it.note || '' } : null)))
          .filter(Boolean);
        stripLabels = GUARD.mergeTabItems(itemObjs).map(it => it.name).filter(Boolean);
      }
      const fams = duplicateFamilies(stripLabels.map(l => ({ label: l, bucket: f, origin: f })));
      fams.forEach(fam => dupFindings.push({
        code, context: `구비서류탭:${f}`, key: fam.key,
        members: fam.members.map(m => resolveLabel(m.label)),
        classification: FAMILY_CLASSIFICATION_OVERRIDES[`${code}|${f}|${fam.key}`] || 'UNRESOLVED'
      }));
    }
  }

  // 4) Subcodes (addReqDocs render in the subcode doc modal).
  const subs = Array.isArray(rec.subCodes) ? rec.subCodes : (Array.isArray(rec.subcodes) ? rec.subcodes : []);
  subs.forEach((sc, si) => {
    for (const f of ['addReqDocs', 'reqDocs', 'documents']) {
      if (Array.isArray(sc[f])) {
        arraysFound++;
        const labels = scanArraySurface({
          code, sub: sc.code || `sub${si}`, context: '세부코드 모달', jsonPath: `subCodes[${si}].${f}`,
          bucketName: f, entries: sc[f]
        });
        const items = labels.map(l => ({ label: l, bucket: f, origin: `${sc.code || si}.${f}` }));
        const fams = duplicateFamilies(MODE === 'after' ? simulateGuard(items) : simulateCurrentRender(items));
        fams.forEach(fam => dupFindings.push({
          code, context: `세부코드:${sc.code || si}`, key: fam.key,
          members: fam.members.map(m => resolveLabel(m.label)),
          classification: FAMILY_CLASSIFICATION_OVERRIDES[`${code}|${sc.code}|${fam.key}`] || 'UNRESOLVED'
        }));
      }
    }
  });

  // 5) Generic recursive sweep for unanticipated array-of-doc shapes so a new
  //    schema never gets silently skipped (excludes known prose fields).
  (function sweep(node, p) {
    if (!node || typeof node !== 'object') return;
    if (Array.isArray(node)) { node.forEach((v, i) => sweep(v, `${p}[${i}]`)); return; }
    for (const [k, v] of Object.entries(node)) {
      if (PROSE_FIELD_DENYLIST.has(k)) continue;
      const known = FLAT_DOC_FIELDS.includes(k) || OBJECT_DOC_FIELDS.includes(k) || BUCKET_KEYS.includes(k)
        || ['subCodes', 'subcodes', 'procedures', 'variants', 'requiredDocs'].includes(k);
      if (!known && Array.isArray(v) && /docs?$|documents?$|서류/i.test(k)) {
        addMatrixRow({
          code, sub: '', context: '동적 발견(미지 스키마)', jsonPath: `${p}.${k}`,
          sourceBucket: k, uxGroup: 'UNGROUPED_REQUIRES_REVIEW', count: toDocArray(v).length,
          dupFamilies: 0, action: 'AMBIGUOUS_STRUCTURE_REQUIRES_DEFER'
        });
      }
      sweep(v, `${p}.${k}`);
    }
  })(rec, code);

  if (!arraysFound) {
    addMatrixRow({
      code, sub: '', context: '-', jsonPath: '-', sourceBucket: '-', uxGroup: '-',
      count: 0, dupFamilies: 0, action: 'NO_DOCUMENT_ARRAY_FOUND'
    });
  }
  perCodeSummary.push({
    code, name: rec.name || '', arrays: arraysFound,
    dupSurfaces: surfaceFindings.length,
    flaggedFamilies: dupFindings.filter(d => d.code === code).length
  });
}

/* ── Grouping audit rows (source bucket → UX group mapping) ───────────────── */
for (const bucket of [...discoveredBucketNames].sort()) {
  groupingRows.push({
    sourceBucket: bucket,
    nature: BUCKET_KEYS.includes(bucket)
      ? 'Paradiso 내부 분류 키 (원문 매뉴얼 보편 표제 아님)'
      : (OBJECT_DOC_FIELDS.includes(bucket) ? '레거시 표시 배열(name/note)' : '레거시 doc-id 배열'),
    uxGroup: UX_GROUP_BY_BUCKET[bucket] || (bucket === 'conditionalDocs' ? '상황별 추가서류' : '기본 준비서류(맥락별)'),
    note: bucket === 'conditionalDocs'
      ? "'조건부 서류'는 보편 공식 표제가 아니므로 사용자 표기는 '상황별 추가서류'로 대체"
      : ''
  });
}

/* ── Reports ─────────────────────────────────────────────────────────────── */
const suffix = MODE === 'before' ? 'before' : 'after';
const topCodes = visaData.map(r => r.code);
const dupCodes = [...new Set(dupFindings.map(d => d.code))];
const unresolved = dupFindings.filter(d => d.classification === 'UNRESOLVED');

function table(rows, cols) {
  const head = `| ${cols.map(c => c.h).join(' | ')} |\n| ${cols.map(() => '---').join(' | ')} |`;
  const body = rows.map(r => `| ${cols.map(c => String(r[c.k] !== undefined ? r[c.k] : '')).replace ? '' : ''}`);
  return head + '\n' + rows.map(r => `| ${cols.map(c => String(r[c.k] ?? '').replace(/\|/g, '\\|')).join(' | ')} |`).join('\n');
}

const matrixMd = `# Paradiso 전수 문서 커버리지 매트릭스 (${suffix})

생성: ${new Date().toISOString()} · mode=${MODE}

## 발견 요약 (visa_data.json에서 동적 생성 — 하드코딩 코드 목록 없음)
- 최상위 코드 수: **${topCodes.length}**
- 최상위 코드 전체 목록: ${topCodes.join(', ')}
- 세부코드 수: ${visaData.reduce((n, r) => n + ((r.subCodes || r.subcodes || []).length), 0)}
- 절차 항목 수: ${visaData.reduce((n, r) => n + Object.keys(r.procedures || {}).length, 0)}
- 시나리오(변형) 수: ${visaData.reduce((n, r) => n + Object.values(r.procedures || {}).reduce((m, p) => m + ((p && p.variants) || []).length, 0), 0)}
- 발견된 문서 배열(행) 수: ${matrixRows.filter(r => r.jsonPath !== '-').length}
- 스캔된 문서 라벨 수: ${totalLabels}
- 발견된 원본(내부) 버킷 이름: ${[...discoveredBucketNames].sort().join(', ')}
- 중복 패밀리 보유 코드 수: ${dupCodes.length} (${dupCodes.join(', ') || '없음'})
- 미해결(UNRESOLVED) 패밀리 수: ${unresolved.length}

## 코드별 요약
${table(perCodeSummary, [
  { h: '코드', k: 'code' }, { h: '이름', k: 'name' }, { h: '문서 배열 수', k: 'arrays' },
  { h: '중복 표면 수', k: 'dupSurfaces' }, { h: '플래그 패밀리 수', k: 'flaggedFamilies' }
])}

## 전체 문서 배열 매트릭스
${table(matrixRows, [
  { h: '코드', k: 'code' }, { h: '세부/시나리오', k: 'sub' }, { h: '맥락', k: 'context' },
  { h: 'JSON 경로', k: 'jsonPath' }, { h: '원본 버킷', k: 'sourceBucket' },
  { h: '제안 UX 그룹', k: 'uxGroup' }, { h: '라벨 수', k: 'count' },
  { h: '중복 패밀리', k: 'dupFamilies' }, { h: '조치', k: 'action' }
])}
`;
fs.writeFileSync(path.join(OUT, `full_coverage_matrix_${suffix}.md`), matrixMd);

const dupTxt = [
  `Paradiso duplicate audit (${suffix}) — ${new Date().toISOString()}`,
  `mode=${MODE} resolveIdsBeforeKeying=${MODE === 'after'}`,
  `top-level codes scanned: ${topCodes.length}`,
  `duplicate families found: ${dupFindings.length} across ${dupCodes.length} codes`,
  '',
  ...dupFindings.map(d => [
    `[${d.code}] ${d.context} :: family=${d.key} :: classification=${d.classification}`,
    ...d.members.map(m => `    - ${m}`)
  ].join('\n'))
].join('\n');
fs.writeFileSync(path.join(OUT, `duplicate_audit_${suffix}.txt`), dupTxt);

const groupingMd = `# 문서 그룹핑 감사 (${suffix})

원문 매뉴얼은 단일 보편 분류(공통/필수/조건부)를 사용하지 않습니다(제출서류·신청서류·첨부서류·기본서류·추가서류·심사에 필요한 추가서류 등 국지 표제 혼용).
아래 매핑은 **표시 전용 UX 분류**이며 공식 표제가 아닙니다. 데이터의 내부 키는 변경하지 않습니다.

${table(groupingRows, [
  { h: '원본(내부) 버킷', k: 'sourceBucket' }, { h: '성격', k: 'nature' },
  { h: '사용자 표시 그룹', k: 'uxGroup' }, { h: '비고', k: 'note' }
])}

표시 그룹(순서 고정): 기본 준비서류 → 상황별 추가서류 → 심사 중 추가 요청 가능(주의 노트로 표시)
재량 문구 감지 패턴: ${DISCRETIONARY_RE}
`;
fs.writeFileSync(path.join(OUT, `grouping_audit_${suffix}.md`), groupingMd);

if (MODE === 'after') {
  fs.writeFileSync(path.join(OUT, 'duplicate_audit_after.json'), JSON.stringify({
    generated: new Date().toISOString(),
    topLevelCodes: topCodes,
    totals: {
      records: visaData.length,
      documentArrays: matrixRows.filter(r => r.jsonPath !== '-').length,
      labels: totalLabels,
      duplicateFamilies: dupFindings.length,
      unresolved: unresolved.length
    },
    findings: dupFindings
  }, null, 2));
  const md = `# 중복 감사 (after)

- 렌더 가드 적용 시뮬레이션 후 남은 패밀리: **${dupFindings.length}**
- 미해결(UNRESOLVED): **${unresolved.length}**
${dupFindings.length ? dupFindings.map(d => `\n## [${d.code}] ${d.context}\n- family: \`${d.key}\`\n- classification: ${d.classification}\n${d.members.map(m => `- ${m}`).join('\n')}`).join('\n') : '\n남은 사용자 노출 중복 없음.'}
`;
  fs.writeFileSync(path.join(OUT, 'duplicate_audit_after.md'), md);
}

console.log(`[audit] mode=${MODE}`);
console.log(`[audit] top-level codes: ${topCodes.length}`);
console.log(`[audit] document arrays discovered: ${matrixRows.filter(r => r.jsonPath !== '-').length}`);
console.log(`[audit] labels scanned: ${totalLabels}`);
console.log(`[audit] duplicate families: ${dupFindings.length} across codes: ${dupCodes.join(', ') || '(none)'}`);
console.log(`[audit] unresolved: ${unresolved.length}`);

if (MODE === 'after' && FAIL_ON_UNRESOLVED && unresolved.length) {
  console.error('[audit] FAIL: unresolved duplicate families remain (not classified DISTINCT_REQUIREMENTS / AMBIGUOUS_TABLE_CONTEXT / OFFICIAL_DUAL_LISTING).');
  process.exit(1);
}
