#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";
import process from "node:process";

const DATA_FILES = [
  "visa_data.json",
  "doc_master.json",
  "backend/data/visas.json",
  "backend/data/doc_master.json"
];

const VALID_SOURCE_STATUSES = new Set([
  "source_confirmed",
  "source_partial",
  "source_contextual",
  "official_unavailable",
  "needs_manual_review"
]);

const UNRESOLVED_SOURCE_STATUSES = new Set([
  "official_unavailable",
  "needs_manual_review"
]);

const CLAIM_KEYS = new Set([
  "newReq",
  "newReqDocs",
  "extReq",
  "extReqDocs",
  "initialReqDocs",
  "extensionReqDocs",
  "changeReqDocs",
  "documents_initial",
  "documents_registration",
  "documents_extension",
  "requiredDocs",
  "feeInfo",
  "fee",
  "fees",
  "period",
  "deadline",
  "deadlines",
  "procedure",
  "procedures",
  "eligibility",
  "office",
  "jurisdiction",
  "reservation",
  "faq",
  "subCodes",
  "overstay"
]);

const LOCATOR_FIELDS = [
  "sourceLocator",
  "sourceUrl",
  "sourcePage",
  "sourceSection",
  "manualPage",
  "manualPageRange",
  "pageRange",
  "lawArticle",
  "noticeId",
  "formId"
];

const EVIDENCE_CONTAINERS = [
  "sourceEvidence",
  "officialSourceEvidence",
  "source",
  "sourceMeta",
  "sourceMetadata",
  "sourceManualStatus",
  "citation"
];

const REQUIRED_VERIFIED_EVIDENCE = [
  "sourceStatus",
  "sourceType",
  "sourceName",
  "sourceVersionDate",
  "supportLevel",
  "reviewerNotes",
  "lastChecked"
];

const argv = process.argv.slice(2);
const strict = argv.includes("--strict");
const help = argv.includes("--help") || argv.includes("-h");
const limitArg = argv.find((arg) => arg.startsWith("--limit="));
const issueLimit = limitArg ? Number.parseInt(limitArg.split("=")[1], 10) : 60;

if (help) {
  console.log(`Usage: node scripts/audit-source-evidence.mjs [--strict] [--limit=N]

Read-only audit for Paradiso source evidence metadata.

Default mode prints findings and exits 0.
--strict exits nonzero when error-level findings are present.
`);
  process.exit(0);
}

const summary = {
  filesScanned: 0,
  filesMissing: 0,
  recordsScanned: 0,
  verifiedRecordsChecked: 0,
  warnings: 0,
  errors: 0,
  unsupportedOrUnknownSourceStatusCount: 0
};

const findings = [];
const scannedFiles = [];
const missingFiles = [];

function isPlainObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function hasValue(value) {
  if (value === null || value === undefined) return false;
  if (typeof value === "string") return value.trim().length > 0;
  if (Array.isArray(value)) return value.length > 0;
  return true;
}

function candidateContainers(record) {
  const containers = [record];
  for (const key of EVIDENCE_CONTAINERS) {
    if (isPlainObject(record[key])) containers.push(record[key]);
  }
  return containers;
}

function getEvidenceValue(record, field) {
  for (const container of candidateContainers(record)) {
    if (Object.hasOwn(container, field) && hasValue(container[field])) {
      return container[field];
    }
  }
  return undefined;
}

function hasAnyEvidenceField(record, fields) {
  return fields.some((field) => hasValue(getEvidenceValue(record, field)));
}

function hasSourceLocator(record) {
  return hasAnyEvidenceField(record, LOCATOR_FIELDS);
}

function hasQuoteOrPreciseSection(record) {
  return hasAnyEvidenceField(record, [
    "sourceQuoteKo",
    "sourceQuote",
    "sourceQuoteEn",
    "preciseSectionReference",
    "sourceSection"
  ]);
}

function getSourceStatus(record) {
  return getEvidenceValue(record, "sourceStatus");
}

function appearsToMakeOfficialClaim(record, filePath) {
  if (!isPlainObject(record)) return false;
  if (filePath.endsWith("doc_master.json") && hasValue(record.id)) return true;
  if (hasValue(record.verified) || hasValue(record.needsManualReview)) return true;
  if (hasValue(getSourceStatus(record))) return true;
  return Object.keys(record).some((key) => CLAIM_KEYS.has(key) && hasValue(record[key]));
}

function looksAuditable(record, filePath) {
  return (
    appearsToMakeOfficialClaim(record, filePath) ||
    hasValue(record.verified) ||
    hasValue(record.needsManualReview) ||
    hasValue(getSourceStatus(record))
  );
}

function recordLabel(record, jsonPath) {
  const parts = [];
  for (const key of ["code", "subCode", "id", "name", "ko_name", "en_name", "procedure"]) {
    if (hasValue(record[key])) parts.push(`${key}=${String(record[key])}`);
  }
  return parts.length > 0 ? parts.join(" ") : jsonPath;
}

