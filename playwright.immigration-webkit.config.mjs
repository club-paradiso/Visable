import { defineConfig } from '@playwright/test';
import base from './playwright.config.mjs';
export default defineConfig({
 ...base,
 testMatch:'**/immigration-checklists.spec.mjs',
 use:{...base.use,launchOptions:{}},
 projects:[
  {name:'webkit-iphone-390',use:{browserName:'webkit',viewport:{width:390,height:844},isMobile:true,hasTouch:true}},
  {name:'webkit-iphone-320',use:{browserName:'webkit',viewport:{width:320,height:568},isMobile:true,hasTouch:true}}
 ]
});
