'use strict';

// Real-time verification transport over the law.go.kr PUBLIC web endpoints
// (no credential). The DRF Open API rejects callers whose server IP/domain
// is not registered for the OC (verified in production 2026-11-05: both the
// Immigration Act and its Enforcement Rule returned
// "upstream_authorization_or_registration_error" from the Vercel egress,
// and OC=test from an unregistered host returns the provider's
// user-verification failure). The public endpoints are the same official
// pages a citizen reads and need no registration:
//
//   /법령/<법령명>                — current-version discovery (MST + efYd)
//   /LSW/lsInfoR.do?lsiSeq=&efYd= — official body HTML for one version
//   /LSW/flDownload.do            — official annex files (별표)
//
// Verification chain for Annex 7 (범칙금의 양정기준): the annex is served
// only as a file, so its text cannot be read from the body page. Instead
// the live Rule body page must list the same flSeq that the preserved
// official corpus snapshot recorded, and the live-downloaded PDF's SHA-256
// must equal the snapshot metadata hash. Only then is the snapshot excerpt
// treated as verified against the current official source.

const crypto = require('node:crypto');

const actVersion20260123 = require('../backend/data/legal-corpus/laws/immigration-act/versions/2026-01-23/metadata.json');
const actVersion20261002 = require('../backend/data/legal-corpus/laws/immigration-act/versions/2026-10-02/metadata.json');
const ruleVersion20260123 = require('../backend/data/legal-corpus/laws/immigration-rule/versions/2026-01-23/metadata.json');
const ruleVersion20261023 = require('../backend/data/legal-corpus/laws/immigration-rule/versions/2026-10-23/metadata.json');
const annex7Metadata = require('../backend/data/legal-corpus/annexes/immigration-rule-annex-7/versions/2026-01-23/metadata.json');
const annex7Data = require('../backend/data/legal-corpus/annexes/immigration-rule-annex-7/versions/2026-01-23/annex7.json');

const BASE_URL = 'https://www.law.go.kr';
const USER_AGENT = 'Visable-Enforcement-Law-Grounding/2';
const DISCOVERY_TIMEOUT_MS = 6500;
const BODY_TIMEOUT_MS = 11500;
const CACHE_TTL_MS = 60 * 60 * 1000;

function versionOf(metadata) {
  return {
    effectiveDate: String(metadata.effectiveFrom || '').replace(/\D/g, ''),
    mst: String(metadata.sourceIdentifier || ''),
  };
}

// Corpus-known versions (MST + effective date), ascending. Used only to
// locate the official version in force on a past violation date; the body
// itself is always fetched live from law.go.kr.
const KNOWN_VERSIONS = {
  '출입국관리법': [versionOf(actVersion20260123), versionOf(actVersion20261002)]
    .filter((v) => v.mst && v.effectiveDate).sort((a, b) => a.effectiveDate.localeCompare(b.effectiveDate)),
  '출입국관리법 시행규칙': [versionOf(ruleVersion20260123), versionOf(ruleVersion20261023)]
    .filter((v) => v.mst && v.effectiveDate).sort((a, b) => a.effectiveDate.localeCompare(b.effectiveDate)),
};

const cache = new Map();
// Only successful results are cached: a transient failure (timeout,
// connection reset by the provider) must never poison later calls in the
// same warm instance.
async function cached(key, producer, isSuccess) {
  const hit = cache.get(key);
  if (hit && Date.now() - hit.at < CACHE_TTL_MS) return hit.value;
  const value = await producer();
  if (isSuccess(value)) cache.set(key, { at: Date.now(), value });
  return value;
}

async function fetchWithTimeout(url, ms, binary = false) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), ms);
  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: { 'User-Agent': USER_AGENT, Accept: binary ? 'application/pdf,*/*' : 'text/html' },
      signal: controller.signal,
    });
    if (!response.ok) return { ok: false, status: `http_${response.status}` };
    return binary
      ? { ok: true, buffer: Buffer.from(await response.arrayBuffer()) }
      : { ok: true, text: await response.text() };
  } catch (error) {
    return { ok: false, status: error && error.name === 'AbortError' ? 'timeout' : 'network_error' };
  } finally {
    clearTimeout(timer);
  }
}

