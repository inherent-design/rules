// Owner-run independent read of the completed cohort, followed by a CSS-only visual check.
import {readFile,writeFile} from 'node:fs/promises';
import {createServer} from 'node:http';
import {createRequire} from 'node:module';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {resolve,join} from 'node:path';
import assert from 'node:assert/strict';
const root=resolve(fileURLToPath(new URL('../..',import.meta.url))),run=resolve(process.argv[2]);
assert(run.startsWith(join(root,'applications/evidence/empack-joined-flow-')));
const browser=JSON.parse(await readFile(join(run,'browser.json'))),native=JSON.parse(await readFile(join(run,'native.json')));
const build=JSON.parse(await readFile(join(root,native.buildCapture,'build.json'))),sha=b=>createHash('sha256').update(b).digest('hex');
try{await readFile(join(run,'backend-probe.json'));throw Error('Capture already exists');}catch(e){if(e.code!=='ENOENT')throw e;}
const sdkPath=join(root,'applications/tools/playwright-core-1.64.1/package/package.json'),sdk=createRequire(sdkPath)('.');
assert.equal(JSON.parse(await readFile(sdkPath)).version,'1.64.1');
const bodies=new Map([['/probe',Buffer.from('<!doctype html><meta charset="utf-8"><title>Independent storage read</title>')]]),hashes={};
await writeFile(join(run,'backend-probe.mjs'),await readFile(fileURLToPath(import.meta.url)));
for(const name of ['transport.mjs','store.mjs','worker.mjs','page.mjs','page.html','style.css']){
 const b=await readFile(join(root,'applications/empack/joined-study',name));bodies.set('/'+name,b);hashes[name]=sha(b);await writeFile(join(run,'probe-'+name),b);
}
for(const name of ['transport.mjs','store.mjs','worker.mjs','page.mjs'])assert.equal(hashes[name],browser.sourceHashes[name]);
bodies.set('/',bodies.get('/page.html'));
for(const name of ['joined.js','joined_bg.wasm'])bodies.set('/'+name,await readFile(join(build.work,'pkg',name)));
const rows=[],requests=[],record={schema:1,scope:'Independent IDB/OPFS reader; same profile/origin; original domain code; external-CSS follow-up only',producerSha256:sha(await readFile(join(run,'backend-probe.mjs'))),hashes,origin:browser.origin,rows,requests};
let context=null,server;
async function backend(page){return page.evaluate(async()=>{
 const db=await new Promise((resolve,reject)=>{const r=indexedDB.open('rules-empack-joined-study',1);r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);});
 const values=await new Promise((resolve,reject)=>{const tx=db.transaction(['roots','history'],'readonly');let root,history;const a=tx.objectStore('roots').get('root'),b=tx.objectStore('history').getAll();a.onsuccess=()=>{root=a.result;};b.onsuccess=()=>{history=b.result;};tx.oncomplete=()=>resolve({root,history});tx.onabort=()=>reject(tx.error);});db.close();
 const directory=await navigator.storage.getDirectory(),objects=[];
 for await(const [name,handle] of directory.entries()){if(handle.kind!=='file')throw Error('Unexpected directory');const f=await handle.getFile(),bytes=await f.arrayBuffer(),digest=[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(b=>b.toString(16).padStart(2,'0')).join('');objects.push({name,bytes:f.size,sha256:digest});}
 return {...values,objects:objects.sort((a,b)=>a.name.localeCompare(b.name))};
});}
try{
 const u=new URL(browser.origin);assert.equal(u.hostname,'127.0.0.1');
 server=createServer((req,res)=>{const b=bodies.get(req.url);requests.push(req.url);res.setHeader('cache-control','no-store');res.setHeader('content-security-policy',"default-src 'self';script-src 'self' 'wasm-unsafe-eval';worker-src 'self';connect-src 'self';object-src 'none';base-uri 'none'");res.setHeader('content-type',req.url==='/'||req.url==='/probe'?'text/html; charset=utf-8':req.url.endsWith('.css')?'text/css; charset=utf-8':req.url.endsWith('.wasm')?'application/wasm':'text/javascript; charset=utf-8');res.statusCode=b?200:404;res.end(b??'Not found');});
 await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(Number(u.port),'127.0.0.1',resolve);});
 for(const original of browser.profiles){
  context=await sdk[original.engine].launchPersistentContext(original.profile,{headless:true,viewport:{width:1050,height:1100}});const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(browser.origin+'/probe');const before=await backend(page);assert.deepEqual({root:before.root,history:before.history},original.backend);
  const snapshots=before.history.map(h=>JSON.parse(h.wire));const refs=new Map(snapshots.flatMap(s=>s.draft.entries.filter(e=>e.asset).map(e=>[e.asset.id,e.asset])));
  assert.equal(before.objects.length,2);for(const [id,ref]of refs){const obj=before.objects.find(o=>o.name==='source-'+id);assert(obj);assert.equal(obj.bytes,ref.bytes);assert.equal(obj.sha256,ref.sha256);}
  await page.goto(browser.origin);await page.waitForFunction(()=>window.study?.state.saved?.revision==='3');
  const visual=await page.evaluate(()=>({font:getComputedStyle(document.body).fontFamily,maxWidth:getComputedStyle(document.body).maxWidth,status:document.querySelector('#status').textContent,dirty:study.state.current.image!==study.state.saved.image}));assert.equal(visual.maxWidth,'960px');assert(visual.font.includes('system-ui'));assert.equal(visual.dirty,false);
  const screenshot=join(native.work,original.engine+'-joined-styled.png');await page.screenshot({path:screenshot,fullPage:true});await page.evaluate(()=>study.stop());await page.goto(browser.origin+'/probe');const after=await backend(page);assert.deepEqual(after,before);assert.deepEqual(errors,[]);
  rows.push({engine:original.engine,version:context.browser().version(),before,after,visual,screenshot,screenshotSha256:sha(await readFile(screenshot)),errors});await context.close();context=null;
 }
 record.complete=true;
}catch(e){record.error={name:e.name,message:e.message,stack:e.stack};throw e;}
finally{if(context)await context.close();if(server){await new Promise(r=>server.close(r));record.serverClosed=true;}await writeFile(join(run,'backend-probe.json'),JSON.stringify(record,null,2)+'\n');}
console.log(JSON.stringify({engines:rows.map(r=>r.engine),objects:rows.map(r=>r.before.objects.length),unchanged:true,serverClosed:record.serverClosed}));
