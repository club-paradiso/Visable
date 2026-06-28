#!/usr/bin/env node
/**
 * import_naturalization_video_metadata.mjs
 *
 * OPTIONAL enrichment for data/naturalization_video_sources.json. When a YouTube
 * Data API key is present (env YOUTUBE_API_KEY or GOOGLE_API_KEY), this fills in
 * real playlist/channel titles via OFFICIAL metadata endpoints only. Without a
 * key it is a clean no-op and the human-written seed is kept.
 *
 * HARD SAFETY GUARANTEES (enforced in code below):
 *   - Only the metadata endpoints playlists/playlistItems/channels/videos are
 *     ever called. The captions endpoint (and any transcript/caption text) is
 *     NEVER requested, downloaded, or stored.
 *   - transcript_stored stays false; is_official stays false; permission_status
 *     is preserved. No transcript-like field is ever written.
 *
 * Usage:
 *   node scripts/import_naturalization_video_metadata.mjs            # dry-run (prints changes)
 *   node scripts/import_naturalization_video_metadata.mjs --write    # write enriched titles back
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const DATA = path.join(ROOT, 'data', 'naturalization_video_sources.json');
const WRITE = process.argv.includes('--write');
const API_KEY = process.env.YOUTUBE_API_KEY || process.env.GOOGLE_API_KEY || '';

// Allowlisted official metadata endpoints. "captions" is intentionally absent.
const ALLOWED = new Set(['playlists', 'playlistItems', 'channels', 'videos']);
const FORBIDDEN_RESOURCE = /captions|transcript|caption/i;

async function ytGet(resource, params) {
  if (!ALLOWED.has(resource) || FORBIDDEN_RESOURCE.test(resource)) {
    throw new Error(`refusing to call non-metadata endpoint: ${resource}`);
  }
  const url = new URL(`https://www.googleapis.com/youtube/v3/${resource}`);
  Object.entries({ ...params, key: API_KEY }).forEach(([k, v]) => url.searchParams.set(k, v));
  const r = await fetch(url, { headers: { Accept: 'application/json' } });
  if (!r.ok) throw new Error(`${resource} HTTP ${r.status}`);
  return r.json();
}

const playlistId = (u) => { try { return new URL(u).searchParams.get('list'); } catch { return null; } };
const channelHandle = (u) => {
  try { const m = new URL(u).pathname.match(/@([^/]+)/); return m ? '@' + m[1] : null; } catch { return null; }
};

async function enrich(rec) {
  if (rec.source_kind === 'playlist') {
    const id = playlistId(rec.url);
    if (!id) return null;
    const d = await ytGet('playlists', { part: 'snippet', id, maxResults: '1' });
    const sn = d.items && d.items[0] && d.items[0].snippet;
    if (!sn) return null;
    return { title: sn.title || rec.title, channel: sn.channelTitle || rec.channel };
  }
  if (rec.source_kind === 'channel') {
    const handle = channelHandle(rec.url);
    if (!handle) return null;
    const d = await ytGet('channels', { part: 'snippet', forHandle: handle, maxResults: '1' });
    const sn = d.items && d.items[0] && d.items[0].snippet;
    if (!sn) return null;
    return { title: sn.title || rec.title, channel: sn.customUrl ? '@' + sn.customUrl.replace(/^@/, '') : rec.channel };
  }
  if (rec.source_kind === 'video') {
    const id = (() => { try { return new URL(rec.url).searchParams.get('v') || new URL(rec.url).pathname.split('/').pop(); } catch { return null; } })();
    if (!id) return null;
    const d = await ytGet('videos', { part: 'snippet', id, maxResults: '1' });
    const sn = d.items && d.items[0] && d.items[0].snippet;
    if (!sn) return null;
    return { title: sn.title || rec.title, channel: sn.channelTitle || rec.channel };
  }
  return null;
}

// Whitelist of fields this importer is allowed to write — guarantees no
// transcript-like field can ever be introduced by enrichment.
const WRITABLE = new Set(['title', 'channel']);

async function main() {
  const doc = JSON.parse(fs.readFileSync(DATA, 'utf8'));
  const videos = doc.videos || [];
  if (!API_KEY) {
    console.log('[import] No YOUTUBE_API_KEY / GOOGLE_API_KEY set — no-op.');
    console.log(`[import] Seed kept as-is (${videos.length} records, metadata-only, transcript_stored=false).`);
    console.log('[import] To enrich titles: set YOUTUBE_API_KEY and run with --write.');
    return;
  }
  let changed = 0;
  for (const rec of videos) {
    let meta = null;
    try { meta = await enrich(rec); } catch (e) { console.warn(`[import] ${rec.id}: ${e.message}`); continue; }
    if (!meta) { console.log(`[import] ${rec.id}: no metadata returned, keeping seed`); continue; }
    for (const [k, v] of Object.entries(meta)) {
      if (!WRITABLE.has(k)) continue; // safety: never write non-whitelisted fields
      if (v && v !== rec[k]) { console.log(`[import] ${rec.id}.${k}: "${rec[k]}" -> "${v}"`); rec[k] = v; changed++; }
    }
    // Invariants are never relaxed by enrichment.
    rec.transcript_stored = false;
    rec.is_official = false;
  }
  if (WRITE && changed) {
    fs.writeFileSync(DATA, JSON.stringify(doc, null, 2) + '\n');
    console.log(`[import] Wrote ${changed} field update(s) to ${path.relative(ROOT, DATA)}.`);
  } else {
    console.log(`[import] ${changed} change(s) ${WRITE ? 'written' : 'detected (dry-run; pass --write to apply)'}.`);
  }
}

main().catch((e) => { console.error('[import] failed:', e.message); process.exit(1); });
