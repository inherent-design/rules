// Owner-run source-fragment study with private OPFS handles, not a VS Code UI run.
import {createRequire,stripTypeScriptTypes} from 'node:module';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {createServer} from 'node:http';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {join,resolve} from 'node:path';
import os from 'node:os';

const root=resolve(fileURLToPath(new URL('../..',import.meta.url)));
const entrypoint=await readFile(fileURLToPath(import.meta.url));
const sdkPath=join(root,'applications/tools/playwright-core-1.64.1/package/package.json');
const {chromium}=createRequire(sdkPath)('.');
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const pin='8a14f0cc1b08d531eb83255ea3764ae22aa932b5';
const sources={
  provider:['src/vs/platform/files/browser/htmlFileSystemProvider.ts','aebeff47ba12c40f4fa11f40f53ab2efd8e4a2fdbab99162f5829507d8887272'],
  access:['src/vs/platform/files/browser/webFileSystemAccess.ts','fbf6900abb87c990ee24a4ac313c3f66c288b7dd2dd0224ae0247c287df99b55'],
  database:['src/vs/base/browser/indexedDB.ts','31dfe9d39cac8e41acd9f7a7977bce1817793739a20532d8018b1437d534640b']};
for(const [key,[path,expected]] of Object.entries(sources)) {
  const bytes=await readFile(join(root,'applications/tools/source-cache/vscode',path.replaceAll('/','__')));
  if(sha(bytes)!==expected)throw Error('Source identity changed: '+path);
  sources[key]={path,sha256:expected,text:bytes.toString('utf8')};
}
const between=(text,start,end)=>{
  const a=text.indexOf(start),b=text.indexOf(end,a+start.length);
  if(a<0||b<0)throw Error('Pinned fragment boundary missing.');
  return text.slice(a,b);
};
const registry=between(sources.provider.text,'\tprivate readonly _files =','\n\t//#endregion');
const predicates=between(sources.access.text,'\texport function isFileSystemHandle','\n}\n').replaceAll('export function','function');
const transaction=between(sources.database.text,'\tasync runInTransaction<T>','\n\t/**');
// Dependency adapters are restricted to the exact-case, root-level names used
// below. They do not qualify VS Code URI/platform case-folding semantics.
const typescript=`
const Schemas={file:'file'};
const URI={from:({scheme='file',path})=>({scheme,path})};
const extUri={
  dirname:uri=>URI.from({path:uri.path==='/'?'/':uri.path.slice(0,uri.path.lastIndexOf('/'))||'/'}),
  basename:uri=>uri.path.split('/').pop(),
  isEqual:(a,b)=>a.scheme===b.scheme&&a.path===b.path
};
const extname=name=>{if(name.includes('/'))throw Error('Unexpected path');const at=name.lastIndexOf('.');return at>0?name.slice(at):'';};
const basename=(name,ext)=>ext?name.slice(0,-ext.length):name;
const FileSystemProviderErrorCode={Unavailable:'Unavailable'};
class DBClosedError extends Error {}
class ErrorNoTelemetry extends Error {static fromError(error){return error;}}
${predicates}
const WebFileSystemAccess={isFileSystemHandle,isFileSystemFileHandle,isFileSystemDirectoryHandle};
class DatabaseFragment {
  pendingTransactions=[];
  constructor(database){this.database=database;this.name='owned-fixture';}
${transaction}
}
class RegistryFragment {
  constructor(indexedDB){this.indexedDB=indexedDB;this.store='handles';this.extUri=extUri;this.errors=[];this.logService={error:error=>this.errors.push({name:error.name,message:error.message})};}
  createFileSystemProviderError(resource,message,code){return Object.assign(new Error(message),{code});}
${registry}
}
globalThis.RegistryFragment=RegistryFragment;
globalThis.DatabaseFragment=DatabaseFragment;
`;
const javascript=stripTypeScriptTypes(typescript,{mode:'strip'});
const run=join(root,'applications/evidence','vscode-handles-'+new Date().toISOString().replace(/[-:.]/g,''));
const work=join(run,'work');await mkdir(work,{recursive:true});
await writeFile(join(work,'fragment.ts'),typescript);await writeFile(join(work,'fragment.js'),javascript);
await writeFile(join(run,'probe.mjs'),entrypoint);
const server=createServer((req,res)=>{res.writeHead(200,{'Content-Type':'text/html','Cache-Control':'no-store'});res.end('<!doctype html><title>Owned handle fixture</title>');});
await new Promise((ok,fail)=>{server.once('error',fail);server.listen(0,'127.0.0.1',ok);});
let context,observed,error,browserVersion;
const pageErrors=[],progress=[];
try {
  context=await chromium.launchPersistentContext(join(work,'profile'),{headless:true,chromiumSandbox:true,
    env:{PATH:'/usr/bin:/bin',HOME:os.homedir(),LANG:'en_US.UTF-8'}});
  browserVersion=context.browser().version();
  if(browserVersion!=='156.0.8078.4')throw Error('Browser version differs from selected SDK manifest.');
  const page=await context.newPage();
  page.on('pageerror',e=>pageErrors.push({name:e.name,message:e.message}));
  await page.exposeFunction('recordProgress',async event=>{
    progress.push(event);await writeFile(join(run,'progress.json'),JSON.stringify(progress,null,2)+'\n');
  });
  await page.goto('http://127.0.0.1:'+server.address().port);
  await page.addScriptTag({content:javascript});
  let timeout;
  const evaluation=page.evaluate(async()=>{
    const root=await navigator.storage.getDirectory();
    const a=await root.getDirectoryHandle('a',{create:true});
    const b=await root.getDirectoryHandle('b',{create:true});
    const fileA=await a.getFileHandle('entry',{create:true});
    const fileB=await b.getFileHandle('entry',{create:true});
    const directory=await b.getDirectoryHandle('entry-dir',{create:true});
    // A directory and file with the same basename require distinct parents.
    const c=await root.getDirectoryHandle('c',{create:true});
    const sameDirectory=await c.getDirectoryHandle('entry',{create:true});
    const cases=[];
    async function database(id){
      const db=await new Promise((ok,fail)=>{const r=indexedDB.open(id,1);r.onupgradeneeded=()=>r.result.createObjectStore('handles');r.onerror=()=>fail(r.error);r.onsuccess=()=>ok(r.result);});
      return {db,adapter:new DatabaseFragment(db)};
    }
    async function capture(id,first,second,options={}){
      await recordProgress({id,stage:'start'});
      const {db,adapter}=await database(id);
      const provider=new RegistryFragment(adapter);
      const initial=await (first.kind==='file'?provider.registerFileHandle(first):provider.registerDirectoryHandle(first));
      const receiving=options.fresh?new RegistryFragment(adapter):provider;
      const later=await (second.kind==='file'?receiving.registerFileHandle(second):receiving.registerDirectoryHandle(second));
      const current=await receiving.getHandle(initial);
      const fresh=new RegistryFragment(adapter);
      const persisted=await fresh.getHandle(initial);
      let directoryResult,directoryError;
      try {directoryResult=await receiving.getDirectoryHandle(later);}
      catch(e){if(e.code!=='Unavailable')throw e;directoryError={code:e.code,message:e.message};}
      cases.push({id,firstKind:first.kind,secondKind:second.kind,freshReceiver:!!options.fresh,
        firstUri:initial.path,secondUri:later.path,sameUnderlyingEntry:await first.isSameEntry(second),
        currentKind:current.kind,currentIsFirst:await current.isSameEntry(first),currentIsSecond:await current.isSameEntry(second),
        persistedKind:persisted.kind,persistedIsFirst:await persisted.isSameEntry(first),persistedIsSecond:await persisted.isSameEntry(second),
        secondDirectoryResolvable:!!directoryResult,directoryError,errors:receiving.errors});
      db.close();
      await recordProgress({id,stage:'complete',observed:cases.at(-1)});
    }
    await capture('same-file',fileA,fileA);
    await capture('different-files',fileA,fileB);
    await capture('file-then-directory',fileA,sameDirectory);
    await capture('directory-then-file',sameDirectory,fileA);
    await capture('new-provider-unloaded-alias',fileA,fileB,{fresh:true});
    const {db,adapter}=await database('failed-persistence');
    await recordProgress({id:'aborted-handle-persistence',stage:'start'});
    const aborting={runInTransaction:(store,mode,callback)=>adapter.runInTransaction(store,mode,objectStore=>{
      const request=callback(objectStore);if(mode==='readwrite')objectStore.transaction.abort();return request;
    })};
    const provider=new RegistryFragment(aborting);
    const uri=await provider.registerFileHandle(fileA);
    const memory=await provider.getHandle(uri);
    let lookup;
    try {await new RegistryFragment(adapter).getHandle(uri);lookup='unexpected-success';}
    catch(e){lookup=e.code;}
    cases.push({id:'aborted-handle-persistence',uri:uri.path,memoryIsFirst:await memory.isSameEntry(fileA),
      freshLookup:lookup,errors:provider.errors});
    await recordProgress({id:'aborted-handle-persistence',stage:'complete',observed:cases.at(-1)});
    db.close();
    return {secure:isSecureContext,browserHandles:{fileClass:fileA.constructor.name,directoryClass:directory.constructor.name,
      queryPermission:await fileA.queryPermission(),distinctSameName:!(await fileA.isSameEntry(sameDirectory))},cases};
  });
  try {observed=await Promise.race([evaluation,new Promise((_,reject)=>{
    timeout=setTimeout(()=>reject(Error('Owned source-fragment fixture exceeded 30 seconds; inspect progress.json and page errors.')),30000);
  })]);} finally {clearTimeout(timeout);}
} catch(e){error={name:e.name,message:e.message};}
finally {if(context)await context.close();await new Promise(ok=>server.close(ok));}
if(observed)await writeFile(join(run,'observed.json'),JSON.stringify(observed,null,2)+'\n');
const receipt={schema:1,kind:'Executed VS Code source fragments with native OPFS/IndexedDB; not vscode.dev picker/UI execution',
  sourceRevision:pin,sources:Object.fromEntries(Object.entries(sources).map(([key,s])=>[key,{path:s.path,sha256:s.sha256}])),
  fragmentHashes:{registry:sha(registry),predicatesAfterExportAdapter:sha(predicates),transaction:sha(transaction)},
  typescriptSha256:sha(typescript),javascriptSha256:sha(javascript),probeSha256:sha(entrypoint),
  observedSha256:observed?sha(await readFile(join(run,'observed.json'))):null,
  sdkVersion:JSON.parse(await readFile(sdkPath,'utf8')).version,platform:os.platform(),architecture:os.arch(),nodeVersion:process.version,
  browserVersion,error,pageErrors,
  limits:['Private loopback origin,private profile,real OPFS handles and IDB; no personal files or picker grants.',
    'Unmodified registry and transaction methods; dependency URI/path/error adapters restrict scope to tested exact-case root names.',
    'No full VS Code application,normal picker,reopened application process,or end-user data-loss reproduction.',
    'Fresh provider means new registry object in the same browser page; authenticated permission changes are not tested.']};
await writeFile(join(run,'receipt.json'),JSON.stringify(receipt,null,2)+'\n');
console.log(JSON.stringify({run,cases:observed?.cases,error},null,2));if(error)process.exitCode=1;
