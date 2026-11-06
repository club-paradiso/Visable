// @ts-check
/**
 * Every static data path the index page loads, in one place (Phase 3, data layer).
 * Paths are relative to the page, exactly as the inline code wrote them before the
 * extraction; the Vite build copies these files verbatim (vite.config.mjs STATIC_COPIES),
 * so the public URLs never change. Canonical job-code dataset: docs/rebuild/phase0-data-canon.md.
 */
export const DATA_PATHS = Object.freeze({
  visaData: './visa_data.json',
  docMaster: './doc_master.json',
  i18nManifest: './data/i18n/manifest.json',
  i18nBase: './data/i18n/',
  officialTerms: './data/i18n/official-terms.json',
  visaNames: './data/i18n/visa-names.json',
  documentHelp: './data/document_help.json',
  docGuide: './data/doc_guide.json',
  integratedFormMetadata: './data/integrated_form_metadata.json',
  visaIssuanceRecords: './data/visa_issuance_records.json',
  procedureEvidenceBindings: './data/procedure_evidence_bindings.json',
  officialWebOverlays: './data/official_web_overlays.json',
  agentRegistry: 'data/agent_registry_2026-04-30.json',
  designatedMedicalInstitutions: 'data/designated_medical_institutions_2026_11_02.json',
  jobcodeMaster: './data/jobcode_master.json',
  employmentDir: './data/employment/'
});

/** Backend API routes the index page calls (relative to the backend origin). */
export const API_ROUTES = Object.freeze({
  visas: '/api/visas',
  ask: '/api/ask',
  employmentInterpret: '/api/employment/interpret'
});
