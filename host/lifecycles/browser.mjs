import {createServer} from 'node:http';
import {readFile,mkdtemp,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {createRequire} from 'node:module';
import {realpathSync} from 'node:fs';
import {resolve} from 'node:path';
import assert from 'node:assert/strict';

const packageFile=process.env.PLAYWRIGHT_PACKAGE;
if(!packageFile) throw Error('Set PLAYWRIGHT_PACKAGE to an installed playwright-core/package.json. See host/lifecycles/README.md.');
const require=createRequire(realpathSync(packageFile));
const {chromium,webkit}=require('.');
const types={chromium,webkit};
const paths={
  '/page.mjs':new URL('./browser-page.mjs',import.meta.url),
  '/worker.mjs':new URL('./browser-worker.mjs',import.meta.url),
};
const headers={ 'content-type':'text/html', 'cache-control':'no-store' };
async function listen(handler) {
  const server=createServer(handler);
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  return {server,origin:'http://127.0.0.1:'+server.address().port};
}
let applied=0;
const remote=await listen((req,res)=>{
  if(req.url==='/effect') applied++;
  if(req.url==='/allowed') res.setHeader('access-control-allow-origin','*');
  res.end('verified-bytes');
});
const local=await listen(async(req,res)=>{
  try {
    if(paths[req.url]) {
      res.writeHead(200,{'content-type':'text/javascript','cache-control':'no-store'});
      res.end(await readFile(paths[req.url]));
    } else {
      res.writeHead(200,headers);
      res.end('<!doctype html><title>Owned host fixture</title><script type="module">window.adapter=await import("/page.mjs")</script>');
    }
  } catch(error) { res.statusCode=500;res.end(error.message); }
});
const rows=[];
function record(profile,operation,predicate,observed,result,extra={}) {
  if(predicate==='collect') observed.covered=true; // This fixture enumerates every owning root.
  rows.push({v:2,profile,app:'browser-candidate',feature:operation,operationId:operation,
    target:local.origin+'/project/root',basis:'0',predicate,observed,
    outcome:{decision:Number(result),...extra}});
}
try {
 for(const [name,type] of Object.entries(types)) {
  const home=await mkdtemp(join(tmpdir(),'rules-browser-'));
  const context=await type.launchPersistentContext(home,{headless:true});
  const browser=context.browser();
  try {
    const page=await context.newPage(),other=await context.newPage();
    for(const p of [page,other]) { await p.goto(local.origin);await p.waitForFunction(()=>window.adapter); }
    const profile=name+'-'+browser.version();
    const cap=await page.evaluate(()=>({ua:navigator.userAgent,secure:isSecureContext,
      opfs:typeof navigator.storage.getDirectory==='function',locks:!!navigator.locks,
      picker:typeof window.showOpenFilePicker==='function',worker:typeof Worker==='function'}));
    assert(cap.opfs && cap.locks && cap.worker && cap.secure);
    // A missing retained input cannot be turned into a durable reference.
    let result=await page.evaluate(()=>adapter.save('0',['missing']));
    record(profile,'missing-asset','draft',{retained:false,current:true,writable:true},result);
    assert.equal((await page.evaluate(()=>adapter.current())).revision,'0');

    // A worker can persist bytes and die before committing a project or replying about its save.
    const worker=await page.evaluate(async()=>{
      const w=new Worker('/worker.mjs',{type:'module'});
      const observation=await new Promise((resolve,reject)=>{
        const timer=setTimeout(()=>reject(Error('worker timeout')),5000);
        w.onmessage=e=>{clearTimeout(timer);resolve(e.data);};
        w.onerror=e=>{clearTimeout(timer);reject(Error(e.message));};
        w.postMessage({name:'A',text:'alpha'});
      });
      w.terminate();
      return {observation,bytes:await adapter.readAsset('A'),project:await adapter.current()};
    });
    assert.equal(worker.observation.retained,'A');
    assert.equal(worker.bytes,'alpha');
    assert.equal(worker.project.revision,'0');
    record(profile,'worker-content-without-project','save_status',{confirmed:false,newer_edit:false},2,
      {workerTerminated:true,bytesRetained:true,revision:worker.project.revision});

    // An IDB request success can still be rolled back by the transaction.
    const aborted=await page.evaluate(async()=>{
      const db=await adapter.database;
      return new Promise((resolve,reject)=>{
        const tx=db.transaction('projects','readwrite');
        tx.objectStore('projects').put({revision:'999',refs:['A']},'root').onsuccess=()=>tx.abort();
        tx.onabort=async()=>resolve(await adapter.current());
        tx.onerror=()=>{};
        tx.oncomplete=()=>reject(Error('abort unexpectedly completed'));
      });
    });
    assert.equal(aborted.revision,'0');
    record(profile,'request-success-transaction-abort','save_status',{confirmed:false,newer_edit:false},2);

    // Two tabs read one basis. The transaction must recheck it inside the writer.
    await page.evaluate(()=>adapter.asset('B','beta'));
    const competing=await Promise.all([
      page.evaluate(()=>adapter.save('0',['A'])),
      other.evaluate(()=>adapter.save('0',['B'])),
    ]);
    assert.equal(competing.filter(Boolean).length,1);
    record(profile,'first-serialized-writer','draft',{retained:true,current:true,writable:true},1);
    record(profile,'second-serialized-writer','draft',{retained:true,current:false,writable:true},0);
    const selected=await page.evaluate(()=>adapter.current());
    const live=selected.refs[0],old=live==='A'?'B':'A';
    assert.equal(selected.revision,'1');

    // Undo and export plans are independent asset owners.
    const held=await page.evaluate(async(old)=>({
      undo:await adapter.collect(old,[old],[old],[]),
      plan:await adapter.collect(old,[],[old],[]),
      orphan:await adapter.collect(old,[],[],[]),
    }),old);
    assert.deepEqual(held,{undo:false,plan:false,orphan:true});
    record(profile,'undo-and-plan-hold','collect',{saved:false,undo:true,plan:true,active:false},held.undo);
    record(profile,'plan-still-holds','collect',{saved:false,undo:false,plan:true,active:false},held.plan);
    record(profile,'all-roots-released','collect',{saved:false,undo:false,plan:false,active:false},held.orphan);

    // Negative control: uncoordinated cross-store GC can delete a newly saved asset.
    await page.evaluate(()=>adapter.asset('race','retained'));
    const staleRoots=await page.evaluate(()=>adapter.current());
    assert(!staleRoots.refs.includes('race'));
    assert(await other.evaluate(()=>adapter.save('1',['race'])));
    await page.evaluate(async()=>{const root=await navigator.storage.getDirectory();await root.removeEntry('race');});
    const broken=await page.evaluate(async()=>{
      const state=await adapter.current();
      const root=await navigator.storage.getDirectory();
      let retained=true;
      try {await root.getFileHandle('race');} catch {retained=false;}
      return {state,retained};
    });
    assert(broken.state.refs.includes('race') && !broken.retained);
    rows.push({v:2,profile,app:'browser-unsafe-control',feature:'gc-publish-race',
      operationId:'gc-publish-race',target:local.origin+'/project/root',basis:'1',
      predicate:'collect',observed:{covered:true,saved:true,undo:false,plan:false,active:false},
      outcome:{decision:1,contradiction:'uncoordinated-cross-store-delete',missingAsset:true}});
    // Repair the disposable metadata to a still-retained input.
    assert(await page.evaluate(live=>adapter.save('2',[live]),live));
    await page.evaluate(()=>adapter.asset('safe-race','retained'));
    const protectedRace=await Promise.all([
      page.evaluate(()=>adapter.collect('safe-race',[],[],[])),
      other.evaluate(()=>adapter.save('3',['safe-race'])),
    ]);
    assert.equal(protectedRace.filter(Boolean).length,1);
    const sound=await page.evaluate(async()=>{
      const s=await adapter.current();
      const root=await navigator.storage.getDirectory();
      for(const id of s.refs) {try{await root.getFileHandle(id);}catch{return false;}}
      return true;
    });
    assert(sound);

    // Native writable stream visibility and abort differ from write acceptance.
    const close=await page.evaluate(async(live)=>{
      const root=await navigator.storage.getDirectory();
      const handle=await root.getFileHandle('export-output',{create:true});
      const initial=await handle.createWritable();await initial.write('original');await initial.close();
      const original=await adapter.readAsset('export-output');
      let writer=await handle.createWritable();
      await writer.write('edited');
      const before=await adapter.readAsset('export-output');
      await writer.abort();
      const afterAbort=await adapter.readAsset('export-output');
      writer=await handle.createWritable();
      await writer.write('edited');
      await writer.close();
      return {original,before,afterAbort,afterClose:await adapter.readAsset('export-output')};
    },live);
    assert.equal(close.before,close.original);
    assert.equal(close.afterAbort,close.original);
    assert.equal(close.afterClose,'edited');
    record(profile,'write-accepted','finalized',{receipt:false,valid:true},0,{before:close.before});
    record(profile,'abort-export','finalized',{receipt:false,valid:true},0,{afterAbort:close.afterAbort});
    record(profile,'closed-export','finalized',{receipt:true,valid:true},1);

    // Browser transport can deliver an opaque response with no verifiable body.
    const network=await page.evaluate(async(origin)=>{
      let blocked=false;
      try { await fetch(origin+'/blocked'); } catch { blocked=true; }
      const opaque=await fetch(origin+'/opaque',{mode:'no-cors'});
      const allowed=await fetch(origin+'/allowed');
      const effect=await fetch(origin+'/effect',{mode:'no-cors'});
      return {blocked,type:opaque.type,bytes:(await opaque.text()).length,allowed:await allowed.text(),effect:effect.type};
    },remote.origin);
    assert(network.blocked);
    assert.equal(network.type,'opaque');assert.equal(network.bytes,0);
    assert.equal(network.allowed,'verified-bytes');
    record(profile,'opaque-body','consume',{identity:true,compatible:true,covered:false},0,{responseType:'opaque'});
    record(profile,'cors-readable-body','consume',{identity:true,compatible:true,covered:true},1);
    record(profile,'opaque-effect','finalized',{receipt:false,valid:false},0,{serverApplied:applied});

    // Same origin has serialization authority, while a separate origin does not share it.
    const ownership=await page.evaluate(async()=>{
      let held,release;
      const entered=new Promise(r=>held=r),gate=new Promise(r=>release=r);
      const active=navigator.locks.request('save-root',async()=>{held();await gate;});
      await entered;
      const unavailable=await navigator.locks.request('save-root',{ifAvailable:true},lock=>lock===null);
      release();await active;
      const available=await navigator.locks.request('save-root',{ifAvailable:true},lock=>!!lock);
      return {unavailable,available};
    });
    assert.deepEqual(ownership,{unavailable:true,available:true});
    record(profile,'lock-held','draft',{retained:true,current:true,writable:false},0);
    record(profile,'lock-released','draft',{retained:true,current:true,writable:true},1);

    // Companion capability absent on this host is refused before effect.
    record(profile,'native-process-unavailable','execute',{capable:false,complete:true,approved:true},0);
    console.log(JSON.stringify({kind:'profile',profile,capabilities:cap}));
  } finally { await context.close();await rm(home,{recursive:true,force:true}); }
 }
 console.log(JSON.stringify({kind:'traces',rows}));
} finally {
 await Promise.all([new Promise(r=>local.server.close(r)),new Promise(r=>remote.server.close(r))]);
}
