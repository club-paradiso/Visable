/* Visable checklists: sourced snapshots + non-publishing editing drafts. */
(function () {
'use strict';
var base = 'data/immigration-checklists/';
var N_KEY = 'visable.checklists.nationalDrafts.v1';
var O_KEY = 'visable.checklists.officeDrafts.v1';
var state = { procedure:'extension', query:'', office:'', limit:30, datasets:{}, offices:[], overrides:[], nationalDrafts:{}, officeDrafts:{}, notes:null, selected:null };
var $ = function (id) { return document.getElementById(id); };
var FIELDS = ['required_text','conditional_text','application_text','note_text'];
function element(tag, cls, text) { var e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=String(text);return e; }
function text(node, value) { node.textContent = value == null ? '' : String(value); return node; }
function append(parent, children) { children.forEach(function (x) { if(x)parent.appendChild(x); }); return parent; }
function safeRead(key) { try { var value=JSON.parse(localStorage.getItem(key)||'{}');return value&&typeof value==='object'&&!Array.isArray(value)?value:{}; } catch(e) {return {};} }
function safeSave(key,val) { try { localStorage.setItem(key,JSON.stringify(val)); }catch(e){window.alert('이 기기에는 저장할 수 없습니다. JSON을 먼저 내려받으세요.');} }
function normalize(s) { return String(s||'').normalize('NFKC').toLocaleLowerCase('ko').replace(/\s+/g,''); }
function meta(item) {return [item.status_code,item.scenario,item.required_text,item.conditional_text,item.note_text,item.application_text].join(' ');}
function note(parent,title,value,cls) {
 if(!value||value==='별도 기재 없음')return;
 var block=element('section','doc-block '+(cls||''));
 var h=element('h4','',title);block.appendChild(h);
 if(title==='기본·명시 서류'&&String(value).includes('; ')){
  var ul=element('ul','doc-list');String(value).split(/;\s*/).map(function(v){return v.trim();}).filter(Boolean).forEach(function(v){ul.appendChild(element('li','',v));});block.appendChild(ul);
 }else{block.appendChild(element('p','',value));}
 parent.appendChild(block);
}
function getDataset() { return state.datasets[state.procedure]; }
function activeRow(original) {
 var patch=state.nationalDrafts[original.id]||null;
 if(!patch)return original;
 var copy=Object.assign({},original);FIELDS.forEach(function(k){if(typeof patch[k]==='string')copy[k]=patch[k];});
 return copy;
}
function approvedOverride(entry) {
 if(!entry||!entry.office_id||!entry.item_id)return false;
 if(!['OFFICIAL_LOCAL_GUIDANCE','VERIFIED_LOCAL_PRACTICE'].includes(entry.review_state))return false;
 if(!entry.evidence||!Array.isArray(entry.evidence)||entry.evidence.length===0)return false;
 if(entry.review_state==='OFFICIAL_LOCAL_GUIDANCE'&&!entry.evidence.some(function(e){return e.type==='office_notice'&&e.url;}))return false;
 if(entry.review_state==='VERIFIED_LOCAL_PRACTICE'&&!entry.evidence.some(function(e){return e.type==='corroborated_reports'&&Number(e.count)>=2;}))return false;
 if(entry.expires_on&&!/^\d{4}-\d{2}-\d{2}$/.test(entry.expires_on))return false;
 if(entry.expires_on&&entry.expires_on<new Date().toISOString().slice(0,10))return false;
 return true;
}
function officeName(id) {var p=state.offices.find(function(x){return x.id===id;});return p?p.name_ko:id;}
function localNotes(item) {
 var found=state.overrides.filter(function(o){return o.item_id===item.id&&o.office_id===state.office&&approvedOverride(o);});
 var draft=state.officeDrafts[item.id+'@'+state.office];if(draft)found.push(Object.assign({review_state:'DRAFT',office_id:state.office},draft));
 return found;
}
function officeCallout(entry) {
 var card=element('div','office-specific'),head=element('h4','',entry.review_state==='DRAFT'?'관서별 편집 초안 · 공개되지 않음':entry.review_state==='OFFICIAL_LOCAL_GUIDANCE'?'관서 공식 안내 · 전국 기준과 별도':'검증된 관서 실무 · 전국 기준과 별도');
 append(card,[head,element('p','',officeName(entry.office_id))]);
 FIELDS.forEach(function(k){if(entry.changes&&typeof entry.changes[k]==='string'&&entry.changes[k].trim())note(card,({'required_text':'관서별 요청 서류','conditional_text':'관서별 조건·생략','application_text':'관서별 본인·대리 안내','note_text':'관서별 추가 정보'})[k],entry.changes[k]);});
 if(entry.evidence&&entry.evidence.length)append(card,[element('p','evidence','근거: '+entry.evidence.map(function(e){return e.url||e.type;}).join(' · '))]);
 if(entry.editor_note)append(card,[element('p','evidence','검토 메모: '+entry.editor_note)]);
 return card;
}
function card(original) {
 var item=activeRow(original),card=element('article','doc-card');
 var head=element('div','card-head'),left=element('div'),code=element('span','code-pill',item.status_code);
 append(left,[code,element('h3','',item.scenario)]);
 var right=element('div');append(right,[element('span','chip',state.nationalDrafts[item.id]?'로컬 문구 초안':'원문 편집본')]);
 var btn=element('button','outline-button','워딩 수정');btn.type='button';btn.setAttribute('aria-label',item.status_code+' '+item.scenario+' 문구 편집');btn.addEventListener('click',function(){openEditor(original);});right.appendChild(btn);
 append(head,[left,right]);card.appendChild(head);
 var body=element('div','card-body');
 note(body,'기본·명시 서류',item.required_text);
 note(body,'해당자·대체·생략 조건',item.conditional_text,'conditional');
 note(body,'본인·대리 신청',item.application_text|| (state.procedure==='registration' ? '신규 외국인등록 및 국내거소신고는 등록대상자의 연령·생체정보 등록 여부에 따라 본인 출석이 필요할 수 있습니다. 대리 접수 가능 여부와 생체정보 제공 절차는 별도로 확인해야 합니다.' : ''));
 note(body,'비고 및 원문 주의',item.note_text);
 card.appendChild(body);
 if(state.office)localNotes(item).forEach(function(o){card.appendChild(officeCallout(o));});
 var tail=element('div','card-tail');
 append(tail,[element('span','','원문 편집본 '+item.source_line+'행'),element('span','','·'),element('span','',item.source_section||''),element('span','','·'),element('span','','검토 필요')]);
 card.appendChild(tail);
 return card;
}
function filtered() {
 var data=getDataset();if(!data||!Array.isArray(data.items))return [];
 var q=normalize(state.query);
 return q?data.items.filter(function(i){return normalize(meta(activeRow(i))).includes(q);}):data.items;
}
function render() {
 var results=filtered(),target=$('cards');target.setAttribute('aria-busy','true');
 var frag=document.createDocumentFragment();
 if(!results.length){var empty=element('div','empty');append(empty,[element('strong','','결과를 찾지 못했어요.'),element('p','','체류자격 코드나 서류명을 짧게 입력하거나 검색을 초기화해 보세요.')]);frag.appendChild(empty);}
 else results.slice(0,state.limit).forEach(function(i){frag.appendChild(card(i));});
 target.replaceChildren(frag);target.setAttribute('aria-busy','false');
 $('count').textContent=results.length+'건의 상황별 항목'+(state.query?' 검색됨':'')+(state.office?' · '+officeName(state.office)+' 선택 (검증된 지역 차이만 표시)':'');
 var more=$('show-more');more.hidden=results.length<=state.limit;if(!more.hidden)more.textContent='더 보기 ('+(results.length-state.limit)+'건 남음) ↓';
 $('export-drafts').hidden=!Object.keys(state.nationalDrafts).some(function(id){return getDataset().items.some(function(i){return i.id===id;});});
 $('export-office-drafts').hidden=!Object.keys(state.officeDrafts).length;
}
function renderNotes(){
 var parent=$('common-notes');parent.replaceChildren();
 (state.notes&&state.notes.proxy_principles||[]).slice(0,12).forEach(function(n){append(parent,[element('dl','',undefined)]);var dl=parent.lastElementChild;append(dl,[element('dt','',n.topic),element('dd','',n.guidance)]);});
}
function exportFile(name,value) {
 var blob=new Blob([JSON.stringify(value,null,2)+'\n'],{type:'application/json;charset=utf-8'});
 var url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;document.body.appendChild(a);a.click();a.remove();setTimeout(function(){URL.revokeObjectURL(url);},3000);
}
function exportNational(){
 var d=JSON.parse(JSON.stringify(getDataset()));
 var edited=0;d.items.forEach(function(item){var p=state.nationalDrafts[item.id];if(!p)return;FIELDS.forEach(function(k){if(typeof p[k]==='string')item[k]=p[k];});item.editor_note=p.editor_note||'';item.curation_review='DRAFT_NEEDS_HUMAN_VERIFICATION';edited++;});
 if(!edited)return;d.editor_export={exported_at:new Date().toISOString(),changed_rows:edited,warning:'초안입니다. 원문 검증 및 GitHub 코드 리뷰 후 적용하세요.'};
 exportFile(state.procedure+'-202609.json',d);
}
function exportOffice(){
 var list=Object.keys(state.officeDrafts).sort().map(function(k){var o=state.officeDrafts[k];return {id:o.id,office_id:o.office_id,item_id:o.item_id,procedure:o.procedure,review_state:'DRAFT',changes:o.changes,evidence:o.evidence||[],editor_note:o.editor_note||'',edited_at:o.edited_at};});
 exportFile('local-overrides.draft.json',{schema_version:1,policy:'DRAFT entries are never rendered publicly. Verification and review state promotion required.',overrides:list});
}
function openEditor(item){
 state.selected=item;var row=activeRow(item);
 var dialog=$('edit-dialog'),form=$('edit-form');form.reset();
 $('edit-context').textContent=item.status_code+' · '+item.scenario+' · '+item.id;
 $('edit-scope').value='national';
 FIELDS.forEach(function(k){form.elements.namedItem(k).value=row[k]||'';});
 form.elements.namedItem('editor_note').value=(state.nationalDrafts[item.id]||{}).editor_note||'';
 toggleScope();
 if(typeof dialog.showModal==='function')dialog.showModal();else dialog.setAttribute('open','');
}
function toggleScope(){
 var national=$('edit-scope').value==='national',item=state.selected,form=$('edit-form');
 $('edit-office-wrap').hidden=national;$('edit-evidence-wrap').hidden=national;
 if(national){
 var row=activeRow(item);FIELDS.forEach(function(k){form.elements.namedItem(k).value=row[k]||'';});
 form.elements.namedItem('editor_note').value=(state.nationalDrafts[item.id]||{}).editor_note||'';
 }else{
 if(state.office)$('edit-office').value=state.office;
 var patch=state.officeDrafts[item.id+'@'+$('edit-office').value]||null;
 FIELDS.forEach(function(k){form.elements.namedItem(k).value=patch&&patch.changes[k]||'';});
 form.elements.namedItem('editor_note').value=patch&&patch.editor_note||'';
 $('edit-evidence').value=patch&&patch.evidence?.[0]?.url||'';
 }
}
function saveDraft(e){
 e.preventDefault();var item=state.selected;if(!item)return;
 var form=$('edit-form'),values={};FIELDS.forEach(function(k){values[k]=String(form.elements.namedItem(k).value||'').trim();});
 var noteText=String(form.elements.namedItem('editor_note').value||'').trim();
 if(!noteText){window.alert('수정 근거·검토 메모가 필요합니다.');return;}
 var now=new Date().toISOString();
 if($('edit-scope').value==='national'){
 if(!values.required_text){window.alert('기본·명시 서류는 빈 값으로 저장하지 않습니다.');return;}
 state.nationalDrafts[item.id]=Object.assign(values,{editor_note:noteText,edited_at:now});safeSave(N_KEY,state.nationalDrafts);
 }else{
 var office=$('edit-office').value;if(!office){window.alert('관할 출입국관서를 선택해 주세요.');return;}
 var key=item.id+'@'+office,ev=$('edit-evidence').value.trim();
 if(ev&&!/^https:\/\//i.test(ev)){window.alert('근거 주소는 HTTPS 링크를 입력해 주세요.');return;}
 state.officeDrafts[key]={id:'draft-'+item.id+'-'+office,office_id:office,item_id:item.id,procedure:state.procedure,review_state:'DRAFT',changes:values,evidence:ev?[{type:'office_notice_candidate',url:ev}]:[],editor_note:noteText,edited_at:now};
 safeSave(O_KEY,state.officeDrafts);
 }
 if(typeof $('edit-dialog').close==='function')$('edit-dialog').close();else $('edit-dialog').removeAttribute('open');
 render();
}
function validateData(data,type){
 if(!data||data.procedure!==type||!Array.isArray(data.items))throw Error(type+' 데이터 구조를 확인할 수 없습니다.');
 var seen=new Set();
 for(var item of data.items){if(!item.id||!item.status_code||seen.has(item.id))throw Error(type+' 데이터 ID 중복 또는 누락');seen.add(item.id);}
 var count={extension:224,change:251,registration:172}[type];if(data.items.length!==count)throw Error(type+' 행 수 불일치: '+data.items.length);
}
async function load(){
 try{
 var files=['extension-202609.json','change-202609.json','registration-202609.json','reference-notes-202609.json','local-overrides.json'];
 var urls=files.map(function(f){return base+f;});urls.push('data/local-practice-202609.json');
 var response=await Promise.all(urls.map(function(u){return fetch(u,{cache:'no-cache'}).then(function(r){if(!r.ok)throw Error('HTTP '+r.status+': '+u);return r.json();});}));
 ['extension','change','registration'].forEach(function(t,i){validateData(response[i],t);state.datasets[t]=response[i];});
 state.notes=response[3];state.overrides=Array.isArray(response[4].overrides)?response[4].overrides:[];
 state.offices=Array.isArray(response[5].offices)?response[5].offices:[];
 var officeSelect=$('office'),editorOffice=$('edit-office');
 state.offices.forEach(function(o){[officeSelect,editorOffice].forEach(function(select){var opt=document.createElement('option');opt.value=o.id;opt.textContent=o.name_ko;select.appendChild(opt);});});
 state.nationalDrafts=safeRead(N_KEY);state.officeDrafts=safeRead(O_KEY);
 renderNotes();render();
 }catch(err){
 var cards=$('cards');cards.replaceChildren();var div=element('div','empty');append(div,[element('strong','','서류 데이터를 가져오지 못했어요.'),element('p','',err.message),element('p','','연결을 확인하고 페이지를 새로고침해 주세요.')]);cards.appendChild(div);cards.setAttribute('aria-busy','false');$('count').textContent='불러오기 실패';
 }
}
document.querySelectorAll('[name="procedure"]').forEach(function(input){input.addEventListener('change',function(){if(!input.checked)return;state.procedure=input.value;state.limit=30;render();});});
$('query').addEventListener('input',function(e){state.query=e.target.value;state.limit=30;render();});
$('office').addEventListener('change',function(e){state.office=e.target.value;state.limit=30;render();});
$('reset').addEventListener('click',function(){state.query='';state.office='';state.procedure='extension';state.limit=30;$('query').value='';$('office').value='';document.querySelector('[name="procedure"][value="extension"]').checked=true;render();$('query').focus();});
$('show-more').addEventListener('click',function(){state.limit+=30;render();});
$('draft-toggle').addEventListener('click',function(){var p=$('draft-info');p.hidden=!p.hidden;this.setAttribute('aria-expanded',String(!p.hidden));if(!p.hidden)p.scrollIntoView({block:'nearest'});});
$('edit-scope').addEventListener('change',toggleScope);
$('edit-office').addEventListener('change',toggleScope);
$('edit-cancel').addEventListener('click',function(){if(typeof $('edit-dialog').close==='function')$('edit-dialog').close();else $('edit-dialog').removeAttribute('open');});
$('edit-form').addEventListener('submit',saveDraft);
$('export-drafts').addEventListener('click',exportNational);
$('export-office-drafts').addEventListener('click',exportOffice);
load();
})();
