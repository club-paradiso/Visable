/*
 * manual-reader.js — Visable 매뉴얼 원문 읽기 (manual.html).
 * Data: data/manual-reader/catalog.json (sections only), chapters/<v|s>/<key>.json (lazy),
 * search.json (lazy, first search), editorial.json (Visable plain-language layer).
 * Built by scripts/build_manual_reader.py; checked by scripts/check_manual_reader.mjs.
 * The manual text is rendered as built; this file only adds navigation, a per-viewer
 * document checklist (localStorage), glossary pop-overs and search highlighting.
 */
(function(){
'use strict';
const BASE = 'data/manual-reader/';
const IMG_BASE = 'assets/manual-reader/img/';
const app = document.getElementById('mr-app');
let CAT = null, ED = null;            // catalog (sections only) + editorial layer
let GROUPS, VISAS, EXTRA_CHAPTERS, SEC, TASKS, QUICK, GLOSSARY;
const CH = {};                         // chapter cache: CH['F-6/s'] = {blocks}
const ROUTE = () => window.VisableManualReaderRoute;
function fetchJson(url){ return fetch(url).then(r => { if (!r.ok) throw new Error('HTTP ' + r.status + ' ' + url); return r.json(); }); }
function chapterData(key, src){
  const id = key + '/' + src;
  if (CH[id]) return Promise.resolve(CH[id]);
  return fetchJson(BASE + 'chapters/' + src + '/' + encodeURIComponent(key) + '.json').then(d => (CH[id] = d));
}
function catEntry(key){ return CAT.chapters.find(c => c.key === key) || null; }
function catSections(key, src){ const e = catEntry(key); return e && e[src] ? e[src].sections : null; }
const $ = (s, r=document) => r.querySelector(s);
const $$ = (s, r=document) => Array.from(r.querySelectorAll(s));
const esc = s => String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const store = {
  get(k, d){ try { const v = localStorage.getItem('visable:manual-reader:'+k); return v == null ? d : JSON.parse(v); } catch(e){ return d; } },
  set(k, v){ try { localStorage.setItem('visable:manual-reader:'+k, JSON.stringify(v)); } catch(e){} }
};
const SRC_NAME = { v:'사증발급 안내매뉴얼', s:'외국인체류 안내매뉴얼' };
const TAB = {
  v: { t:'한국에 오기 전', b:'비자(사증) 받기' },
  s: { t:'한국에 있을 때', b:'연장·변경·등록 등' }
};

// ---------- font size
let fs = store.get('fs', 16);
function applyFs(){ document.documentElement.style.setProperty('--fs', fs + 'px'); }
applyFs();
$('#mr-fsm').onclick = () => { fs = Math.max(14, fs - 1); applyFs(); store.set('fs', fs); };
$('#mr-fsp').onclick = () => { fs = Math.min(22, fs + 1); applyFs(); store.set('fs', fs); };

// ---------- helpers
function chapterInfo(key){
  const v = VISAS.find(x => x.key === key && !x.link);
  if (v) return v;
  if (EXTRA_CHAPTERS[key]) return Object.assign({ key, code: key === 'common' ? '공통' : '부록' }, EXTRA_CHAPTERS[key]);
  return { key, code: key, name: key, en: '', d: '' };
}
function stripTags(h){
  return h.replace(/<[^>]+>/g, ' ').replace(/&nbsp;/g,' ').replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&quot;/g,'"').replace(/&#x27;|&#39;/g,"'").replace(/&amp;/g,'&').replace(/\s+/g,' ').trim();
}
function secTitle(b){
  if (b.t === 'sec' && SEC[b.k]) return SEC[b.k].t;
  if (b.t === 'sec') return b.l || '이어지는 내용';
  return '본문';
}
function firstSentence(html, max){
  const t = stripTags(html);
  if (!t) return '';
  return t.length > max ? t.slice(0, max).replace(/\s\S*$/, '') + '…' : t;
}
function sectionIndex(secs, want){
  if (!secs || want == null || want === '') return -1;
  if (/^\d+$/.test(want)) return +want < secs.length ? +want : -1;
  if (want === 'parttime'){
    const i = secs.findIndex(b => b.t === 'sec' && /시간제\s*취업/.test(b.l || ''));
    return i >= 0 ? i : secs.findIndex(b => b.t === 'sec' && b.k === 'extra');
  }
  return secs.findIndex(b => b.t === 'sec' && b.k === want);
}
function toast(msg){
  const t = document.createElement('div'); t.className = 'toast'; t.textContent = msg; t.setAttribute('role','status');
  document.body.appendChild(t); setTimeout(() => t.remove(), 1800);
}

// ---------- routing
let task = store.get('task', null);
function go(h){ if (location.hash === '#' + h) route(); else location.hash = h; }
window.addEventListener('hashchange', route);

function route(){
  closePop();
  const h = decodeURIComponent(location.hash.slice(1));
  const q = $('#mr-q');
  if (!h || h === 'home'){ q.value = ''; renderHome(); return; }
  if (h === 'glossary'){ renderGlossary(); return; }
  if (h.startsWith('c-')){
    const parts = h.slice(2).split('.');
    renderChapter(parts[0], parts[1], parts[2]);
    return;
  }
  renderHome();
}

// ---------- home
function renderHome(){
  document.title = '매뉴얼 원문 읽기 | VISABLE';
  const t = TASKS.find(x => x.id === task);
  let html = `
  <section class="intro">
    <div>
      <div class="eyebrow">OFFICIAL MANUALS / 2026.09</div>
      <h1>매뉴얼 원문을,<br>내 자격과 업무만 골라 읽어요</h1>
      <p>법무부 「사증발급 안내매뉴얼」(2026. 9. 1.)과 「외국인체류 안내매뉴얼」(2026. 9. 18.) 원문을 고치지 않고 체류자격·업무별로 나눠 보여 드려요. 쉬운 말 제목과 서류 체크리스트는 Visable이 덧붙인 것이에요.</p>
      <p class="srcline"><span class="state">원문 발췌 · 검토 전</span><a href="docs/source-manuals/2026-09/visa_manual_260901.pdf" target="_blank" rel="noopener">사증발급 PDF</a><a href="docs/source-manuals/2026-09/stay_manual_260918.pdf" target="_blank" rel="noopener">외국인체류 PDF</a><a href="${esc(CAT.sources.v.official_url)}" target="_blank" rel="noopener">HiKorea 공지</a></p>
    </div>
    <ol class="howto" aria-label="이용 방법">
      <li>하려는 일을 고르세요. (선택)</li>
      <li>체류자격(비자 종류)을 고르세요.</li>
      <li>서류 목록을 눌러 하나씩 체크하세요.</li>
    </ol>
  </section>
  <div class="block-h"><h2 id="taskh">무엇을 하려고 하나요?</h2><span>고르면 자격 카드에서 그 안내로 바로 이동해요</span></div>
  <div class="tasks" role="group" aria-labelledby="taskh">
    ${TASKS.map(x => `<button class="task" type="button" data-task="${x.id}" aria-pressed="${x.id === task}"><small>${x.s}</small><b>${x.t}</b><span>${x.d}</span></button>`).join('')}
  </div>
  <div class="taskbar" aria-live="polite">${t ? `선택함: <b>${t.t}</b> · 아래에서 체류자격을 고르세요 <button type="button" id="clr">선택 해제</button>` : ''}</div>
  <div class="block-h"><h2>많이 찾는 안내</h2></div>
  <div class="quick">${QUICK.map(x => { const h = quickHref(x); return h ? `<a href="${h}">${esc(x.t)}</a>` : ''; }).join('')}</div>
  <div class="block-h"><h2>체류자격 고르기</h2><span>코드는 외국인등록증·비자에 적혀 있어요</span></div>`;
  for (const g of GROUPS){
    const items = VISAS.filter(v => v.g === g.id);
    html += `<section class="group"><h3>${g.name} <small>${g.en}</small></h3><div class="cards">`;
    for (const v of items){
      let href = '#c-' + v.key, miss = '', dim = false, goTxt = '';
      if (t && !v.link){
        const src = t.src;
        const secs = catSections(v.key, src);
        const sec = secs ? secs.findIndex(b => b.t === 'sec' && t.keys.includes(b.k)) : -1;
        if (sec >= 0){ href = `#c-${v.key}.${src}.${sec}`; goTxt = `${t.t} 안내로 →`; }
        else if (secs){ href = `#c-${v.key}.${src}`; miss = '이 자격에는 해당 항목이 따로 없어요. 전체 안내를 확인하세요.'; dim = true; }
      }
      html += `<a class="card${dim ? ' dim' : ''}" href="${href}"><span class="stamp${v.code.length > 5 || /[가-힣]/.test(v.code) ? ' k' : ''}">${esc(v.code)}</span><span><span class="nm">${esc(v.name)}</span><br><span class="en">${esc(v.en)}</span></span><p>${esc(v.d)}</p>${goTxt ? `<span class="go">${goTxt}</span>` : ''}${miss ? `<span class="miss">${miss}</span>` : ''}</a>`;
    }
    html += `</div></section>`;
  }
  html += `
  <div class="block-h"><h2>모두에게 해당하는 안내</h2></div>
  <div class="commons">
    <a href="#c-common"><b>신청 전에 꼭 읽어 주세요</b><span>서류 유효기간, 번역·아포스티유, 수수료, 결핵진단서, 여권 유효기간</span></a>
    <a href="#glossary"><b>어려운 용어 풀이</b><span>사증발급인정서, 체류자격외 활동, 신원보증서 같은 말을 쉽게</span></a>
    <a href="#c-D-3-rule"><b>기술연수생 훈령 (부록)</b><span>해외투자기업 기술연수생 관련 훈령과 서식</span></a>
  </div>
  ${footer()}`;
  app.innerHTML = html;
  $$('.task').forEach(b => b.onclick = () => { task = task === b.dataset.task ? null : b.dataset.task; store.set('task', task); renderHome(); $(`.task[data-task="${b.dataset.task}"]`)?.focus(); });
  const clr = $('#clr'); if (clr) clr.onclick = () => { task = null; store.set('task', null); renderHome(); };
  window.scrollTo(0, 0);
}

function quickHref(x){
  const secs = catSections(x.key, x.src);
  if (!secs) return null;
  let i = -1;
  if (x.lab) i = secs.findIndex(b => b.t === 'sec' && (b.l || '').includes(x.lab));
  else if (x.sec) i = secs.findIndex(b => b.t === 'sec' && b.k === x.sec);
  return `#c-${x.key}.${x.src}` + (i >= 0 ? '.' + i : '');
}
function footer(){
  return `<footer class="foot">
    <p><b>법무부 출입국·외국인정책본부 「사증발급 안내매뉴얼」(2026. 9. 1.)·「외국인체류 안내매뉴얼」(2026. 9. 18.) 원문을 Visable이 읽기 쉽게 나눠 보여 주는 화면입니다.</b> 원문 문장은 고치지 않았고, 쪽 넘김 때문에 반복된 항목명과 표지 그림만 뺐습니다. 쉬운 말 제목·자격 소개·용어 풀이·서류 체크는 Visable 편집 안내이며 법적 요건이 아닙니다. 원문 내용 검토는 아직 진행 중이므로, 표·그림과 적용 조건은 공식 PDF에서 확인하세요. 허가 여부는 심사로 결정되며, 출입국·외국인관서는 필요하면 제출서류를 더하거나 줄일 수 있습니다.</p>
    <p>문의: 외국인종합안내센터 <span class="sel">1345</span> · 하이코리아 <a href="https://www.hikorea.go.kr" target="_blank" rel="noopener">www.hikorea.go.kr</a> · <a href="index.html">Visable로 돌아가기</a></p>
    <p lang="en">This reader shows the Korean original text. Use your browser's translate feature to read it in another language.</p>
  </footer>`;
}

// ---------- glossary
function renderGlossary(){
  document.title = '용어 풀이 | 매뉴얼 원문 읽기 | VISABLE';
  app.innerHTML = `<div class="crumb"><a href="#home">← 처음으로</a></div>
    <h1 style="margin:0 0 6px">어려운 용어 풀이<span class="ed">Visable 편집</span></h1>
    <p style="color:var(--ink2);margin:0 0 16px">본문에서 점선 밑줄이 있는 말을 누르면 같은 설명이 나와요.</p>
    <dl class="gloss">${GLOSSARY.map(([t,d]) => `<div><dt>${esc(t)}</dt><dd>${esc(d)}</dd></div>`).join('')}</dl>${footer()}`;
  window.scrollTo(0,0);
}

// ---------- chapter
let current = null;
let renderSeq = 0;
function renderChapter(key, tab, secIdx, opts){
  const entry = catEntry(key);
  if (!entry){ renderHome(); return; }
  if (!tab || !entry[tab]) tab = entry.v ? 'v' : 's';
  const seq = ++renderSeq;
  if (!app.querySelector('#secs') || !current || current.key !== key || current.tab !== tab) app.innerHTML = '<p class="mr-loading" role="status">원문을 불러오는 중입니다.</p>';
  const want = ['v', 's'].filter(s => entry[s]);
  Promise.all(want.map(s => chapterData(key, s))).then(list => {
    if (seq !== renderSeq) return;
    const ch = {}; want.forEach((s, i) => { ch[s] = list[i]; });
    const secs = ch[tab].blocks;
    const resolved = sectionIndex(secs, secIdx);
    drawChapter(key, tab, ch, resolved >= 0 ? String(resolved) : null, opts);
  }).catch(err => {
    if (seq !== renderSeq) return;
    app.innerHTML = `<div class="mr-err" role="alert">원문을 불러오지 못했어요. <button type="button" id="mr-retry">다시 시도</button> 또는 <a href="docs/source-manuals/2026-09/${tab === 'v' ? 'visa_manual_260901' : 'stay_manual_260918'}.pdf" target="_blank" rel="noopener">공식 PDF</a>를 여세요.</div>`;
    $('#mr-retry').onclick = () => renderChapter(key, tab, secIdx, opts);
    console.error(err);
  });
}
function drawChapter(key, tab, ch, secIdx, opts){
  opts = opts || {};
  const info = chapterInfo(key);
  const blocks = ch[tab].blocks;
  document.title = `${info.name}${/[A-Z]-/.test(info.code) ? ' (' + info.code + ')' : ''} | 매뉴얼 원문 읽기 | VISABLE`;

  // quick facts from both manuals
  const facts = [];
  const pick = (src, k) => { const c = ch[src]; if (!c) return null; const i = c.blocks.findIndex(b => b.t === 'sec' && b.k === k); return i < 0 ? null : { i, b: c.blocks[i], src }; };
  const per = pick('s','period') || pick('v','period');
  const scope = pick('v','scope') || pick('s','scope') || pick('v','who');
  if (scope) facts.push(`<div class="fact"><small>할 수 있는 일 (원문 앞부분)</small><div>${esc(firstSentence(scope.b.h, 110))}</div><a href="#c-${key}.${scope.src}.${scope.i}">원문 보기</a></div>`);
  if (per) facts.push(`<div class="fact"><small>한 번에 받을 수 있는 최대 체류기간</small><div>${esc(firstSentence(per.b.h, 110))}</div><a href="#c-${key}.${per.src}.${per.i}">원문 보기</a></div>`);

  const tabBtn = s => {
    const has = !!ch[s];
    const n = has ? ch[s].blocks.filter(b => b.t === 'sec').length : 0;
    return `<button class="tab" role="tab" type="button" data-tab="${s}" aria-selected="${s === tab}" ${has ? '' : 'disabled'}><small>${TAB[s].t}</small><b>${TAB[s].b}</b></button>`;
  };

  // toc
  let toc = '<b>이 탭의 목차</b>';
  blocks.forEach((b, i) => {
    if (b.t === 'sec'){
      const orig = SEC[b.k] ? SEC[b.k].s : '';
      toc += `<a href="#c-${key}.${tab}.${i}" data-i="${i}">${esc(secTitle(b))}${orig ? `<small>${esc(orig)}</small>` : ''}</a>`;
    } else {
      const heads = [...b.h.matchAll(/<(h3 class="banner"|h4 class="fh"|h1|h2)[^>]*>([\s\S]*?)<\/(h3|h4|h1|h2)>/g)].map(m => stripTags(m[2])).filter(Boolean);
      toc += `<a href="#c-${key}.${tab}.${i}" data-i="${i}">${blocks.length === 1 ? '본문 전체' : '본문'}</a>`;
      heads.slice(0, 60).forEach((hd, j) => { toc += `<a class="sub" href="#c-${key}.${tab}.${i}" data-i="${i}" data-h="${j}">${esc(hd.length > 40 ? hd.slice(0, 40) + '…' : hd)}</a>`; });
    }
  });

  const links = VISAS.filter(v => v.link && v.key === key).map(v => v.code);
  app.innerHTML = `
    <div class="crumb"><a href="#home">← 체류자격 목록</a></div>
    <div class="chead">
      <span class="stamp lg${/[가-힣]/.test(info.code) || info.code.length > 5 ? ' k' : ''}">${esc(info.code)}</span>
      <div><h1>${esc(info.name)}</h1><div class="en">${esc(info.en || '')}${links.length ? ' · ' + links.join(', ') + ' 포함' : ''}</div></div>
      ${info.d ? `<p class="lead">${esc(info.d)}<span class="ed">Visable 편집 설명</span></p>` : ''}
    </div>
    ${facts.length ? `<div class="facts">${facts.join('')}</div>` : ''}
    <div class="tabs" role="tablist" aria-label="매뉴얼 선택">${tabBtn('v')}${tabBtn('s')}</div>
    <div class="layout">
      <nav class="toc" aria-label="목차"><details class="tocd" ${matchMedia('(max-width:900px)').matches ? '' : 'open'}><summary>이 탭의 목차</summary>${toc}</details></nav>
      <div class="doc">
        <p class="disc"><span class="state">원문 발췌 · 검토 전</span> 아래는 「${SRC_NAME[tab]}」(${esc(CAT.sources[tab].date.replace(/-/g, '. ').replace(/^(\d+)\. 0?(\d+)\. 0?(\d+)$/, '$1. $2. $3.'))}) 원문이에요. 굵은 제목은 Visable이 붙인 쉬운 말이고, 회색 꼬리표가 원문 항목명이에요. 표·그림과 적용 조건은 <a href="${esc(CAT.sources[tab].pdf)}" target="_blank" rel="noopener">공식 PDF</a>에서 확인하세요.</p>
        <div id="secs"></div>
      </div>
    </div>${footer()}`;
  current = { key, tab };

  const wrap = $('#secs');
  const frag = document.createDocumentFragment();
  blocks.forEach((b, i) => {
    const s = document.createElement('section');
    s.className = 'sec' + (b.t === 'html' ? ' free-sec' : '');
    s.id = `s${i}`;
    const orig = b.t === 'sec' && SEC[b.k] ? `<span class="orig">${esc(b.l)}</span>` : '';
    const title = b.t === 'sec' ? `<header><h2>${esc(secTitle(b))}</h2>${orig}</header>` : `<header><h2>${blocks.length === 1 ? esc(info.name) + ' 안내 본문' : '본문'}</h2></header>`;
    s.innerHTML = `${title}<div class="sec-body${b.t === 'html' ? ' free' : ''}"></div>`;
    const body = s.querySelector('.sec-body');
    body.innerHTML = b.h;
    enhance(body, `${key}|${tab}|${i}`);
    const long = b.h.length > 9000 && b.t === 'sec';
    if (long && String(i) !== secIdx){
      body.classList.add('clip');
      const m = document.createElement('div'); m.className = 'more';
      const mins = Math.max(1, Math.round(stripTags(b.h).length / 600));
      m.innerHTML = `<button type="button" aria-expanded="false">전체 펼치기 · 약 ${mins}분 분량</button>`;
      m.firstChild.onclick = () => { body.classList.remove('clip'); m.remove(); };
      s.appendChild(m);
    }
    frag.appendChild(s);
  });
  wrap.appendChild(frag);

  $$('.tab').forEach(bt => bt.onclick = () => { if (!bt.disabled) go(`c-${key}.${bt.dataset.tab}`); });
  $$('.toc a').forEach(a => a.addEventListener('click', e => {
    e.preventDefault();
    const i = a.dataset.i;
    history.replaceState(null, '', `#c-${key}.${tab}.${i}`);
    if (matchMedia('(max-width:900px)').matches){ const d = a.closest('details'); if (d) d.open = false; }
    scrollToSec(i, a.dataset.h);
  }));
  setupSpy();
  if (secIdx != null && secIdx !== ''){
    requestAnimationFrame(() => scrollToSec(secIdx, null, opts.term));
  } else window.scrollTo(0, 0);
}

function scrollToSec(i, h, term){
  const s = document.getElementById('s' + i);
  if (!s) return;
  const body = s.querySelector('.sec-body');
  if (body.classList.contains('clip')){ body.classList.remove('clip'); s.querySelector('.more')?.remove(); }
  let target = s;
  if (h != null){
    const heads = $$('h3.banner, h4.fh, h1, h2', body);
    if (heads[+h]) target = heads[+h];
  }
  if (term){
    const m = markTerm(body, term);
    if (m) target = m;
  }
  target.scrollIntoView({ block: target === s ? 'start' : 'center' });
  s.classList.add('hit'); setTimeout(() => s.classList.remove('hit'), 1600);
}

function setupSpy(){
  const links = $$('.toc a:not(.sub)');
  if (!('IntersectionObserver' in window) || !links.length) return;
  const map = new Map(links.map(a => [a.dataset.i, a]));
  const io = new IntersectionObserver(es => {
    es.forEach(e => {
      if (e.isIntersecting){
        links.forEach(a => a.classList.remove('on'));
        const a = map.get(e.target.id.slice(1));
        if (a) a.classList.add('on');
      }
    });
  }, { rootMargin: '-30% 0px -60% 0px' });
  $$('#secs > section').forEach(s => io.observe(s));
}

// ---------- enhancements: images, checklists, glossary terms
function enhance(body, base){
  $$('img[data-img]', body).forEach(img => { img.src = IMG_BASE + img.dataset.img + '.webp'; img.decoding = 'async'; });
  // checklist lists
  $$('ul.docs', body).forEach((ul, li_i) => {
    const items = $$(':scope > li.doc', ul);
    if (!items.length) return;
    const sk = `${base}|${li_i}`;
    const saved = store.get('ck:' + sk, []);
    items.forEach((li, j) => {
      li.setAttribute('role', 'checkbox'); li.tabIndex = 0;
      const on = saved.includes(j);
      li.classList.toggle('on', on); li.setAttribute('aria-checked', on);
    });
    const bar = document.createElement('div'); bar.className = 'dtools';
    bar.innerHTML = `<span>준비 서류 체크</span><span class="cnt"></span><button type="button" data-a="copy">목록 복사</button><button type="button" data-a="reset">체크 지우기</button>`;
    ul.before(bar);
    const upd = () => {
      const st = items.map((li, j) => li.classList.contains('on') ? j : -1).filter(j => j >= 0);
      store.set('ck:' + sk, st);
      bar.querySelector('.cnt').textContent = `${st.length} / ${items.length}`;
    };
    upd();
    const toggle = li => { li.classList.toggle('on'); li.setAttribute('aria-checked', li.classList.contains('on')); upd(); };
    items.forEach(li => {
      li.addEventListener('click', e => { if (e.target.closest('a,button.gl')) return; toggle(li); });
      li.addEventListener('keydown', e => { if (e.key === ' ' || e.key === 'Enter'){ e.preventDefault(); toggle(li); } });
    });
    bar.querySelector('[data-a=reset]').onclick = () => { items.forEach(li => { li.classList.remove('on'); li.setAttribute('aria-checked', false); }); upd(); };
    bar.querySelector('[data-a=copy]').onclick = () => {
      const txt = items.map(li => (li.classList.contains('on') ? '[v] ' : '[ ] ') + li.querySelector('.dt').textContent.trim()).join('\n');
      const done = () => toast('서류 목록을 복사했어요');
      try {
        navigator.clipboard.writeText(txt).then(done, () => fallbackCopy(bar, txt));
      } catch(e){ fallbackCopy(bar, txt); }
    };
  });
  // glossary terms: first occurrence per section
  const used = new Set(GL_SKIP_IDX);
  let added = 0;
  const walker = document.createTreeWalker(body, NodeFilter.SHOW_TEXT, { acceptNode: n => n.parentElement.closest('button,a,th,.dtools,b.k,.hd,h3,h4,mark') ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT });
  const nodes = []; while (walker.nextNode()) nodes.push(walker.currentNode);
  for (const n of nodes){
    if (used.size >= GLOSSARY.length || added >= 4) break;
    for (let gi = 0; gi < GLOSSARY.length; gi++){
      if (used.has(gi)) continue;
      const term = GLOSSARY[gi][0];
      const idx = n.data.indexOf(term);
      if (idx < 0) continue;
      used.add(gi);
      const after = n.splitText(idx); after.splitText(term.length);
      const b = document.createElement('button'); b.type = 'button'; b.className = 'gl'; b.dataset.g = gi; b.textContent = term;
      after.replaceWith(b); added++;
      break;
    }
  }
}
let GL_SKIP_IDX = [];
function fallbackCopy(bar, txt){
  let ta = bar.nextElementSibling && bar.nextElementSibling.classList.contains('copybox') ? bar.nextElementSibling : null;
  if (!ta){ ta = document.createElement('textarea'); ta.className = 'copybox'; ta.readOnly = true; bar.after(ta); }
  ta.value = txt; ta.focus(); ta.select();
  toast('목록을 선택해 두었어요. 복사해서 쓰세요');
}

// glossary popover
let pop = null;
function closePop(){ if (pop){ pop.remove(); pop = null; } }
document.addEventListener('click', e => {
  const b = e.target.closest('button.gl');
  if (!b){ if (!e.target.closest('.pop')) closePop(); return; }
  e.stopPropagation();
  closePop();
  const [t, d] = GLOSSARY[+b.dataset.g];
  pop = document.createElement('div'); pop.className = 'pop'; pop.setAttribute('role', 'tooltip');
  pop.innerHTML = `<b>${esc(t)}</b>${esc(d)}`;
  document.body.appendChild(pop);
  const r = b.getBoundingClientRect(), pw = pop.offsetWidth, ph = pop.offsetHeight;
  let x = Math.min(Math.max(16, r.left), window.innerWidth - pw - 16);
  let y = r.bottom + 8; if (y + ph > window.innerHeight - 16) y = r.top - ph - 8;
  pop.style.left = x + 'px'; pop.style.top = y + 'px';
});
window.addEventListener('scroll', closePop, { passive: true });
document.addEventListener('keydown', e => { if (e.key === 'Escape') closePop(); });

function markTerm(root, term){
  const words = term.split(/\s+/).filter(w => w.length >= 1);
  const w = words.sort((a,b) => b.length - a.length)[0];
  if (!w) return null;
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  let first = null, count = 0;
  const hits = [];
  while (walker.nextNode()){
    const n = walker.currentNode;
    if (n.data.toLowerCase().includes(w.toLowerCase())) hits.push(n);
  }
  for (const n of hits){
    if (count > 50) break;
    const i = n.data.toLowerCase().indexOf(w.toLowerCase());
    const mid = n.splitText(i); mid.splitText(w.length);
    const m = document.createElement('mark'); m.textContent = mid.data; mid.replaceWith(m);
    if (!first) first = m; count++;
  }
  return first;
}

// ---------- search
let INDEX = null, indexPromise = null;
function loadIndex(){
  if (INDEX) return Promise.resolve(INDEX);
  if (!indexPromise) indexPromise = fetchJson(BASE + 'search.json').then(rows => {
    INDEX = rows.map(([key, src, i, text]) => {
      const secs = catSections(key, src) || [];
      const b = secs[i] || { t: 'html' };
      return { key, src, i, title: secTitle(b), orig: b.l || '', text };
    });
    return INDEX;
  }).catch(e => { indexPromise = null; throw e; });
  return indexPromise;
}
function norm(s){ return s.toLowerCase().replace(/\s+/g, ' ').trim(); }
function snippet(text, terms){
  const low = text.toLowerCase();
  let pos = -1;
  const ord = terms.slice().sort((a, b) => (/^[a-z]-?\d/i.test(a) ? 1 : 0) - (/^[a-z]-?\d/i.test(b) ? 1 : 0) || b.length - a.length);
  for (const t of ord){ pos = low.indexOf(t); if (pos >= 0) break; }
  if (pos < 0) pos = 0;
  const start = Math.max(0, pos - 50);
  let s = (start > 0 ? '…' : '') + text.slice(start, start + 170) + (start + 170 < text.length ? '…' : '');
  s = esc(s);
  for (const t of terms){
    if (!t) continue;
    const rx = new RegExp(esc(t).replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi');
    s = s.replace(rx, m => `<mark>${m}</mark>`);
  }
  return s;
}
function renderSearch(q){
  if (!INDEX){
    app.innerHTML = '<p class="mr-loading" role="status">검색 색인을 불러오는 중입니다.</p>';
    loadIndex().then(() => { if ($('#mr-q').value.trim() === q) renderSearch(q); }).catch(() => { app.innerHTML = '<div class="mr-err" role="alert">검색 색인을 불러오지 못했어요. 잠시 뒤 다시 검색하세요.</div>'; });
    return;
  }
  const raw = norm(q);
  const terms = raw.split(' ').filter(Boolean);
  // map task words
  const taskWords = { '연장':'extend', '변경':'change', '등록':'reg', '재입국':'reentry', '근무처':'work', '아르바이트':'extra', '자격외':'extra', '시간제':'extra', '부여':'grant', '비자':'visa', '사증':'visa' };
  const codeRx = /^[a-z]-?\d{1,2}(-[a-z0-9]{1,3})*$/i;
  const codeTerm = terms.find(t => codeRx.test(t));
  const visaHits = VISAS.filter(v => {
    const hay = norm(`${v.code} ${v.name} ${v.en} ${v.alias || ''} ${v.d}`);
    return terms.some(t => hay.includes(t));
  });
  // section hits
  const scored = [];
  for (const e of INDEX){
    const info = chapterInfo(e.key);
    const head = norm(`${info.code} ${info.name} ${e.title} ${e.orig}`);
    const body = e.text.toLowerCase();
    let ok = true, score = 0;
    for (const t of terms){
      const inHead = head.includes(t), inBody = body.includes(t);
      const vk = codeRx.test(t) && (info.code.toLowerCase() === t || (info.alias || '').toLowerCase().includes(t));
      if (!(inHead || inBody || vk)){ ok = false; break; }
      score += (vk ? 6 : 0) + (inHead ? 4 : 0) + (inBody ? Math.min(3, body.split(t).length - 1) : 0);
      const tk = taskWords[t];
      if (tk && ((e.src === 's' && SEC[tk] && e.title === SEC[tk].t) || (tk === 'visa' && e.src === 'v'))) score += 5;
    }
    if (ok) scored.push({ e, score });
  }
  scored.sort((a, b) => b.score - a.score);
  const top = scored.slice(0, 60);
  let html = `<div class="results"><div class="crumb"><a href="#home">← 처음으로</a></div><h1>“${esc(q)}” 검색 결과</h1><p class="empty" style="margin:0">${scored.length ? `본문에서 ${scored.length}곳을 찾았어요${scored.length > 60 ? ' (관련도 높은 60곳 표시)' : ''}.` : ''}</p>`;
  if (visaHits.length){
    html += `<div class="rgroup">체류자격</div><div class="cards">` + visaHits.slice(0, 8).map(v => `<a class="card" href="#c-${v.key}"><span class="stamp${/[가-힣]/.test(v.code) || v.code.length > 5 ? ' k' : ''}">${esc(v.code)}</span><span><span class="nm">${esc(v.name)}</span><br><span class="en">${esc(v.en)}</span></span><p>${esc(v.d)}</p></a>`).join('') + `</div>`;
  }
  if (top.length){
    html += `<div class="rgroup">본문</div>`;
    for (const { e } of top){
      const info = chapterInfo(e.key);
      html += `<a class="res" href="#c-${e.key}.${e.src}.${e.i}" data-key="${e.key}" data-src="${e.src}" data-i="${e.i}"><span class="where"><span class="stamp">${esc(info.code)}</span>${esc(info.name)} · ${e.src === 'v' ? '비자(사증) 받기' : '체류 업무'}</span><b>${esc(e.title)}</b><p>${snippet(e.text, terms)}</p></a>`;
    }
  }
  if (!visaHits.length && !top.length){
    html += `<p class="empty">찾는 내용이 없어요. 단어를 줄이거나 다른 말로 찾아보세요. 예: “연장”, “시간제취업”, “F-6”.</p>`;
  }
  html += `</div>`;
  app.innerHTML = html;
  $$('.res').forEach(a => a.addEventListener('click', ev => {
    ev.preventDefault();
    history.pushState(null, '', a.getAttribute('href'));
    renderChapter(a.dataset.key, a.dataset.src, a.dataset.i, { term: terms.filter(t => !codeRx.test(t)).join(' ') || terms[0] });
  }));
}
let st = null;
$('#mr-q').addEventListener('input', e => {
  clearTimeout(st);
  const v = e.target.value.trim();
  st = setTimeout(() => { if (v.length >= 1) renderSearch(v); else route(); }, 220);
});
$('#mr-q').addEventListener('keydown', e => { if (e.key === 'Enter'){ clearTimeout(st); const v = e.target.value.trim(); if (v) renderSearch(v); } });

Promise.all([fetchJson(BASE + 'catalog.json'), fetchJson(BASE + 'editorial.json')]).then(([cat, ed]) => {
  CAT = cat; ED = ed;
  GROUPS = ed.groups; VISAS = ed.statuses; EXTRA_CHAPTERS = ed.extra_chapters; SEC = ed.section_titles;
  TASKS = ed.tasks; QUICK = ed.quick; GLOSSARY = ed.glossary.map(g => [g.term, g.text]);
  GL_SKIP_IDX = GLOSSARY.map((g, i) => ['사증','체류자격','근무처','약호','TOPIK'].includes(g[0]) ? i : -1).filter(i => i >= 0);
  route();
}).catch(err => {
  console.error(err);
  app.innerHTML = '<div class="mr-err" role="alert">매뉴얼 원문을 불러오지 못했어요. 새로고침하거나 공식 PDF를 여세요: <a href="docs/source-manuals/2026-09/visa_manual_260901.pdf">사증발급</a> · <a href="docs/source-manuals/2026-09/stay_manual_260918.pdf">외국인체류</a></div>';
});
})();
