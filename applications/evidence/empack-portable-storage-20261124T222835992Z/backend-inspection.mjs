// Read the owned origin's raw IDB/OPFS after the completed study. No app import.
import {createRequire} from 'node:module';
import {createServer} from 'node:http';
import {readFile,writeFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {resolve,join} from 'node:path';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
const root=resolve(fileURLToPath(new URL('../..',import.meta.url))),run=resolve(process.argv[2]??'');
assert.equal(resolve(run,'..'),join(root,'applications/evidence'));assert(run.split('/').at(-1).startsWith('empack-portable-storage-'));
const originalBytes=await readFile(join(run,'receipt.json')),original=JSON.parse(originalBytes);assert(original.serverClosed&&!original.error);
const origin=new URL(original.origin);assert.equal(origin.hostname,'127.0.0.1');assert.equal(origin.protocol,'http:');assert.equal(origin.pathname,'/');
const output=join(run,'backend-inspection.json');
try{await readFile(output);throw Error('Inspection exists;review before a repeat.');}catch(e){if(e.code!=='ENOENT')throw e;}
const sdk=createRequire(original.package.path)('.');const sha=b=>createHash('sha256').update(b).digest('hex');
assert.equal(sha(await readFile(original.package.path)),original.package.sha256);
const rows=[];let context,error;
const server=createServer((req,res)=>{res.setHeader('cache-control','no-store');res.setHeader('content-type','text/html');res.end('<!doctype html><title>Owned raw storage inspection</title>');});
await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(Number(origin.port),'127.0.0.1',resolve);});
try{
  for(const profile of original.profiles){
    context=await sdk[profile.engine].launchPersistentContext(join(run,'work',profile.engine,'profile'),{headless:true});const page=await context.newPage();await page.goto(original.origin);
    const measured=await page.evaluate(async()=>{
      const db=await new Promise((resolve,reject)=>{const r=indexedDB.open('rules-empack-draft-study',1);r.onupgradeneeded=()=>{r.transaction.abort();reject(Error('Expected database absent'));};r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);});
      const record=await new Promise((resolve,reject)=>{let value;const tx=db.transaction('projects','readonly');tx.objectStore('projects').get('root').onsuccess=e=>value=e.target.result;tx.oncomplete=()=>resolve(value);tx.onabort=()=>reject(tx.error);});db.close();
      const root=await navigator.storage.getDirectory();const assets=[];
      for await(const [name,handle]of root.entries()){
        if(handle.kind!=='file')throw Error('Unexpected study directory');const f=await handle.getFile();if(f.size>1024*1024)throw Error('Unexpected study asset size');
        const bytes=await f.arrayBuffer();const hash=[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(b=>b.toString(16).padStart(2,'0')).join('');assets.push({name,bytes:f.size,sha256:hash});
      }
      assets.sort((a,b)=>a.name<b.name?-1:1);return{record,assets};
    });
    const owned=new Set([measured.record.draft.author,...measured.record.draft.entries.map(e=>e.asset)].map(r=>'asset-'+r.id));
    const empty=measured.assets.filter(a=>a.bytes===0);assert.equal(empty.length,1);assert(!owned.has(empty[0].name));
    const created=profile.events.find(e=>e.kind==='worker-loss'&&e.hold==='asset-created').phase.detail.asset;assert.equal(empty[0].name,'asset-'+created);
    const corrupt=profile.events.find(e=>e.kind==='retained-corruption');assert.equal(measured.record.revision,'5');assert.equal(measured.record.image,corrupt.current.image);
    const checks=[measured.record.draft.author,...measured.record.draft.entries.map(e=>e.asset)].map(ref=>{
      const actual=measured.assets.find(a=>a.name==='asset-'+ref.id);assert(actual);return{id:ref.id,expected:ref,observed:actual,valid:ref.bytes===actual.bytes&&ref.sha256===actual.sha256};
    });
    assert.deepEqual(checks.filter(c=>!c.valid).map(c=>c.id),[corrupt.entry.asset.id]);
    rows.push({engine:profile.engine,browserVersion:context.browser().version(),record:measured.record,assets:measured.assets,referenced:checks,
      emptyUnreferenced:empty.map(a=>a.name),terminationTargetObservedAsEmpty:true,unreferenced:measured.assets.filter(a=>!owned.has(a.name)).map(a=>a.name)});
    await context.close();context=null;
  }
}catch(e){error={name:e.name,message:e.message,stack:e.stack};throw e;}
finally{
  if(context)await context.close();await new Promise(resolve=>server.close(resolve));
  await writeFile(join(run,'backend-inspection.mjs'),await readFile(fileURLToPath(import.meta.url)));
  await writeFile(output,JSON.stringify({schema:1,producerSha256:sha(await readFile(join(run,'backend-inspection.mjs'))),browserReceiptSha256:sha(originalBytes),rows,error,contextsClosed:true,serverClosed:true,
    limits:['Read-only application storage query,not process-wide browser-profile write tracing.','Corrupt referenced JAR is the explicit owned fault from the first capture;no repair,deletion,GC,or real-user state accessed.','Empty private file is retained as an orphan. Fresh retry succeeded with a different handle;no general collision,eviction,quota,retention or durability guarantee.']},null,2)+'\n');
}
console.log(JSON.stringify({run,engines:rows.map(r=>({engine:r.engine,assets:r.assets.length,emptyOrphans:r.emptyUnreferenced.length,unreferenced:r.unreferenced.length})),error}));
