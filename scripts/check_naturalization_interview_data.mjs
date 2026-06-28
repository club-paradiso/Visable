#!/usr/bin/env node
/**
 * check_naturalization_interview_data.mjs
 *
 * Offline, stdlib/Node-only validator for the 귀화면접 학습실 datasets:
 *   - data/naturalization_interview_questions.json
 *   - data/naturalization_video_sources.json
 *   - data/naturalization_learning_topics.json
 *
 * Enforces the practice-question + YouTube-safety contract (no transcripts, no
 * fabricated official status). Exits non-zero on any failure.
 * Run: node scripts/check_naturalization_interview_data.mjs
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const readJson = (rel) => JSON.parse(fs.readFileSync(path.join(ROOT, rel), 'utf8'));

const failures = [];
let passes = 0;
const check = (label, condition, detail = '') => {
  if (condition) passes++;
  else failures.push(`${label}${detail ? `: ${detail}` : ''}`);
};

const questionsDoc = readJson('data/naturalization_interview_questions.json');
const videosDoc = readJson('data/naturalization_video_sources.json');
const topicsDoc = readJson('data/naturalization_learning_topics.json');
const sourcesDoc = readJson('data/nationality_service_sources.json');
const sourceIds = new Set((sourcesDoc.sources || []).map((s) => s.id));
const sourceById = new Map((sourcesDoc.sources || []).map((s) => [s.id, s]));

const CATEGORIES = new Set([
  'korean_language', 'reason_for_naturalization', 'life_in_korea', 'korean_society',
  'democratic_order', 'rights_and_duties', 'interview_attitude', 'pre_evaluation_study'
]);
const DIFFICULTIES = new Set(['easy', 'medium', 'hard']);
const SOURCE_TYPES = new Set([
  'official_law', 'official_notice', 'official_kiip', 'official_socinet',
  'practice', 'video_reference_topic', 'internal_guidance'
]);
const PERMISSION_STATUSES = new Set(['metadata_only', 'creator_permission_required', 'permission_granted']);
const VIDEO_KINDS = new Set(['playlist', 'channel', 'video']);

// Forbidden transcript-like field names anywhere in a video record.
const FORBIDDEN_VIDEO_FIELDS = ['transcript', 'captions', 'caption', 'full_text', 'fulltext', 'script', 'body_text', 'bodytext', 'subtitles', 'srt', 'vtt', 'lesson_text'];
// Any video text field longer than this looks like stored transcript/lesson text.
const VIDEO_TEXT_CEILING = 400;

/* ------------------------------------------------------------- questions */
const questions = Array.isArray(questionsDoc.questions) ? questionsDoc.questions : [];
check('question bank is a non-empty array', questions.length > 0);
check('question bank has at least 50 questions', questions.length >= 50, `${questions.length}`);

const QUESTION_REQUIRED = [
  'id', 'category', 'difficulty', 'question_ko', 'answer_guidance_ko',
  'good_answer_structure_ko', 'bad_answer_patterns', 'source_type',
  'source_refs', 'is_official_past_question', 'labels'
];
const seenIds = new Set();
for (const q of questions) {
  const label = q.id || '(missing id)';
  for (const field of QUESTION_REQUIRED) {
    const v = q[field];
    const empty = v == null || v === '' ||
      (Array.isArray(v) && v.length === 0 && !['source_refs'].includes(field));
    if (field === 'is_official_past_question') {
      // #6 must be boolean.
      check(`${label}.is_official_past_question is boolean`, typeof v === 'boolean');
    } else if (field === 'source_refs') {
      check(`${label} has source_refs array`, Array.isArray(v));
    } else if (Array.isArray(v)) {
      check(`${label} has non-empty "${field}"`, v.length > 0);
    } else {
      check(`${label} has required field "${field}"`, !empty);
    }
  }
  // #2 duplicate ids.
  check(`${label}.id is unique`, !seenIds.has(q.id), q.id);
  seenIds.add(q.id);
  // #3/#4/#5 enums.
  check(`${label}.category is valid`, CATEGORIES.has(q.category), q.category);
  check(`${label}.difficulty is valid`, DIFFICULTIES.has(q.difficulty), q.difficulty);
  check(`${label}.source_type is valid`, SOURCE_TYPES.has(q.source_type), q.source_type);

  // source_refs must resolve when present.
  for (const ref of q.source_refs || []) {
    check(`${label}.source_refs resolves: ${ref}`, sourceIds.has(ref));
  }

  // #10 a question may only claim official past-question status with a verified
  // official source reference (a primary-level official source in source_refs).
  if (q.is_official_past_question === true) {
    const refs = q.source_refs || [];
    const hasVerifiedOfficial = refs.some((r) => sourceById.get(r)?.official_level === 'primary');
    check(`${label} official-past-question claim has a verified official source`, hasVerifiedOfficial);
  } else {
    // Defensive: practice items should carry an explicit non-official label.
    const labels = (q.labels || []).join(' ');
    check(`${label} practice question carries a non-official label`,
      /공식\s*기출\s*아님|연습문제|학습|공식\s*기준\s*참고/.test(labels));
  }
}

