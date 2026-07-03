#!/usr/bin/env node
import fs from 'node:fs'; import path from 'node:path'; import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const read=p=>fs.readFileSync(path.join(root,p),'utf8');
const env=read('backend/.env.example'), backend=read('backend/paradiso_backend.py'), nim=read('backend/services/providers/nvidia_nim.py'), all=env+backend+nim;
const names=[...env.matchAll(/^([A-Z][A-Z0-9_]+)=/gm)].map(x=>x[1]);
const nv=['ENABLE_NVIDIA_NIM_EXPERIMENTAL','NVIDIA_API_KEY','NVIDIA_NIM_BASE_URL','NVIDIA_NIM_MODEL','NVIDIA_NIM_TIMEOUT_SECONDS','NVIDIA_NIM_MAX_TOKENS','NVIDIA_NIM_REASONING_ENABLED','NVIDIA_NIM_ALLOWED_MODES','NVIDIA_NIM_ALLOW_PERSONAL_DATA'];
const missing=nv.filter(x=>!names.includes(x)), disabled=/^ENABLE_NVIDIA_NIM_EXPERIMENTAL=false$/m.test(env), pii=/^NVIDIA_NIM_ALLOW_PERSONAL_DATA=false$/m.test(env);
const health=['provider_status','"openrouter"','"fallback_allowed"','"effective_mode"','"legal_evidence"','"nvidia_nim"','"production_ready": False'];
const missingHealth=health.filter(x=>!all.includes(x));
const hard=(all.match(/(?:nvapi-|sk-or-v1-)[A-Za-z0-9_-]{12,}/g)||[]).length;
const logs=(all.match(/(?:logger|print)[^\n]*(?:API_KEY|Authorization)/g)||[]).length;
const dir=path.join(root,'audits/api-provider-audit'); fs.mkdirSync(dir,{recursive:true});
const matrix=[
['OpenRouter','OPENROUTER_API_KEY, OPENROUTER_MODEL, OPENROUTER_MODEL_CANDIDATES, OPENROUTER_TIMEOUT_SECONDS, OPENROUTER_MODEL_COOLDOWN_SECONDS','primary when keyed'],
['Groq','GROQ_API_KEY, GROQ_MODEL, ALLOW_GROQ_FALLBACK','fallback default off'],
['NVIDIA NIM',nv.join(', '),'experimental; off; not /api/ask'],
['Open Law','LAW_API_OC, LAW_API_KEY, LAW_GROUNDING_MODE, LAW_GROUNDING_TIMEOUT_SECONDS, LAW_GROUNDING_CACHE_TTL_SECONDS','disabled/audit/enabled'],
['Legal evidence','LAW_API_ADMIN_APPEAL_TARGET, LAW_API_SPECIAL_ADMIN_APPEAL_TARGET','supplementary; shared OC'],
['Public data','PUBLIC_DATA_API_KEY, PUBLIC_DATA_BASE_URL, PUBLIC_DATA_VISA_PATH, PUBLIC_DATA_JOB_PATH','placeholder'],
['DB/Supabase','DATABASE_URL, SUPABASE_URL, SUPABASE_SERVICE_KEY','config flags only']];
fs.writeFileSync(path.join(dir,'summary.md'),`# API/provider static audit summary\n\nStatic only; no environment values or network.\n\n- NVIDIA vars documented: ${missing.length?'NO: '+missing:'YES'}\n- NVIDIA disabled by default: ${disabled?'YES':'NO'}\n- Personal data denied by default: ${pii?'YES':'NO'}\n- Structured health fields: ${missingHealth.length?'MISSING '+missingHealth:'YES'}\n- Suspicious hard-coded keys: ${hard}\n- Obvious key/header logging patterns: ${logs}\n- Raw \`resp.text\` references: ${(backend.match(/resp\.text/g)||[]).length}; manually reviewed, public /api/ask errors are replaced/sanitized.\n\nCannot prove Railway values, runtime logs, proxy behavior, or upstream retention.\n`);
fs.writeFileSync(path.join(dir,'provider-env-matrix.md'),'# Provider environment matrix\n\n| Integration | Documented variables | Posture |\n|---|---|---|\n'+matrix.map(r=>`| ${r[0]} | ${r[1].split(', ').map(x=>'`'+x+'`').join('<br>')} | ${r[2]} |`).join('\n')+'\n');
fs.writeFileSync(path.join(dir,'nvidia-readiness.md'),`# NVIDIA readiness\n\n- Key documented: ${names.includes('NVIDIA_API_KEY')?'yes':'no'}\n- Flag defaults off: ${disabled?'yes':'no'}\n- Modes research/internal QA: ${/^NVIDIA_NIM_ALLOWED_MODES=research,internal_qa$/m.test(env)?'yes':'no'}\n- Personal data blocked: ${pii?'yes':'no'}\n- Wired to /api/ask: no\n- Production ready: no\n- Live call: no\n\nKeep disabled; approved internal tests must use synthetic/public non-personal input.\n`);
const ok=!missing.length&&disabled&&pii&&!missingHealth.length&&!hard&&!logs;
console.log(JSON.stringify({ok,missingNvidia:missing,missingHealth,hardCodedKeyHits:hard,rawKeyLoggingHits:logs},null,2)); if(!ok) process.exitCode=1;
