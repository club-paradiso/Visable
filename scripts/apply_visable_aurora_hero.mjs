#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

const root = process.cwd();
const indexPath = path.join(root, 'index.html');
const html = fs.readFileSync(indexPath, 'utf8');
let next = html;

const cssHref = 'assets/css/visable-aurora-hero.css?v=20260629';
const jsSrc = 'assets/js/visable-aurora-hero.js?v=20260629';

if (!next.includes(cssHref)) {
  next = next.replace(
    /(<\/head>)/i,
    `    <link id="visableAuroraHeroStylesheet" rel="stylesheet" href="${cssHref}">\n$1`
  );
}

if (!next.includes(jsSrc)) {
  next = next.replace(
    /(<\/body>)/i,
    `    <script src="${jsSrc}" defer></script>\n$1`
  );
}

if (next === html) {
  console.log('Visable Aurora Mesh assets are already linked.');
  process.exit(0);
}

fs.writeFileSync(indexPath, next, 'utf8');
console.log('Linked Visable Aurora Mesh CSS/JS in index.html');
