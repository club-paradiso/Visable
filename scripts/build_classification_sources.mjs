#!/usr/bin/env node
/*
 * build_classification_sources.mjs
 * ----------------------------------------------------------------------------
 * Ingestion / update script for the employment-reporting classification source
 * metadata. It does NOT touch the canonical codes — it reads the existing
 * canonical dataset (data/jobcode_master.json), derives consolidated source
 * metadata, computes a content checksum, and writes:
 *
 *     data/employment/classification_sources.json
 *
 * This satisfies the source-of-truth metadata requirement (source_name,
 * source_reference, fetched_at, classification_name, revision/version,
 * checksum/hash) without duplicating or mutating the official code table.
 *
 * Run:  node scripts/build_classification_sources.mjs
 * ----------------------------------------------------------------------------
 */
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const masterPath = join(root, 'data', 'jobcode_master.json');
const outDir = join(root, 'data', 'employment');
const outPath = join(outDir, 'classification_sources.json');

const raw = readFileSync(masterPath, 'utf8');
const master = JSON.parse(raw);
const checksum = 'sha256:' + createHash('sha256').update(raw).digest('hex');
const fetchedAt = new Date().toISOString().slice(0, 10);

const occ = master.occupation_source || {};
const ind = master.industry_source || {};
const ctx = master.employment_reporting_context || {};

function buildBlock(meta, classificationName) {
  return {
    classification_name: meta.classification || classificationName,
    short_name: meta.short_name || null,
    version: meta.short_name || null,
    revision: meta.announcement || null,
    announcement_date: meta.announcement_date || null,
    effective_date: meta.effective_date || null,
    source_name: meta.issuing_body || '통계청 / 국가데이터처',
    source_reference: meta.portal || '국가데이터처 통계분류포털 (kssc.mods.go.kr)',
    source_url: ctx.classification_portal_url || 'https://kssc.mods.go.kr',
    runtime_count: meta.runtime_count || null,
    full_table_loaded: meta.full_table_loaded === true,
    fetched_at: fetchedAt
  };
}

const out = {
  schema_version: '2026-06-employment-analyzer-classification-sources',
  generated_by: 'scripts/build_classification_sources.mjs',
  generated_at: fetchedAt,
  note: 'Consolidated source metadata for the HiKorea employment-reporting code analyzer. Canonical codes live in data/jobcode_master.json; this file only records provenance + checksum. It does not contain or alter any codes.',
  canonical_dataset: {
    path: 'data/jobcode_master.json',
    schema_version: master.schema_version || null,
    total_count: master.total_count || (Array.isArray(master.data) ? master.data.length : null),
    categories: master.categories || null,
    checksum: checksum,
    fetched_at: fetchedAt
  },
  occupation: buildBlock(occ, '제8차 한국표준직업분류'),
  industry: buildBlock(ind, '제11차 한국표준산업분류'),
  reporting_context: {
    reported_fields: ctx.reported_fields || ['직종', '업종', '연간소득'],
    legal_basis: ctx.legal_basis || null,
    list_source_note: ctx.list_source_note || null,
    classification_portal_url: ctx.classification_portal_url || 'https://kssc.mods.go.kr',
    final_confirmation: ctx.final_confirmation || null
  },
  legal_sources: [
    {
      source_name: '문신사법(타투업법)',
      applies_to: ['tattoo'],
      status: '국회 본회의 통과(2025-09-25), 시행 전',
      effective_date: '2027-10-29',
      verified: true,
      source_reference: '보건복지부 보도자료 / 국회 본회의 의결(2025-09-25). 문신·반영구화장을 ‘문신 행위’로 규정, 국가자격(면허) 필요. 2년 경과 후 시행.',
      source_url: 'https://www.law.go.kr',
      notes: '문신/타투 관련 활동은 시행일·면허요건·체류자격·고용형태·실제 시술 여부에 따라 별도 검토 필요. 본 메타데이터는 보도자료 기반이며 최종 확인은 국가법령정보센터(law.go.kr)에서 해야 한다. 코드가 있다고 해서 활동이 허용되는 것은 아니다.'
    },
    {
      source_name: '출입국관리법 시행규칙 제47조·제49조의2 (외국인 취업정보 신고)',
      applies_to: ['entertainment', 'tattoo'],
      status: '시행 중',
      effective_date: null,
      verified: true,
      source_reference: '법무부 「외국인 취업정보 온라인 신고제」 확대 시행(2026-01-02). 직종·업종은 국가데이터처 표준직업/표준산업분류 참고.',
      source_url: 'https://www.hikorea.go.kr',
      notes: '취업정보 신고는 직종·업종·연간소득 신고이며, 활동의 적법성(자격외활동 허가 등)을 판단하지 않는다.'
    }
  ],
  adapter_note: 'HiKorea 신고 화면의 직종/업종 드롭다운이 공개 표준분류표와 다를 경우, 캐논 데이터를 임의로 바꾸지 말고 이 메타데이터에 mismatch 를 기록하고 어댑터 계층(런타임 매핑)으로 처리한다.',
  known_mismatches: [
    {
      area: 'occupation',
      issue: 'KSCO8 세세분류(5단계) 전체표 미적용 — 런타임은 대/중/소/세분류(728행)만 보유',
      handling: '세부코드 확정은 HiKorea 직종조회/통계분류포털에서 확인하도록 경고 표시(어댑터: warning)'
    },
    {
      area: 'occupation_and_industry',
      issue: '‘문신/타투’ 전용 직종·업종 항목이 표준분류에 없음(법적 민감 직군)',
      handling: '미용·개인서비스 등 넓은 분류로 간접 매칭하되 confidence_cap=low + 문신사법 법적 주의 표시. 캐논 데이터에 가짜 코드를 추가하지 않음.'
    },
    {
      area: 'occupation',
      issue: '‘아이돌’ 등 복합 연예 활동에 대응하는 단일 표준직업 항목 없음',
      handling: '가수/무용가/배우/방송 등 실제 활동으로 분해(ambiguous_inputs.json)하여 후보 제시. 단일 코드로 단정하지 않음.'
    }
  ]
};

mkdirSync(outDir, { recursive: true });
writeFileSync(outPath, JSON.stringify(out, null, 2) + '\n', 'utf8');
console.log(`wrote ${outPath}`);
console.log(`  canonical checksum: ${checksum}`);
console.log(`  occupation: ${out.occupation.classification_name} (${out.occupation.runtime_count} rows)`);
console.log(`  industry:   ${out.industry.classification_name} (${out.industry.runtime_count} rows)`);