function addFinding(level, filePath, jsonPath, record, message) {
  findings.push({
    level,
    filePath,
    jsonPath,
    record: recordLabel(record, jsonPath),
    message
  });
  if (level === "error") summary.errors += 1;
  else summary.warnings += 1;
}

function validateRecord(record, filePath, jsonPath) {
  if (!looksAuditable(record, filePath)) return;

  summary.recordsScanned += 1;

  const sourceStatus = getSourceStatus(record);
  if (hasValue(sourceStatus)) {
    if (!VALID_SOURCE_STATUSES.has(sourceStatus)) {
      summary.unsupportedOrUnknownSourceStatusCount += 1;
      addFinding(
        "error",
        filePath,
        jsonPath,
        record,
        `invalid sourceStatus '${sourceStatus}'`
      );
    } else if (UNRESOLVED_SOURCE_STATUSES.has(sourceStatus)) {
      summary.unsupportedOrUnknownSourceStatusCount += 1;
    }
  }

  if (record.verified === true) {
    summary.verifiedRecordsChecked += 1;

    if (record.needsManualReview === true) {
      addFinding(
        "error",
        filePath,
        jsonPath,
        record,
        "record has verified=true and needsManualReview=true for the same object"
      );
    }

    const missing = REQUIRED_VERIFIED_EVIDENCE.filter(
      (field) => !hasValue(getEvidenceValue(record, field))
    );

    if (!hasSourceLocator(record)) missing.push("sourceLocator/sourceUrl/sourcePage/sourceSection");
    if (!hasQuoteOrPreciseSection(record)) missing.push("sourceQuoteKo/preciseSectionReference");

    if (sourceStatus && sourceStatus !== "source_confirmed") {
      missing.push("sourceStatus=source_confirmed");
    }

    const supportLevel = getEvidenceValue(record, "supportLevel");
    if (supportLevel && supportLevel !== "direct") {
      missing.push("supportLevel=direct");
    }

    if (missing.length > 0) {
      addFinding(
        "error",
        filePath,
        jsonPath,
        record,
        `verified=true lacks required source evidence: ${[...new Set(missing)].join(", ")}`
      );
    }
  }

  if (
    appearsToMakeOfficialClaim(record, filePath) &&
    !hasSourceLocator(record) &&
    record.verified !== false
  ) {
    addFinding(
      "warning",
      filePath,
      jsonPath,
      record,
      "claim-like record is missing a source locator field"
    );
  }
}

function walk(value, filePath, jsonPath = "$") {
  if (Array.isArray(value)) {
    value.forEach((item, index) => walk(item, filePath, `${jsonPath}[${index}]`));
    return;
  }

  if (!isPlainObject(value)) return;

  validateRecord(value, filePath, jsonPath);

  for (const [key, child] of Object.entries(value)) {
    if (isPlainObject(child) || Array.isArray(child)) {
      walk(child, filePath, `${jsonPath}.${key}`);
    }
  }
}

for (const filePath of DATA_FILES) {
  const absolutePath = path.resolve(filePath);
  if (!fs.existsSync(absolutePath)) {
    summary.filesMissing += 1;
    missingFiles.push(filePath);
    continue;
  }

  try {
    const parsed = JSON.parse(fs.readFileSync(absolutePath, "utf8"));
    scannedFiles.push(filePath);
    summary.filesScanned += 1;
    walk(parsed, filePath);
  } catch (error) {
    addFinding("error", filePath, "$", {}, `failed to parse JSON: ${error.message}`);
  }
}

function printFindings(level) {
  const selected = findings.filter((finding) => finding.level === level);
  if (selected.length === 0) return;

  console.log(`\n${level.toUpperCase()} findings`);
  for (const finding of selected.slice(0, issueLimit)) {
    console.log(
      `- [${finding.filePath} ${finding.jsonPath}] ${finding.record}: ${finding.message}`
    );
  }
  if (selected.length > issueLimit) {
    console.log(`- ... ${selected.length - issueLimit} more ${level} findings not shown`);
  }
}

console.log("Paradiso source evidence audit");
console.log(`Mode: ${strict ? "strict" : "report-only"}`);
console.log(`Scanned: ${scannedFiles.length > 0 ? scannedFiles.join(", ") : "(none)"}`);
if (missingFiles.length > 0) {
  console.log(`Missing optional files: ${missingFiles.join(", ")}`);
}

printFindings("error");
printFindings("warning");

console.log("\nSummary");
console.log("| Metric | Count |");
console.log("|---|---:|");
console.log(`| files scanned | ${summary.filesScanned} |`);
console.log(`| records scanned | ${summary.recordsScanned} |`);
console.log(`| verified records checked | ${summary.verifiedRecordsChecked} |`);
console.log(`| warnings | ${summary.warnings} |`);
console.log(`| errors | ${summary.errors} |`);
console.log(
  `| unsupported/unknown source status count | ${summary.unsupportedOrUnknownSourceStatusCount} |`
);

if (strict && summary.errors > 0) {
  process.exit(1);
}

process.exit(0);
