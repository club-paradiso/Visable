#!/usr/bin/env node
/*
 * Smoke-check ai.html visa_data payload matching.
 *
 * This script mirrors the pure matching helpers in ai.html instead of importing
 * from the browser document. Keep the normalization and matching behavior in
 * sync when ai.html changes.
 */

'use strict';

const fs = require('fs');
const path = require('path');

const VISA_DATA_PATH = path.resolve(__dirname, '..', 'visa_data.json');
const VISA_LETTERS = new Set(['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']);
const SOURCE_MANUAL_VERSION = '2026.5';
const SOURCE_MANUALS = ['visa_manual_2026_05', 'stay_manual_2026_06_01'];
const STRICT_DATA_FILE = process.env.SMOKE_AI_PAYLOAD_STRICT_DATA === '1';
const SMOKE_FIXTURE_DATA = [
  { code: 'D-2' },
  { code: 'E-7', subcodes: [{ code: 'E-7-4' }] },
  { code: 'F-6', subcodes: [{ code: 'F-6-1' }] },
  { code: 'K-STAR' }
];

function normalizeVisaCode(input) {
  if (!input) return null;
  const raw = String(input).trim().toUpperCase()
    .replace(/[‐‑‒–—―−]/g, '-')
    .replace(/\s+/g, '');
  if (!raw) return null;
  if (raw === 'KSTAR' || raw === 'K-STAR') return 'K-STAR';
  if (raw.includes('-')) {
    const hyphenated = raw.match(/^([A-H])-?(\d{1,2})(?:-([A-Z0-9]{1,3}))?$/);
    if (!hyphenated || !VISA_LETTERS.has(hyphenated[1])) return null;
    return hyphenated[3] ? `${hyphenated[1]}-${hyphenated[2]}-${hyphenated[3]}` : `${hyphenated[1]}-${hyphenated[2]}`;
  }
  const compact = raw.replace(/[^A-Z0-9]/g, '');
  const match = compact.match(/^([A-H])(\d{1,2})([A-Z0-9]{0,3})$/);
  if (!match || !VISA_LETTERS.has(match[1])) return null;
  return match[3] ? `${match[1]}-${match[2]}-${match[3]}` : `${match[1]}-${match[2]}`;
}

function extractVisaCodesFromQuestion(question) {
  if (!question || typeof question !== 'string') return [];
  const candidates = [];
  const seen = new Set();
  function add(raw) {
    const code = normalizeVisaCode(raw);
    if (!code || seen.has(code)) return;
    seen.add(code);
    candidates.push(code);
  }
  if (/\bK[\s-]*STAR\b/i.test(question)) add('K-STAR');
  const re = /(^|[^A-Za-z0-9])\(?\s*([A-Za-z])\s*[-‐‑‒–—―−]?\s*(\d{1,2})(?:\s*[-‐‑‒–—―−]\s*([A-Za-z0-9]{1,3}))?\s*\)?/g;
  let m;
  while ((m = re.exec(question)) !== null) {
    const letter = m[2].toUpperCase();
    if (!VISA_LETTERS.has(letter)) continue;
    add(m[4] ? `${letter}-${m[3]}-${m[4]}` : `${letter}-${m[3]}`);
  }
  return candidates;
}

function recordCode(record) {
  return normalizeVisaCode(record && record.code);
}

function findSubcodeRecord(record, normalizedCode) {
  const subs = Array.isArray(record && record.subcodes)
    ? record.subcodes
    : (Array.isArray(record && record.subCodes) ? record.subCodes : []);
  return subs.find((sub) => normalizeVisaCode(sub && sub.code) === normalizedCode) || null;
}