async function discoverCurrent(lawName) {
  return cached(`discover:${lawName}`, async () => {
    const result = await fetchWithTimeout(`${BASE_URL}/법령/${lawName}`, DISCOVERY_TIMEOUT_MS);
    if (!result.ok) return { ok: false, status: result.status };
    const match = result.text.match(/lsInfoP\.do\?lsiSeq=(\d+)&[^"']*efYd=(\d{8})/);
    if (!match) return { ok: false, status: 'public_discovery_failed' };
    return { ok: true, mst: match[1], effectiveDate: match[2] };
  }, (value) => value.ok);
}

function decodeEntities(text) {
  return text
    .replace(/&nbsp;/g, ' ')
    .replace(/&middot;/g, '·')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;|&apos;/g, "'")
    .replace(/&amp;/g, '&');
}

function stripTags(html) {
  return decodeEntities(String(html || '').replace(/<[^>]*>/g, ' ')).replace(/\s+/g, ' ').trim();
}

const ARTICLE_LABEL = /^제(\d+)조(?:의(\d+))?\s*(?:\(([^)]*)\))?/;

// Port of the corpus parser's article extraction (lsInfoR body pages):
// an article starts at a <p> carrying a joNoList input or a label matching
// 제N조; following paragraphs belong to it. The annex region (별표 서식)
// is excluded.
function parseArticles(html) {
  const cut = html.indexOf('별표 서식 시작');
  const body = cut >= 0 ? html.slice(0, cut) : html;
  const articles = new Map();
  let current = null;
  const paragraphRe = /<p\b[^>]*>([\s\S]*?)<\/p>/g;
  let match;
  while ((match = paragraphRe.exec(body)) !== null) {
    const block = match[1];
    const labelMatch = block.match(/<label[^>]*>([\s\S]*?)<\/label>/);
    const labelText = labelMatch ? stripTags(labelMatch[1]) : '';
    const text = stripTags(block);
    const label = ARTICLE_LABEL.exec(labelText) || ARTICLE_LABEL.exec(text);
    const hasJoInput = /name="joNoList"/.test(block);
    if (label && (hasJoInput || labelText)) {
      const number = String(Number(label[1]));
      const branch = label[2] ? Number(label[2]) : 0;
      current = { number, branch, parts: [] };
      const rest = text.slice(label[0].length).trim();
      if (rest) current.parts.push(rest);
      if (!branch && !articles.has(number)) articles.set(number, current);
      else if (branch) current = null; // branch articles (제N조의M) are not excerpt targets
      continue;
    }
    if (current && text) current.parts.push(text);
  }
  const out = new Map();
  for (const [number, article] of articles) {
    const excerpt = article.parts.join(' ').replace(/\s+/g, ' ').trim();
    if (excerpt) out.set(number, excerpt);
  }
  return out;
}

