'use strict';

const { LAW_CREDENTIAL_ENV_NAMES, resolveLawCredential } = require('../../lib/law-credential');

const LAW_HOST = 'https://www.law.go.kr';

// Law-search responses can wrap records in objects or arrays and can include
// highlighted titles. Never expose the raw upstream response or the OC.
function normalizedLawName(value) {
  return String(value || '')
    .replace(/<[^>]*>/g, '')
    .replace(/&(?:nbsp|middot|#160|#183);/gi, '')
    .replace(/[\s·]/g, '')
    .trim();
}

function inspectLawResponse(data, lawName) {
  const wanted = normalizedLawName(lawName);
  const stack = [data];
  let nodes = 0;
  let namedLawCount = 0;
  let exactLawFound = false;
  let totalCount = null;
  let upstreamErrorKind = null;
  while (stack.length && nodes < 10000) {
    const value = stack.pop();
    nodes += 1;
    if (Array.isArray(value)) {
      stack.push(...value);
      continue;
    }
    if (!value || typeof value !== 'object') continue;
    const name = value['법령명한글'] || value['법령명'] || value['법령명_한글'] || value.lawName || value['법령명한글보기'];
    if (typeof name === 'string' && name.trim()) {
      namedLawCount += 1;
      if (normalizedLawName(name) === wanted) exactLawFound = true;
    }
    if (totalCount === null) {
      const total = value.totalCnt ?? value.totalCount;
      if (total !== undefined && total !== null && /^\\d{1,8}$/.test(String(total))) {
        totalCount = Number(total);
      }
    }
    // Upstream APIs sometimes encode an application/auth failure in HTTP 200 JSON.
    // Examine only known message fields; return a category, never the message.
    for (const field of ['errorMessage', 'resultMsg', 'message', 'msg', 'error', 'detail', '결과메시지']) {
      if (typeof value[field] !== 'string' || !value[field].trim()) continue;
      const message = value[field];
      if (/인증|승인|권한|접근|등록되지|도메인|아이피|(?:\\bIP\\b)|(?:\\bOC\\b)|invalid|unauthori[sz]ed|forbidden/i.test(message)) {
        upstreamErrorKind = 'authorization_or_registration';
      } else if (!upstreamErrorKind) {
        upstreamErrorKind = 'application_error';
      }
    }
    for (const child of Object.values(value)) {
      if (child && typeof child === 'object') stack.push(child);
    }
  }
  const responseKind = upstreamErrorKind
    ? 'upstream_application_error'
    : namedLawCount > 0 ? 'law_records'
    : totalCount === 0 ? 'empty_results'
    : 'unrecognized_response';
  const status = exactLawFound ? 'ok'
    : upstreamErrorKind === 'authorization_or_registration' ? 'upstream_authorization_or_registration_error'
    : upstreamErrorKind ? 'upstream_application_error'
    : namedLawCount > 0 ? 'no_exact_law_match'
    : totalCount === 0 ? 'no_results'
    : 'unexpected_json_shape';
  return {
    exactLawFound,
    status,
    diagnostics: { responseKind, namedLawCount, totalCount, scanLimitReached: nodes >= 10000 },
  };
}

module.exports = async function handler(request, response) {
  if (request.method !== 'GET') {
    response.setHeader('Allow', 'GET');
    return response.status(405).json({ detail: 'method not allowed' });
  }

  const resolved = resolveLawCredential();
  const credential = resolved.credential;
  const credentialSource = resolved.credentialSource || null;
  const mode = String(process.env.LAW_GROUNDING_MODE || 'enabled').trim().toLowerCase();
  const publicBase = {
    service: 'visable-enforcement-law-probe',
    credentialSource,
    supportedCredentialEnvNames: [...LAW_CREDENTIAL_ENV_NAMES],
    mode,
  };

  if (!credential) {
    return response.status(200).json({
      ...publicBase,
      configured: false,
      reachable: false,
      exactLawFound: false,
      status: 'not_configured',
    });
  }

  const params = new URLSearchParams({
    OC: credential,
    target: 'law',
    type: 'JSON',
    query: '출입국관리법',
    display: '5',
  });
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 8000);

  try {
    const upstream = await fetch(`${LAW_HOST}/DRF/lawSearch.do?${params.toString()}`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      signal: controller.signal,
    });
    if (!upstream.ok) {
      return response.status(200).json({
        ...publicBase,
        configured: true,
        reachable: true,
        exactLawFound: false,
        status: `upstream_http_${upstream.status}`,
      });
    }
    const text = await upstream.text();
    let data;
    try { data = JSON.parse(text); }
    catch {
      return response.status(200).json({
        ...publicBase,
        configured: true,
        reachable: true,
        exactLawFound: false,
        status: 'unexpected_non_json_response',
      });
    }
    const inspection = inspectLawResponse(data, '출입국관리법');
    response.setHeader('Cache-Control', 'no-store');
    return response.status(200).json({
      ...publicBase,
      configured: true,
      reachable: true,
      ...inspection,
    });
  } catch (error) {
    return response.status(200).json({
      ...publicBase,
      configured: true,
      reachable: false,
      exactLawFound: false,
      status: error && error.name === 'AbortError' ? 'timeout' : 'network_error',
    });
  } finally {
    clearTimeout(timer);
  }
};
