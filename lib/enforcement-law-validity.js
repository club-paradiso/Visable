'use strict';

// Original VISABLE-specific temporal evidence guard. Uses official law metadata
// from the existing law.go.kr adapter, not third-party MCP implementation code.
// This is an evidence sufficiency test, NOT a source of historical statute text.

function dateIso(value) {
  const raw = String(value || '').trim();
  const match = raw.match(/^(\d{4})[.\/-]?(\d{1,2})[.\/-]?(\d{1,2})\.?$/);
  if (!match) return null;
  const iso = `${match[1]}-${match[2].padStart(2, '0')}-${match[3].padStart(2, '0')}`;
  const date = new Date(iso + 'T00:00:00Z');
  return !Number.isNaN(date.getTime()) && date.toISOString().slice(0, 10) === iso ? iso : null;
}

function assessTemporalLawEvidence(caseData, actEffectiveDate, ruleEffectiveDate) {
  const start = dateIso(caseData && caseData.violationStartDate);
  const end = dateIso(caseData && caseData.violationEndDate);
  const act = dateIso(actEffectiveDate);
  const rule = dateIso(ruleEffectiveDate);
  if (!start || !end || start > end) {
    return { verified: false, code: 'violation_dates_required', 
      note: '정확한 위반 시작일·종료일이 없어 사건 당시 법령과 현재 조회된 법령의 동일성을 확정할 수 없습니다.' };
  }
  if (!act || !rule) {
    return { verified: false, code: 'effective_dates_unavailable',
      note: '법제처 응답의 법령 시행일을 확인할 수 없어 당시 시행법 검증을 완료하지 못했습니다.' };
  }
  if (act > start || rule > start) {
    return { verified: false, code: 'historical_version_required',
      note: '사건 발생 뒤 시행된 법령이 검색되었습니다. 당시 시행 법령·별표의 별도 원문 확인이 필요합니다.' };
  }
  return { verified: true, code: 'current_source_effective_at_violation',
    note: null };
}

module.exports = { assessTemporalLawEvidence, dateIso };
