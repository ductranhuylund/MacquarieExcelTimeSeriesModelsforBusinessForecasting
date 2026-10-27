import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
const root=path.resolve('dist');
assert.ok(fs.existsSync(root),'Run npm run build first.');
function walk(dir){return fs.readdirSync(dir,{withFileTypes:true}).flatMap(e=>e.isDirectory()?walk(path.join(dir,e.name)):[path.join(dir,e.name)]);}
const pages=walk(root).filter(f=>f.endsWith('.html'));
const failures=[];
for(const file of pages){
 const html=fs.readFileSync(file,'utf8');
 const urlPath='/'+path.relative(root,file).replaceAll(path.sep,'/').replace(/index\.html$/,'');
 const origin=new URL(urlPath,'https://ct.invalid');
 if((html.match(/<h1(?:\s|>)/g)||[]).length!==1)failures.push(`${urlPath}: expected one main heading`);
 if(!html.includes('lang="vi"'))failures.push(`${urlPath}: missing Vietnamese language`);
 if(!html.includes('name="description"'))failures.push(`${urlPath}: missing description`);
 for(const match of html.matchAll(/(?:href|src)="([^"]+)"/g)){
  const value=match[1];
  if(value==='#'){failures.push(`${urlPath}: placeholder link`);continue;}
  if(/^(data:|mailto:|tel:|https?:\/\/)/.test(value))continue;
  const target=new URL(value,origin);
  let dest=path.join(root,decodeURIComponent(target.pathname));
  if(target.pathname.endsWith('/'))dest=path.join(dest,'index.html');
  if(!fs.existsSync(dest)){failures.push(`${urlPath}: missing resource ${value}`);continue;}
  if(target.hash && dest.endsWith('.html')){
   const body=fs.readFileSync(dest,'utf8');
   const anchor=decodeURIComponent(target.hash.slice(1));
   if(!body.includes(`id="${anchor}"`))failures.push(`${urlPath}: missing anchor ${value}`);
  }
 }
}
assert.equal(failures.length,0,failures.join('\n'));
console.log(`PASS: ${pages.length} pages; internal navigation, anchors, assets, page headings and metadata.`);
