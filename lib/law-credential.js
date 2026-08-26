'use strict';

const LAW_CREDENTIAL_ENV_NAMES = Object.freeze([
  'LAW_API_OC',
  'LAW_OC',
  'OPEN_LAW_ID',
  'LAW_API_KEY',
]);

function resolveLawCredential(env = process.env) {
  for (const name of LAW_CREDENTIAL_ENV_NAMES) {
    const value = String((env && env[name]) || '').trim();
    if (value) return { credential: value, credentialSource: name };
  }
  return { credential: '', credentialSource: '' };
}

function publicLawCredentialConfig(env = process.env) {
  const resolved = resolveLawCredential(env);
  return {
    lawApiConfigured: Boolean(resolved.credential),
    lawApiCredentialSource: resolved.credentialSource || null,
    supportedCredentialEnvNames: [...LAW_CREDENTIAL_ENV_NAMES],
  };
}

module.exports = {
  LAW_CREDENTIAL_ENV_NAMES,
  publicLawCredentialConfig,
  resolveLawCredential,
};