// Port of the corpus parser's annex-list extraction: within the 별표 서식
// region, each bylInfoDiv block carries a [별표 N] title and flDownload
// file sequences.
function parseAnnexFiles(html, annexNo) {
  const start = html.indexOf('별표 서식 시작');
  const end = html.indexOf('별표 서식 끝');
  if (start < 0 || end <= start) return [];
  const segment = html.slice(start, end);
  const blocks = segment.split(/bylInfoDiv\('(\d+)'\)/);
  for (let i = 1; i < blocks.length - 1; i += 2) {
    const block = blocks[i + 1];
    const titleMatch = block.match(/\[(별표\s*[^\]]+|별지\s*[^\]]+)\]\s*([^<"]*)/);
    if (!titleMatch) continue;
    const title = `[${titleMatch[1].replace(/\s+/g, ' ')}] ${titleMatch[2]}`.trim();
    const normalized = title.replace(/\s+/g, '');
    if (!normalized.startsWith(`[별표${annexNo}]`)) continue;
    const files = [];
    const seen = new Set();
    const fileRe = /flDownload\.do\?gubun=&(?:amp;)?(?:flExt=(?:hwp|hwpx|pdf)&(?:amp;)?)?flSeq=(\d+)&(?:amp;)?bylClsCd=(\d+)/g;
    let fm;
    while ((fm = fileRe.exec(block)) !== null) {
      if (seen.has(fm[1])) continue;
      seen.add(fm[1]);
      files.push({ flSeq: fm[1], bylClsCd: fm[2] });
    }
    return files;
  }
  return [];
}

function annexExcerpt() {
  const text = `[별표 7] ${annex7Data.titleKo || '범칙금의 양정기준'} ${annex7Data.generalCriteriaKo || ''}`;
  return text.replace(/\s+/g, ' ').trim().slice(0, 850);
}

async function verifyAnnex7(liveFiles) {
  const pdfEntry = (annex7Metadata.files || []).find((f) => f.detectedFormat === 'pdf');
  if (!pdfEntry) return { verified: false, status: 'annex_snapshot_missing' };
  if (!liveFiles.some((f) => f.flSeq === pdfEntry.flSeq)) {
    return { verified: false, status: 'annex_file_sequence_changed' };
  }
  return cached(`annex7:${pdfEntry.flSeq}`, async () => {
    const url = `${BASE_URL}/LSW/flDownload.do?gubun=&flSeq=${pdfEntry.flSeq}&bylClsCd=${pdfEntry.bylClsCd}`;
    const result = await fetchWithTimeout(url, BODY_TIMEOUT_MS, true);
    if (!result.ok) return { verified: false, status: result.status };
    const digest = crypto.createHash('sha256').update(result.buffer).digest('hex');
    if (digest !== pdfEntry.sha256) return { verified: false, status: 'annex_hash_mismatch' };
    return { verified: true, excerpt: annexExcerpt() };
  }, (value) => value.verified);
}

function compactDay(value) {
  const raw = String(value || '').replace(/\D/g, '');
  return /^\d{8}$/.test(raw) ? raw : '';
}

async function fetchPublicLaw(lawName, caseData = {}) {
  const current = await discoverCurrent(lawName);
  if (!current.ok) return { ok: false, status: current.status };

  const start = compactDay(caseData.violationStartDate);
  const end = compactDay(caseData.violationEndDate);
  const dated = Boolean(start && end && start <= end);
  const known = KNOWN_VERSIONS[lawName] || [];

  let chosen;
  let crossesVersion = false;
  if (!dated || current.effectiveDate <= start) {
    chosen = { mst: current.mst, effectiveDate: current.effectiveDate };
  } else {
    const eligible = known.filter((v) => v.effectiveDate <= start);
    if (!eligible.length) return { ok: false, status: 'historical_version_unavailable' };
    chosen = eligible[eligible.length - 1];
    crossesVersion = known.some((v) => v.effectiveDate > start && v.effectiveDate <= end)
      || (current.effectiveDate > start && current.effectiveDate <= end);
  }

  const bodyResult = await cached(`body:${chosen.mst}:${chosen.effectiveDate}`, async () => {
    const url = `${BASE_URL}/LSW/lsInfoR.do?lsiSeq=${chosen.mst}&efYd=${chosen.effectiveDate}&ancYnChk=0`;
    return fetchWithTimeout(url, BODY_TIMEOUT_MS);
  }, (value) => value.ok);
  if (!bodyResult.ok) return { ok: false, status: bodyResult.status };

  const articles = parseArticles(bodyResult.text);
  if (!articles.size) return { ok: false, status: 'public_parse_failed' };

  let annex = null;
  if (lawName === '출입국관리법 시행규칙') {
    const files = parseAnnexFiles(bodyResult.text, '7');
    annex = files.length
      ? await verifyAnnex7(files)
      : { verified: false, status: 'annex_not_listed' };
  }

  return {
    ok: true,
    transport: 'public',
    candidate: { mst: chosen.mst, id: '', name: lawName, effectiveDate: chosen.effectiveDate },
    articles,
    annex,
    crossesVersion,
    historical: dated,
  };
}

module.exports = {
  fetchPublicLaw,
  parseArticles,
  parseAnnexFiles,
  annexExcerpt,
  KNOWN_VERSIONS,
};
