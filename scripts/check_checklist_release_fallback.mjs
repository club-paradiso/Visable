import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { JSDOM, VirtualConsole } from 'jsdom';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const read = p => JSON.parse(fs.readFileSync(path.join(root,p),'utf8'));
const baseline = Object.fromEntries(['extension','change','registration'].map(t => [t,read('data/immigration-checklists/'+t+'-202609.json')]));
const copy = x => JSON.parse(JSON.stringify(x));
async function boot(payload, {preview=false, locale='ko',offline=false}={}) {
 const errors=[]; const vc=new VirtualConsole(); vc.on('jsdomError', e=>errors.push(e.message));
 const dom=new JSDOM(fs.readFileSync(path.join(root,'immigration-checklists.html'),'utf8'),{url:'https://test.invalid/immigration-checklists.html'+(preview?'?preview_release=test':''),runScripts:'outside-only',virtualConsole:vc,pretendToBeVisual:true});
 const w=dom.window; w.scrollTo=()=>{};w.HTMLElement.prototype.scrollIntoView=function(){};
 w.VisableI18n={getLocale:()=>locale,t:(_k,_v,f)=>f||_k,applyRTL:()=>{}};
 w.VisableBackend={url:p=>'https://test.invalid'+p};
 w.fetch=async u=>{const s=String(u);if(s.includes('/api/checklists/')) {if(offline)throw Error('offline');return {ok:true,json:async()=>copy(payload)};}return {ok:true,json:async()=>read(s)};};
 w.eval(fs.readFileSync(path.join(root,'assets/js/immigration-checklists.js'),'utf8'));
 for(let i=0;i<100;i++){await new Promise(r=>setTimeout(r,5));if(w.document.querySelector('#office').options.length>1)break;}
 const st=w.__VISABLE_INTERNALS.state;
 return {dom,w,st,errors,counts:()=>Object.fromEntries(Object.entries(st.datasets).map(([k,v])=>[k,v.items.length]))};
}
const cases=[];
cases.push(['empty active release', {status:'active',total_items:0,...Object.fromEntries(Object.keys(baseline).map(t=>[t,{procedure:t,row_count:0,items:[]}]))}, {extension:224,change:251,registration:172}]);
const valid=copy(baseline);valid.extension.items[0].note_text='TEST RELEASE NOTE';
cases.push(['complete valid release',valid,{extension:224,change:251,registration:172}]);
const badCount=copy(valid);badCount.extension.items.pop();cases.push(['partial release stays atomic',badCount,{extension:224,change:251,registration:172}]);
const duplicate=copy(valid);duplicate.change.items[1].id=duplicate.change.items[0].id;cases.push(['duplicate id release',duplicate,{extension:224,change:251,registration:172}]);
const missing=copy(valid);delete missing.registration;cases.push(['missing procedure',missing,{extension:224,change:251,registration:172}]);
for(const [name,payload,expected] of cases){
 const app=await boot(payload);console.log(name,app.counts());assert.deepEqual(app.counts(),expected,name);
 const actual=app.st.datasets.extension.items[0].note_text;
 assert.equal(actual,name==='complete valid release'?'TEST RELEASE NOTE':baseline.extension.items[0].note_text,name+' content atomicity');
 assert.ok(app.w.document.querySelector('#count').textContent.includes('224'),name+' rendered count');
 assert.ok(app.w.document.querySelector('#guided-discovery').textContent.includes('D-2'),name+' status choices');
 app.dom.window.close();
}
for(const [name,opts] of [['network failure',{offline:true}],['empty preview',{preview:true}]]){
 const app=await boot(cases[0][1],opts);assert.deepEqual(app.counts(),{extension:224,change:251,registration:172},name);app.dom.window.close();console.log(name,'PASS');
}
console.log('Checklist release fallback: 7 DOM integration scenarios passed. No network or live AI.');
