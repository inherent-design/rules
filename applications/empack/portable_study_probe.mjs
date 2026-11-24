// Owner-run proposed storage feasibility. No portable production engine/codec.
import {createRequire} from 'node:module';
import {createServer} from 'node:http';
import {readFile,writeFile,mkdir,stat} from 'node:fs/promises';
import {createReadStream,existsSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {join,resolve} from 'node:path';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import assert from 'node:assert/strict';

const root=resolve(fileURLToPath(new URL('../..',import.meta.url))),source=join(root,'applications/empack/portable-study');
const packagePath=join(root,'applications/tools/playwright-core-1.64.1/package/package.json');
const sdk=createRequire(packagePath)('.');const packageInfo=JSON.parse(await readFile(packagePath,'utf8'));
assert.equal(packageInfo.version,'1.64.1');
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
async function fileHash(path){const h=createHash('sha256');for await(const part of createReadStream(path))h.update(part);return h.digest('hex');}
const manifestPath=join(root,'applications/tools/playwright-core-1.64.1/package/browsers.json');
assert.equal(await fileHash(manifestPath),'2cfd419f71ac6475d81e1301fa86c34cf2a2a6bae2a0da4b5a2b18310216b6bf');
const names=['store.mjs','worker.mjs','page.mjs','page.html'];const bodies=Object.fromEntries(await Promise.all(names.map(async n=>[n,await readFile(join(source,n))])));
const run=join(root,'applications/evidence','empack-portable-storage-'+new Date().toISOString().replace(/[-:.]/g,'')),work=join(run,'work');
await mkdir(join(work,'inputs'),{recursive:true});await writeFile(join(run,'probe.mjs'),await readFile(fileURLToPath(import.meta.url)));
for(const n of names)await writeFile(join(run,n),bodies[n]);
const jar=join(work,'inputs','Sample Ω 日本.jar'),config=join(work,'inputs','rules.json'),supplied=join(work,'inputs','arbitrary-name.cfg');
const jarSource=`import sys,zipfile\nwith zipfile.ZipFile(sys.argv[1],'w',compression=zipfile.ZIP_STORED) as z:\n z.writestr('META-INF/MANIFEST.MF','Manifest-Version: 1.0\\n')\n z.writestr('study.txt','Opaque owned JAR fixture; no executable mod or game acceptance.\\n')\n`;
await writeFile(join(run,'make-jar.py'),jarSource);execFileSync('python3',['-c',jarSource,jar]);
await writeFile(config,'{"message":"local Ω 日本","enabled":true}\n');await writeFile(supplied,'# manually supplied bytes\n');
const nativeAuthor=await readFile(join(root,'applications/evidence/empack-native-ownership-20261124T031930881554Z/work/parent/project/empack.yml'),'utf8');
const allowed=new Map(names.map(n=>['/'+n,bodies[n]]));allowed.set('/',bodies['page.html']);
const requests=[],profiles=[];let context,serverError,error;
const server=createServer((req,res)=>{
  const body=allowed.get(req.url);requests.push({method:req.method,path:req.url,status:body?200:404});
  res.setHeader('cache-control','no-store');res.setHeader('content-security-policy',"default-src 'self';script-src 'self';worker-src 'self';connect-src 'self';style-src 'self' 'unsafe-inline';object-src 'none';base-uri 'none'");
  if(!body){res.statusCode=404;res.end('Not found');return;}
  res.setHeader('content-type',req.url==='/'||req.url.endsWith('.html')?'text/html; charset=utf-8':'text/javascript; charset=utf-8');res.end(body);
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));const origin='http://127.0.0.1:'+server.address().port;
const receipt={schema:1,kind:'Research-only browser draft storage,not portable empack implementation',producerSha256:await fileHash(join(run,'probe.mjs')),
  sourceSha256:Object.fromEntries(names.map(n=>[n,sha(bodies[n])])),package:{path:packagePath,version:packageInfo.version,sha256:await fileHash(packagePath),browserManifestSha256:await fileHash(manifestPath)},
  inputSha256:{jar:await fileHash(jar),config:await fileHash(config),supplied:await fileHash(supplied),nativeAuthor:sha(nativeAuthor)},origin,profiles,requests,
  limits:['Proposed study schema and host adapter;no production portable engine,project wire,consumer codec or browser Prism export.',
    'FileList injection exercises actual File/FileList APIs;not human OS picker/drag-drop permission acceptance.',
    'Private persistent profiles and loopback origin only;no account,remote service,live project/store or game.',
    'No asset collection/deletion. Store-byte references and semantic image digest are distinct;digest is observation,not source authentication.']};
async function saveReceipt(){await writeFile(join(run,'receipt.json'),JSON.stringify(receipt,null,2)+'\n');}
async function snap(page){return page.evaluate(()=>study.snapshot());}
async function phase(page,name,start){
  await page.waitForFunction(({name,start})=>study.phases.slice(start).some(p=>p.phase===name),{name,start},{timeout:10000});
  return page.evaluate(({name,start})=>study.phases.slice(start).find(p=>p.phase===name),{name,start});
}
try{
  for(const name of ['chromium','webkit']){
    const type=sdk[name],home=join(work,name,'profile');await mkdir(home,{recursive:true});
    const executable=type.executablePath();assert(existsSync(executable));
    const row={engine:name,executable,executableSha256:await fileHash(executable),events:[],errors:[],downloads:[],contextClosed:false};profiles.push(row);await saveReceipt();
    async function launch(){
      context=await type.launchPersistentContext(home,{headless:true,acceptDownloads:true,viewport:{width:1100,height:850}});
      row.browserVersion=context.browser().version();const page=await context.newPage();
      page.on('pageerror',e=>row.errors.push(e.message));await page.goto(origin);await page.waitForFunction(()=>window.study);return page;
    }
    let page=await launch();row.capabilities=await page.evaluate(()=>({secure:isSecureContext,opfs:typeof navigator.storage.getDirectory==='function',locks:!!navigator.locks,workers:typeof Worker==='function',indexedDB:!!indexedDB}));
    assert(Object.values(row.capabilities).every(Boolean));
    await page.locator('#files').setInputFiles([jar,config]);await page.waitForFunction(()=>study.snapshot().draft.entries.length===2);
    await page.locator('#label').fill('<img src=x onerror="window.injected=true"> Ω 日本');
    await page.evaluate(()=>{const v=study.snapshot().draft;v.entries.find(e=>e.path.endsWith('/rules.json')).path='pack/config/renamed-rules.json';study.replace(v);});
    assert.equal(await page.evaluate(()=>!!window.injected||!!document.querySelector('img')),false);
    row.events.push({kind:'import-edit',state:await snap(page)});
    const first=await page.evaluate(()=>study.save());assert.equal(first.revision,'1');
    row.events.push({kind:'save-invalid-missing',record:first,state:await snap(page)});
    const other=await context.newPage();await other.goto(origin);await other.waitForFunction(()=>window.study);await other.evaluate(()=>study.reopen());
    const second=await page.evaluate(()=>study.save());assert.equal(second.revision,'2');assert.equal(first.image,second.image);assert.notEqual(first.draft.author.id,second.draft.author.id);
    row.events.push({kind:'same-image-new-backing',record:second,state:await snap(page)});
    await other.locator('#label').fill('Stale tab');const stale=await other.evaluate(async()=>{try{await study.save();return {unexpected:true};}catch(e){return {error:e.message,code:e.code,state:study.snapshot(),current:await study.current()};}});
    assert.equal(stale.code,'STALE_REVISION');assert.equal(stale.current.revision,'2');row.events.push({kind:'stale-tab',...stale});await other.close();
    const downloadFile=async(label)=>{
      const ready=page.waitForEvent('download',{timeout:10000});await page.locator('#backup').click();const download=await ready;
      const destination=join(run,name+'-'+label+'.json');await download.saveAs(destination);assert.equal(await download.failure(),null);
      const bytes=await readFile(destination);const record={label,file:destination.slice(run.length+1),sha256:sha(bytes),bytes:bytes.length,suggestedFilename:download.suggestedFilename(),completed:true};row.downloads.push(record);await saveReceipt();return JSON.parse(bytes);
    };
    const invalid=await downloadFile('invalid-backup');assert.equal(invalid.record.draft.missing.length,1);
    row.events.push({kind:'invalid-backup',image:invalid.record.image,revision:invalid.record.revision});
    for(const hold of ['asset-created','assets-retained','metadata-committed']){
      await page.locator('#label').fill('Loss boundary '+hold);const before=await snap(page);const start=await page.evaluate(()=>study.phases.length);
      await page.evaluate(hold=>{window.saveObservation=study.save(hold).then(r=>({ok:true,r})).catch(e=>({ok:false,message:e.message,code:e.code}));},hold);
      const held=await phase(page,hold,start);await page.evaluate(()=>study.stop());
      const completion=await page.evaluate(()=>window.saveObservation);assert.equal(completion.code,'OUTCOME_UNKNOWN');
      const current=await page.evaluate(()=>study.current());assert.equal(current.revision,hold==='metadata-committed'?'4':hold==='asset-created'?'2':'3');
      row.events.push({kind:'worker-loss',hold,phase:held,before,completion,current,state:await snap(page),terminationRequested:true});
      if(hold==='asset-created'){
        const retry=await page.evaluate(()=>study.save());assert.equal(retry.revision,'3');row.events.push({kind:'retry-after-unpublished-file',record:retry,state:await snap(page)});
      }else{const reopened=await page.evaluate(()=>study.reopen());row.events.push({kind:'reconcile-after-loss',record:reopened.record,state:await snap(page)});}
    }
    await page.locator('#author').fill(nativeAuthor);await page.locator('#label').fill('Complete study Ω 日本');
    await page.locator('#supply').setInputFiles(supplied);await page.waitForFunction(()=>study.snapshot().draft.missing.length===0&&study.snapshot().draft.entries.length===3);
    const complete=await page.evaluate(()=>study.save());assert.equal(complete.revision,'5');row.events.push({kind:'save-complete',record:complete,state:await snap(page)});
    const beforeRestart=await snap(page);await context.close();context=null;row.firstContextClosed=true;
    page=await launch();const reopened=await page.evaluate(()=>study.reopen());assert.equal(reopened.record.image,complete.image);assert.equal(reopened.record.revision,'5');
    row.events.push({kind:'browser-relaunch-reopen',before:beforeRestart,record:reopened.record,state:await snap(page)});
    const backup=await downloadFile('complete-backup');assert.equal(backup.record.image,complete.image);
    const corrupt=await page.evaluate(async()=>{
      const entry=study.snapshot().draft.entries.find(e=>e.path.endsWith('.jar'));const root=await navigator.storage.getDirectory(),handle=await root.getFileHandle('asset-'+entry.asset.id);
      const bytes=new Uint8Array(await(await handle.getFile()).arrayBuffer());bytes[0]^=1;const writer=await handle.createWritable();await writer.write(bytes);await writer.close();
      let openError,saveError;try{await study.reopen();}catch(e){openError=e.message;}try{await study.save();}catch(e){saveError=e.message;}
      return {entry,openError,saveError,current:await study.current(),state:study.snapshot()};
    });
    assert.equal(corrupt.openError,'Retained digest mismatch');assert.equal(corrupt.saveError,'Retained digest mismatch');assert.equal(corrupt.current.revision,'5');
    row.events.push({kind:'retained-corruption',...corrupt});
    await page.screenshot({path:join(run,name+'-final.png'),fullPage:true});assert.deepEqual(row.errors,[]);
    await context.close();context=null;row.contextClosed=true;await saveReceipt();
    console.log(JSON.stringify({engine:name,browser:row.browserVersion,events:row.events.length,downloads:row.downloads.length,closed:row.contextClosed}));
  }
}catch(e){error={name:e.name,message:e.message,stack:e.stack};receipt.error=error;throw e;}
finally{
  if(context){await context.close();context=null;receipt.closedAfterError=true;}
  await new Promise(resolve=>server.close(resolve));receipt.serverClosed=true;await saveReceipt();
  console.log(JSON.stringify({run,profiles:profiles.length,error,serverClosed:true}));
}
