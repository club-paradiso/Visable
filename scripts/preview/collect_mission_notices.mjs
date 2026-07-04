#!/usr/bin/env node
/**
 * PreView by Paradiso — limited official mission-notice collector.
 *
 * MANUAL / OFFLINE DATA-PREPARATION SCRIPT ONLY.
 * This is never called by preview.html at runtime; it exists so an operator
 * can refresh data/preview/mission-notices.snapshot.json from official
 * Korean mission web pages, under strict guardrails:
 *
 *   - allowed hosts: mofa.go.kr / www.mofa.go.kr / overseas.mofa.go.kr ONLY
 *   - explicit MVP allowlist (Vietnam, Mongolia, Uzbekistan) — no discovery,
 *     no link following, no site crawling
 *   - low request count (hard cap), per-request timeout, polite delay,
 *     honest User-Agent
 *   - text snippets are short, tagged, and never presented as complete
 *     official checklists ("공식 원문 확인 필요")
 *
 * Usage:
 *   node scripts/preview/collect_mission_notices.mjs            # dry-run plan
 *   node scripts/preview/collect_mission_notices.mjs --fetch    # fetch + write
 *
 * If fetching is blocked (as in sandboxed environments), the existing curated
 * snapshot is left untouched and the failure is reported honestly.
 */

import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(HERE, '..', '..');
const SNAPSHOT_PATH = path.join(REPO_ROOT, 'data', 'preview', 'mission-notices.snapshot.json');

const ALLOWED_HOSTS = new Set(['mofa.go.kr', 'www.mofa.go.kr', 'overseas.mofa.go.kr']);
const MAX_REQUESTS = 8;
const TIMEOUT_MS = 10000;
const DELAY_MS = 1500;
const SNIPPET_MAX = 280;
const USER_AGENT =
  'ParadisoPreViewCollector/0.1 (+manual offline data prep; 2026 foreign-affairs public data contest MVP)';

/**
 * MVP allowlist. Every URL below is an official overseas.mofa.go.kr page
 * corroborated via search-index results (base pages and board paths).
 * Boards may be renumbered by missions; failures are reported, not guessed.
 */
const TARGETS = [
  {
    country: '베트남',
    post: '주베트남 대한민국 대사관',
    language: 'ko',
    urls: [{ title: '공관 대표 페이지', url: 'https://overseas.mofa.go.kr/vn-ko/index.do' }],
  },
  {
    country: '베트남',
    post: '주호치민 대한민국 총영사관',
    language: 'ko',
    urls: [
      { title: '공지사항 게시판', url: 'https://overseas.mofa.go.kr/vn-hochiminh-ko/brd/m_4024/list.do' },
      { title: '구비서류 게시판', url: 'https://overseas.mofa.go.kr/vn-hochiminh-ko/brd/m_4020/list.do' },
    ],
  },
  {
    country: '몽골',
    post: '주몽골 대한민국 대사관',
    language: 'ko',
    urls: [{ title: '공관 대표 페이지', url: 'https://overseas.mofa.go.kr/mn-ko/index.do' }],
  },
  {
    country: '우즈베키스탄',
    post: '주우즈베키스탄 대한민국 대사관',
    language: 'ko',
    urls: [
      { title: '사증 안내 게시판', url: 'https://overseas.mofa.go.kr/uz-ko/brd/m_8550/list.do' },
      {
        title: '[주요 안내] 각 비자 신청 종류별 구비서류 안내 (게시글)',
        url: 'https://overseas.mofa.go.kr/uz-ko/brd/m_8550/view.do?seq=1281058',
      },
    ],
  },
];

function assertAllowedUrl(rawUrl) {
  const parsed = new URL(rawUrl);
  if (parsed.protocol !== 'https:') {
    throw new Error(`blocked non-https url: ${rawUrl}`);
  }
  if (!ALLOWED_HOSTS.has(parsed.hostname)) {
    throw new Error(`blocked host outside allowlist: ${parsed.hostname}`);
  }
  return parsed;
}

function stripTags(html) {
  return html
    .replace(/<script[\s\S]*?<\/script>/gi, ' ')
    .replace(/<style[\s\S]*?<\/style>/gi, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/\s+/g, ' ')
    .trim();
}

