'use strict';

const LAW_CREDENTIAL_ENV_NAMES = Object.freeze([
  'LAW_API_OC',
  'LAW_OC',
  'OPEN_LAW_ID',
  'LAW_API_KEY',
]);

// `paradiso` was committed/documented historically as an example OC and a
// 2026-06 live probe returned 403 for it. Do not let that known placeholder
// shadow another configured credential (most importantly Railway's legacy
// LAW_API_KEY). If it is the only configured value we still return it for
// backward compatibility, while exposing only a non-secret warning flag.
const KNOWN_PLACEHOLDER_VALUES = new Set(['paradiso']);

function normalizeCredential(value) {
  return String(value || '').trim();
}

function isKnownPlaceholder(value) {
  return KNOWN_PLACEHOLDER_VALUES.has(normalizeCredential(value).toLowerCase());
}

function resolveLawCredential(env = process.env) {
  const configured = LAW_CREDENTIAL_ENV_NAMES
    .map((name) => ({ name, value: normalizeCredential(env && env[name]) }))
    .filter((item) => item.value);

  const preferredReal = configured.find((item) => !isKnownPlaceholder(item.value));
  const selected = preferredReal || configured[0];
  const ignoredPlaceholder = preferredReal
    ? configured.find((item) => isKnownPlaceholder(item.value) && item.name !== preferredReal.name)
    : null;

  if (!selected) {
    return { credential: '', credentialSource: '', ignoredPlaceholderSource: '' };
  }
  return {
    credential: selected.value,
    credentialSource: selected.name,
    ignoredPlaceholderSource: ignoredPlaceholder ? ignoredPlaceholder.name : '',
  };
}

function publicLawCredentialConfig(env = process.env) {
  const resolved = resolveLawCredential(env);
  return {
    lawApiConfigured: Boolean(resolved.credential),
    lawApiCredentialSource: resolved.credentialSource || null,
    lawApiIgnoredPlaceholderSource: resolved.ignoredPlaceholderSource || null,
    supportedCredentialEnvNames: [...LAW_CREDENTIAL_ENV_NAMES],
  };
}

module.exports = {
  KNOWN_PLACEHOLDER_VALUES,
  LAW_CREDENTIAL_ENV_NAMES,
  isKnownPlaceholder,
  publicLawCredentialConfig,
  resolveLawCredential,
};