/* ---------------------------------------------------------------- videos */
const videos = Array.isArray(videosDoc.videos) ? videosDoc.videos : [];
check('video registry is a non-empty array', videos.length > 0);

const VIDEO_REQUIRED = ['id', 'source_kind', 'title', 'url', 'language', 'notes_ko', 'derived_topics', 'transcript_stored', 'permission_status', 'is_official'];
for (const v of videos) {
  const label = v.id || '(missing id)';
  for (const field of VIDEO_REQUIRED) {
    if (field === 'transcript_stored' || field === 'is_official') continue; // booleans checked below
    const val = v[field];
    const empty = val == null || val === '' || (Array.isArray(val) && val.length === 0);
    // channel may be empty for playlists; title is required.
    check(`${label} has required field "${field}"`, !empty);
  }
  check(`${label}.source_kind is valid`, VIDEO_KINDS.has(v.source_kind), v.source_kind);
  // #12 permission_status enum.
  check(`${label}.permission_status is valid`, PERMISSION_STATUSES.has(v.permission_status), v.permission_status);
  // #11 transcript_stored must be exactly false.
  check(`${label}.transcript_stored is exactly false`, v.transcript_stored === false, String(v.transcript_stored));

  // #7 no transcript-like fields may exist on the record. (transcript_stored is
  // the explicit safety flag and is allowlisted.)
  for (const key of Object.keys(v)) {
    const lk = key.toLowerCase();
    if (lk === 'transcript_stored') continue;
    check(`${label} has no transcript-like field "${key}"`,
      !FORBIDDEN_VIDEO_FIELDS.some((bad) => lk === bad || lk.includes(bad)));
  }
  // #8 no suspiciously long transcript-like text in any string field.
  for (const [key, val] of Object.entries(v)) {
    if (typeof val === 'string') {
      check(`${label}.${key} is not transcript-length text`, val.length <= VIDEO_TEXT_CEILING, `${val.length} chars`);
    }
  }
  // #9 a YouTube-derived record may not claim official status without an explicit official marker.
  if (v.is_official === true) {
    check(`${label} is_official=true requires an explicit official_source_id marker`,
      typeof v.official_source_id === 'string' && sourceIds.has(v.official_source_id));
  } else {
    check(`${label}.is_official is boolean false`, v.is_official === false);
  }
}

/* ---------------------------------------------------------- learning topics */
const topics = Array.isArray(topicsDoc.topics) ? topicsDoc.topics : [];
check('learning topics is a non-empty array', topics.length > 0);
for (const t of topics) {
  const label = t.id || '(missing id)';
  check(`${label} has id/category/title_ko/summary_ko`, !!(t.id && t.category && t.title_ko && t.summary_ko));
  check(`${label}.category is valid`, CATEGORIES.has(t.category), t.category);
  for (const ref of t.related_sources || []) {
    check(`${label}.related_sources resolves: ${ref}`, sourceIds.has(ref));
  }
}

/* --------------------------------------------------------------- summary */
if (failures.length) {
  console.error(`Naturalization-interview data validation FAILED (${failures.length} issue(s)):`);
  for (const f of failures) console.error(`  ✗ ${f}`);
  process.exit(1);
}
console.log(`Naturalization-interview data validation passed: ${passes} checks, ${questions.length} questions, ${videos.length} video sources, ${topics.length} topics.`);
process.exit(0);