async function fetchOne(url) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const response = await fetch(url, {
      signal: controller.signal,
      redirect: 'error', // never follow anywhere, not even same-host redirects
      headers: { 'User-Agent': USER_AGENT, Accept: 'text/html' },
    });
    if (!response.ok) return { ok: false, error: `http_${response.status}` };
    const body = await response.text();
    return { ok: true, body: body.slice(0, 500000) };
  } catch (error) {
    return { ok: false, error: error.name === 'AbortError' ? 'timeout' : `fetch_failed_${error.name || 'Error'}` };
  } finally {
    clearTimeout(timer);
  }
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function main() {
  const doFetch = process.argv.includes('--fetch');
  const today = new Date().toISOString().slice(0, 10);

  const plan = TARGETS.flatMap((target) =>
    target.urls.map((entry) => ({ ...entry, country: target.country, post: target.post, language: target.language })),
  ).slice(0, MAX_REQUESTS);

  // Validate the entire allowlist up front — refuse to run with a bad URL.
  for (const entry of plan) assertAllowedUrl(entry.url);

  if (!doFetch) {
    console.log('[collect_mission_notices] DRY RUN — no network requests made. Plan:');
    for (const entry of plan) console.log(`  - [${entry.country}/${entry.post}] ${entry.title} -> ${entry.url}`);
    console.log(`[collect_mission_notices] ${plan.length} request(s) planned (cap ${MAX_REQUESTS}). Use --fetch to collect.`);
    return;
  }

  const items = [];
  let successes = 0;
  for (const entry of plan) {
    const result = await fetchOne(entry.url);
    if (result.ok) {
      successes += 1;
      const text = stripTags(result.body);
      const titleMatch = /<title[^>]*>([\s\S]*?)<\/title>/i.exec(result.body);
      items.push({
        country: entry.country,
        post: entry.post,
        title: titleMatch ? stripTags(titleMatch[1]).slice(0, 160) : entry.title,
        url: entry.url,
        fetchedAt: today,
        language: entry.language,
        textSnippet:
          (text.slice(0, SNIPPET_MAX) || '') +
          ' … (일부 발췌 — 완전한 공식 체크리스트가 아님, 공식 원문 확인 필요)',
        sourceType: 'overseas_mofa_public_web',
        evidenceLevel: 'official_public_web',
        extractionStatus: 'partial_snippet_extracted',
      });
    } else {
      items.push({
        country: entry.country,
        post: entry.post,
        title: entry.title,
        url: entry.url,
        fetchedAt: null,
        language: entry.language,
        textSnippet: '공식 원문 확인 필요 — 이 실행에서 본문을 수집하지 못했습니다.',
        sourceType: 'overseas_mofa_public_web',
        evidenceLevel: 'official_public_web',
        extractionStatus: `fetch_blocked_${result.error}`,
      });
    }
    await sleep(DELAY_MS);
  }

  if (successes === 0) {
    console.error('[collect_mission_notices] all fetches failed — leaving the existing curated snapshot untouched.');
    if (existsSync(SNAPSHOT_PATH)) {
      const existing = JSON.parse(readFileSync(SNAPSHOT_PATH, 'utf8'));
      console.error(`[collect_mission_notices] existing snapshot kept: ${existing.items?.length ?? 0} item(s).`);
    }
    process.exitCode = 1;
    return;
  }

  const snapshot = {
    schemaVersion: 1,
    generatedAt: today,
    generatedBy: 'scripts/preview/collect_mission_notices.mjs',
    collectionPolicyKo:
      '허용 호스트(mofa.go.kr, overseas.mofa.go.kr)의 명시된 공개 게시판·안내 페이지만 저요청으로 수집. ' +
      '사이트 전체 크롤링·외부 링크 추적 금지. 발췌는 완전한 공식 체크리스트가 아니며 공식 원문 확인 필요.',
    items,
  };
  writeFileSync(SNAPSHOT_PATH, JSON.stringify(snapshot, null, 2) + '\n', 'utf8');
  console.log(`[collect_mission_notices] wrote ${items.length} item(s) (${successes} fetched) -> ${SNAPSHOT_PATH}`);
}

main().catch((error) => {
  console.error(`[collect_mission_notices] fatal: ${error.message}`);
  process.exitCode = 1;
});
