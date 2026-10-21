import fs from 'node:fs';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const read=p=>JSON.parse(fs.readFileSync(path.join(root,p),'utf8'));
const expected={extension:224,change:251,registration:172};
const all=new Map();
for (const [kind,count] of Object.entries(expected)) {
 const data=read('data/immigration-checklists/'+kind+'-202609.json');
 assert.equal(data.schema_version,1);
 assert.equal(data.procedure,kind);
 assert.equal(data.row_count,count);
 assert.equal(data.items.length,count);
 const unique=new Set();
 for (const item of data.items) {
  assert.match(item.id,new RegExp('^'+kind[0]+'-\\d{4}$'));
  assert.ok(!unique.has(item.id),'duplicate ID: '+item.id);unique.add(item.id);
  assert.ok(item.status_code&&item.scenario,'identity missing: '+item.id);
  assert.equal(item.review_state,'COMPILED_NEEDS_REVIEW');
  for(const key of ['required_text','conditional_text','application_text','note_text'])
    assert.equal(typeof item[key],'string',item.id+' field '+key);
  assert.ok(item.source_line>=1&&item.source_line<=859);
  assert.ok(!all.has(item.id),'global ID collision: '+item.id);all.set(item.id,item);
 }
}
assert.equal(all.size,647);
const notes=read('data/immigration-checklists/reference-notes-202609.json');
assert.equal(notes.proxy_candidates.length,24);
assert.ok(notes.proxy_principles.length>=10);
const practice=read('data/local-practice-202609.json');
const officeIds=new Set(practice.offices.map(o=>o.id));
const ledger=read('data/immigration-checklists/local-overrides.json');
assert.ok(Array.isArray(ledger.overrides));
for (const o of ledger.overrides) {
 assert.ok(all.has(o.item_id),'unknown item '+o.item_id);
 assert.ok(officeIds.has(o.office_id),'unknown office '+o.office_id);
 assert.equal(all.get(o.item_id).id.slice(0,1),o.procedure.slice(0,1));
 assert.ok(['DRAFT','SUBMITTED','UNDER_REVIEW','OFFICIAL_LOCAL_GUIDANCE','VERIFIED_LOCAL_PRACTICE','CONFLICTING_REPORTS','STALE_REPORT'].includes(o.review_state));
 if(o.review_state==='OFFICIAL_LOCAL_GUIDANCE')
   assert.ok(o.evidence?.some(e=>e.type==='office_notice'&&/^https:\/\//.test(e.url)),'official local evidence needed');
 if(o.review_state==='VERIFIED_LOCAL_PRACTICE')
   assert.ok(o.evidence?.some(e=>e.type==='corroborated_reports'&&e.count>=2),'corroboration needed');
 assert.equal(typeof o.changes,'object');
}
const html=fs.readFileSync(path.join(root,'immigration-checklists.html'),'utf8');
for (const s of ['id="cards"','id="office"','id="edit-dialog"','assets/js/immigration-checklists.js'])assert.ok(html.includes(s),s);
const js=fs.readFileSync(path.join(root,'assets/js/immigration-checklists.js'),'utf8');
for (const s of ['OFFICIAL_LOCAL_GUIDANCE','VERIFIED_LOCAL_PRACTICE','localStorage','exportOffice','approvedOverride'])assert.ok(js.includes(s),s);
console.log('Immigration checklist validation passed: '+all.size+' cases / '+officeIds.size+' offices');