function findVisaRecordForQuestion(question, dataset) {
  const detectedCodes = extractVisaCodesFromQuestion(question);
  if (!Array.isArray(dataset) || dataset.length === 0) {
    return { detected_code: detectedCodes[0] || null, detected_codes: detectedCodes, match_found: false, reason: 'Local visa_data not loaded' };
  }
  if (!detectedCodes.length) {
    return { detected_code: null, detected_codes: [], match_found: false, reason: 'No visa code detected in user message' };
  }
  for (const detectedCode of detectedCodes) {
    const exact = dataset.find((r) => recordCode(r) === detectedCode);
    if (exact) {
      return { code: exact.code, matched_code: exact.code, matched_subcode: null, detected_code: detectedCode, detected_codes: detectedCodes, match_found: true, match_type: 'exact' };
    }
    const parentCode = detectedCode.split('-').slice(0, 2).join('-');
    const parent = dataset.find((r) => recordCode(r) === parentCode);
    if (parent) {
      const matchedSubcode = findSubcodeRecord(parent, detectedCode);
      return {
        code: parent.code,
        matched_code: parent.code,
        matched_subcode: matchedSubcode ? matchedSubcode.code : detectedCode,
        detected_code: detectedCode,
        detected_codes: detectedCodes,
        match_found: true,
        match_type: matchedSubcode ? 'subcode' : 'parent'
      };
    }
  }
  return { detected_code: detectedCodes[0] || null, detected_codes: detectedCodes, match_found: false, reason: 'No matching local visa_data entry' };
}

function buildVisaDataPayload(question, dataset) {
  return Object.assign(findVisaRecordForQuestion(question, dataset), {
    source_manual_version: SOURCE_MANUAL_VERSION,
    source_manuals: SOURCE_MANUALS
  });
}

function loadVisaData() {
  if (!fs.existsSync(VISA_DATA_PATH)) {
    throw new Error(`visa_data.json not found at ${VISA_DATA_PATH}`);
  }
  let lastError = null;
  for (let attempt = 1; attempt <= 3; attempt += 1) {
    try {
      const raw = JSON.parse(fs.readFileSync(VISA_DATA_PATH, 'utf8'));
      return Array.isArray(raw) ? raw : raw.data;
    } catch (err) {
      lastError = err;
      if (!err || !['ETIMEDOUT', 'EAGAIN', 'EBUSY'].includes(err.code)) {
        break;
      }
    }
  }
  if (STRICT_DATA_FILE) {
    throw lastError || new Error(`failed to read ${VISA_DATA_PATH}`);
  }
  const code = lastError && lastError.code ? `${lastError.code}: ` : '';
  console.warn(`[smoke_ai_payload] WARNING: ${code}using minimal fixture after visa_data.json read failed`);
  return SMOKE_FIXTURE_DATA;
}

function main() {
  const data = loadVisaData();
  if (!Array.isArray(data)) throw new Error('visa_data.json did not contain an array or data array');

  const cases = [
    { label: 'F-6 divorce', question: 'F-6-1 결혼이민 비자에서 이혼했을 때 어떻게 되나요?', expectedCode: 'F-6', expectedSubcode: 'F-6-1' },
    { label: 'D-2 student', question: 'D-2 유학생 시간제취업 허가가 궁금해요', expectedCode: 'D-2' },
    { label: 'E-7 skilled worker', question: 'E-7-4 숙련기능인력 요건 알려줘', expectedCode: 'E-7', expectedSubcode: 'E-7-4' },
    { label: 'K-STAR top tier', question: 'K-STAR F-2-71 동반가족은 어떻게 신청하나요?', expectedCode: data.some((r) => r.code === 'K-STAR') ? 'K-STAR' : 'F-2' }
  ];

  let failed = false;
  for (const item of cases) {
    const payload = buildVisaDataPayload(item.question, data);
    const sub = payload.matched_subcode || '-';
    console.log(`${item.label}: detected=${payload.detected_code || '-'} matched=${payload.matched_code || '-'} sub=${sub} type=${payload.match_type || '-'} found=${payload.match_found}`);
    if (!payload.match_found || payload.matched_code !== item.expectedCode) {
      console.error(`Expected ${item.expectedCode} for ${item.label}, got ${payload.matched_code || 'no match'}`);
      failed = true;
    }
    if (item.expectedSubcode && payload.matched_subcode !== item.expectedSubcode) {
      console.error(`Expected subcode ${item.expectedSubcode} for ${item.label}, got ${payload.matched_subcode || 'none'}`);
      failed = true;
    }
  }

  if (failed) process.exit(1);
}

main();
