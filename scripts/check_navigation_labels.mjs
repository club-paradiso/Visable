import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import {JSDOM, VirtualConsole} from 'jsdom';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const locales=['ko','en','zh-CN','zh-TW','ja','vi','tl','id','ru','fr','es','ar','de','tr','uk'];
const source=p=>fs.readFileSync(path.join(root,p),'utf8');
const json=p=>JSON.parse(source(p));
const wait=()=>new Promise(r=>setTimeout(r,15));
function page(name) {
 const dom=new JSDOM(source(name),{url:'https://test.invalid/'+name,runScripts:'outside-only',pretendToBeVisual:true,virtualConsole:new VirtualConsole()});
 const w=dom.window;w.scrollTo=()=>{};w.HTMLElement.prototype.scrollIntoView=function(){};
 w.matchMedia=()=>({matches:false,addListener(){},removeListener(){},addEventListener(){},removeEventListener(){}});
 w.HTMLCanvasElement.prototype.getContext=()=>({measureText:t=>({width:t.length*8})});
 w.fetch=async u=>{if(String(u).includes('/api/'))throw Error('offline');return {ok:true,json:async()=>json(String(u))};};
 return {dom,w};
}
const forms=page('form-helper.html');
forms.w.eval(source('assets/js/zh-traditional.js'));
forms.w.eval(source('assets/js/form-engine.js'));
forms.w.eval(source('assets/js/form-helper-app.js'));
for(let i=0;i<100&&!forms.w.document.body.classList.contains('fh-ready');i++)await wait();
assert.ok(forms.w.document.body.classList.contains('fh-ready'),'form helper booted');
for(const locale of locales){
 forms.w.VisableFormHelper.setLang(locale);await wait();
 const pack=json('data/i18n/'+(locale==='zh-TW'?'zh-CN':locale)+'.json');
 const expected=locale==='zh-TW'?forms.w.ParadisoZhT.convert(pack.skipToContent):pack.skipToContent;
 const skip=forms.w.document.querySelector('#fhSkip');
 assert.equal(skip.textContent,expected,locale+' describes skip target');
 assert.equal(skip.getAttribute('href'),'#fhMain');
 const homeLabel=locale==='zh-TW'?forms.w.ParadisoZhT.convert(pack.fh.back):pack.fh.back;
 assert.equal(forms.w.document.querySelector('#fhBack').getAttribute('aria-label'),homeLabel,locale+' home label kept'); // icon link: label lives in aria-label (ab1d076)
}
forms.dom.window.close();
const lists=page('immigration-checklists.html');
lists.w.eval(source('assets/js/zh-traditional.js'));
lists.w.eval(source('assets/js/visable-i18n.js'));
lists.w.eval(source('assets/js/immigration-checklists.js'));
for(let i=0;i<100&&lists.w.document.querySelector('#office').options.length<2;i++)await wait();
for(const locale of locales){
 await lists.w.VisableI18n.setLocale(locale);lists.w.__VISABLE_INTERNALS.updateLanguage(locale);
 const feedback=lists.w.document.querySelector('#open-feedback-btn');
 assert.equal(feedback.textContent.trim(),lists.w.VisableI18n.t('navFeedback'),locale+' feedback action named correctly');
 assert.equal(feedback.hasAttribute('href'),false,'button is not a navigation anchor');
 const form=lists.w.document.querySelector('a.header-link');
 assert.equal(form.querySelector('span').textContent,lists.w.VisableI18n.t('navFormHelper'),locale+' form label');
 assert.equal(form.getAttribute('href'),'form-helper.html'+(locale==='ko'?'':'?lang='+encodeURIComponent(locale)),locale+' form destination');
}
lists.dom.window.close();
console.log('Navigation labels: form skip/home and checklist feedback/form destinations passed in all 15 locales.');
