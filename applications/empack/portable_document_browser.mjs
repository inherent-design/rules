// Owner-run shared DocumentCodec comparison. Not a project store or consumer exporter.
import {createRequire}from'node:module';
import{createServer}from'node:http';
import{readFile,writeFile,mkdir}from'node:fs/promises';
import{existsSync,createReadStream}from'node:fs';
import{fileURLToPath}from'node:url';
import{resolve,join}from'node:path';
import{createHash}from'node:crypto';
import assert from'node:assert/strict';
const root=resolve(fileURLToPath(new URL('../..',import.meta.url))),run=resolve(process.argv[2]);assert(run.startsWith(join(root,'applications/evidence/empack-portable-documents-')));
assert(!existsSync(join(run,'browser.json')),'Existing browser capture is immutable; use a new continuation capture.');
const reuse=JSON.parse(await readFile(join(run,'reused-build.json'),'utf8'));const buildRaw=await readFile(join(root,reuse.capture,'build.json'));assert.equal(createHash('sha256').update(buildRaw).digest('hex'),reuse.buildReceiptSha256);const build=JSON.parse(buildRaw),cases=JSON.parse(await readFile(join(run,'cases.json'),'utf8'));
const sdkPath=join(root,'applications/tools/playwright-core-1.64.1/package/package.json'),info=JSON.parse(await readFile(sdkPath,'utf8'));assert.equal(info.version,'1.64.1');const sdk=createRequire(sdkPath)('.');
const sha=b=>createHash('sha256').update(b).digest('hex');
async function fileHash(p){const h=createHash('sha256');for await(const b of createReadStream(p))h.update(b);return h.digest('hex');}
const source=join(root,'applications/empack/portable-core'),files=['host.mjs','worker.mjs','page.mjs','page.html'],bodies=new Map();
await writeFile(join(run,'browser-probe.mjs'),await readFile(fileURLToPath(import.meta.url)));
const sourceHashes={};for(const name of files){const raw=await readFile(name==='page.html'?join(root,'applications/empack/document-portable/page.html'):join(source,name));await writeFile(join(run,'browser-'+name),raw);bodies.set('/'+name,raw);sourceHashes[name]=sha(raw);}bodies.set('/',bodies.get('/page.html'));
const wasm=await readFile(build.wasm.path);assert.equal(sha(wasm),build.wasm.sha256);bodies.set('/core.wasm',wasm);
const requests=[],profiles=[];let context=null,server,origin,error=null;
const receipt={schema:1,kind:'Unchanged actual DocumentCodec/submodules in dedicated browser workers;not full portable engine/project/export qualification',producerSha256:await fileHash(join(run,'browser-probe.mjs')),sourceHashes,wasmSha256:sha(wasm),package:{path:sdkPath,version:info.version,sha256:await fileHash(sdkPath)},requests,profiles,serverClosed:false,node:{path:process.execPath,version:process.version,sha256:await fileHash(process.execPath),rows:[]}};
async function save(){await writeFile(join(run,'browser.json'),JSON.stringify(receipt,null,2)+'\n');}
try{
 const {loadCore}=await import('./portable-core/host.mjs');const core=await loadCore(wasm);receipt.node.imports=core.imports;receipt.node.exports=core.exports;for(const c of cases)receipt.node.rows.push({id:c.id,...core.project(Uint8Array.from(Buffer.from(c.packetHex,'hex')))});await save();
 server=createServer((req,res)=>{const body=bodies.get(req.url);requests.push({method:req.method,path:req.url,status:body?200:404});res.setHeader('cache-control','no-store');res.setHeader('content-security-policy',"default-src 'self';script-src 'self' 'wasm-unsafe-eval';worker-src 'self';connect-src 'self';object-src 'none';base-uri 'none'");if(!body){res.statusCode=404;res.end('Not found');return;}res.setHeader('content-type',req.url.endsWith('.wasm')?'application/wasm':req.url==='/'?'text/html; charset=utf-8':'text/javascript; charset=utf-8');res.end(body);});
 await new Promise(r=>server.listen(0,'127.0.0.1',r));origin='http://127.0.0.1:'+server.address().port;receipt.origin=origin;await save();
 for(const name of['chromium','webkit']){
  const profile=join(build.work,'browser-'+name);await mkdir(profile,{recursive:true});const executable=sdk[name].executablePath();assert(existsSync(executable));
  const row={engine:name,executable,executableSha256:await fileHash(executable),profile,contextClosed:false,rows:[],errors:[]};profiles.push(row);await save();
  context=await sdk[name].launchPersistentContext(profile,{headless:true,viewport:{width:900,height:600}});row.version=context.browser().version();const page=await context.newPage();page.on('pageerror',e=>row.errors.push(e.message));await page.goto(origin);await page.waitForFunction(()=>window.study);
  row.capabilities=await page.evaluate(()=>({secureContext:isSecureContext,wasm:typeof WebAssembly==='object',worker:typeof Worker==='function'}));
  for(const c of cases){
   const measured=await page.evaluate(async hex=>await Promise.race([study.project(hex),new Promise((_,reject)=>setTimeout(()=>reject(Error('Fixture result timeout')),5000))]),c.packetHex);
   row.rows.push({id:c.id,...measured.result});row.imports=measured.imports;row.exports=measured.exports;
  }
  // Closed wire bound is transport refusal, not a successful prior result.
  row.overLimitRefused=await page.evaluate(async()=>{try{await study.project('00'.repeat(65537));return false;}catch{return true;}});
  await page.evaluate(()=>study.close());await context.close();context=null;row.contextClosed=true;await save();
 }
}catch(e){error=e;receipt.error={name:e.name,message:e.message};}
finally{if(context){try{await context.close();receipt.closedOnError=true;}catch(e){receipt.closeError=e.message;}context=null;}if(server){await new Promise(r=>server.close(r));receipt.serverClosed=true;}await save();}
if(error)throw error;
console.log(JSON.stringify({profiles:profiles.map(p=>({engine:p.engine,rows:p.rows.length,closed:p.contextClosed,version:p.version})),serverClosed:receipt.serverClosed}));
