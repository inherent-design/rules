// Owner-run selected VS Code methods. No application or extension host launch.
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {stripTypeScriptTypes} from 'node:module';
import {resolve,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import vm from 'node:vm';

const root=resolve(fileURLToPath(new URL('../..',import.meta.url)));
const ledgerPath=join(root,'applications/sources/vscode-extensions-selections.json');
const ledgerBytes=await readFile(ledgerPath),ledger=JSON.parse(ledgerBytes);
const sha=b=>createHash('sha256').update(b).digest('hex');
const bodies={};
for(const row of ledger.sources){const b=await readFile(join(root,row.cache));if(sha(b)!==row.sha256)throw Error('Source drift: '+row.path);bodies[row.id]=b.toString();}
function method(text,start){const a=text.indexOf(start),b=text.indexOf('\n\t}\n}',a);if(a<0||b<0)throw Error('Missing pinned method boundary.');return text.slice(a,b+4);}
const native=method(bodies.native,'\tpublic static pickExtensionHostKind(');
const browser=method(bodies.browser,'\tpublic static pickRunningLocation(');
const common=bodies.kinds.slice(bodies.kinds.indexOf('export function determineExtensionHostKinds(')).replace('export function','function');
// Enum values and lowercase-only identifier adapter are fixture dependencies.
// Every original method body is unchanged; source imports/constructors are not run.
const fragment=`const ExtensionHostKind={LocalProcess:1,LocalWebWorker:2,Remote:3};
const ExtensionRunningPreference={None:0,Local:1,Remote:2};
const ExtensionIdentifier={toKey:(id)=>id.value.toLowerCase()};
class NativeFragment {\n${native}\n}
class BrowserFragment {\n${browser}\n}
${common}
globalThis.fixture={NativeFragment,BrowserFragment,determineExtensionHostKinds};\n`;
// Node 26.13.1 only strips types. Its API does not lower parameter properties.
// Supply the two helper-record constructors as explicit fixture adapters;
// selected caller/picker/getter bodies remain byte-for-byte upstream excerpts.
let adapted=fragment;
for(const [before,after] of [
  ['constructor(\n\t\tpublic readonly desc: IExtensionDescription,\n\t\tpublic readonly kind: ExtensionKind[]\n\t) { }','constructor(desc,kind) { this.desc=desc;this.kind=kind; }'],
  ['constructor(\n\t\tpublic readonly local: ExtensionWithKind | null,\n\t\tpublic readonly remote: ExtensionWithKind | null,\n\t) { }','constructor(local,remote) { this.local=local;this.remote=remote; }']
]){if(adapted.split(before).length!==2)throw Error('Helper constructor boundary drift.');adapted=adapted.replace(before,after);}
const js=stripTypeScriptTypes(adapted,{mode:'strip'});
const context=vm.createContext({});new vm.Script(js).runInContext(context);
const {NativeFragment,BrowserFragment,determineExtensionHostKinds}=context.fixture;
const cases=[];
function add(label,surface,kinds,local,remote,remoteHost,worker,development='none',remoteKinds=kinds){
  cases.push({label,surface,localKinds:kinds,remoteKinds,local,remote,remoteHost,worker,development});
}
add('desktop-local-workspace','desktop',['workspace'],true,false,false,false);
add('remote-window-local-workspace','desktop',['workspace'],true,false,true,true);
add('remote-installed-workspace','desktop',['workspace'],false,true,true,true);
add('remote-only-ui','desktop',['ui'],false,true,true,true);
add('local-ui-remote-window','desktop',['ui'],true,true,true,true);
add('worker-disabled','desktop',['web'],true,false,false,false);
add('worker-enabled','desktop',['web'],true,false,false,true);
add('remote-only-web','desktop',['web'],false,true,true,true);
add('local-web-fallback','desktop',['workspace','web'],true,false,true,true);
add('ui-first','desktop',['ui','workspace'],true,true,true,true);
add('workspace-first','desktop',['workspace','ui'],true,true,true,true);
add('remote-development','desktop',['ui','workspace'],true,true,true,true,'remote');
add('local-development','desktop',['workspace','ui'],true,true,true,true,'local');
add('remote-development-web-first','desktop',['web','workspace'],true,true,true,true,'remote');
add('local-development-workspace-first','desktop',['workspace','web'],true,true,true,true,'local');
add('both-development-preserves-order','desktop',['workspace','ui'],true,true,true,true,'both');
add('local-manifest-wins','desktop',['ui'],true,true,true,true,'none',['workspace']);
add('local-workspace-manifest-wins','desktop',['workspace'],true,true,true,true,'none',['ui']);
add('browser-local-workspace','browser',['workspace'],true,false,false,true);
add('browser-remote-workspace','browser',['workspace'],false,true,true,true);
add('browser-local-ui','browser',['ui'],true,false,false,true);
add('browser-remote-ui-last-resort','browser',['ui'],false,true,true,true);
add('browser-web-before-ui-reserve','browser',['ui','web'],true,true,true,true);
add('browser-remote-development-ui','browser',['ui','web'],true,true,true,true,'remote');
add('browser-workspace-first','browser',['workspace','web'],true,true,true,true);
add('browser-local-development','browser',['workspace','web'],true,true,true,true,'local');
add('browser-remote-development','browser',['web','workspace'],true,true,true,true,'remote');
add('browser-remote-only-web','browser',['web'],false,true,true,true);
add('browser-local-manifest-wins','browser',['ui'],true,true,true,true,'none',['web']);
add('browser-both-development','browser',['web','workspace'],true,true,true,true,'both');
const out=join(root,'applications/evidence','vscode-host-selection-'+new Date().toISOString().replace(/[-:.]/g,''));
await mkdir(out,{recursive:true});
await writeFile(join(out,'requests.json'),JSON.stringify({schema:1,profile:'selected-vscode-1.148-host-methods',cases},null,2)+'\n');
const observations=[];
for(const row of cases){
  const desc=(remote)=>({identifier:{value:remote?'RULES-STUDY.FIXTURE':'rules-study.fixture'},kinds:remote?row.remoteKinds:row.localKinds,isUnderDevelopment:row.development==='both'||row.development===(remote?'remote':'local')});
  let callback=null;
  const result=determineExtensionHostKinds(row.local?[desc(false)]:[],row.remote?[desc(true)]:[],d=>d.kinds,(id,kinds,local,remote,preference)=>{
    const host=row.surface==='desktop'?NativeFragment.pickExtensionHostKind(kinds,local,remote,preference,row.remoteHost,row.worker):BrowserFragment.pickRunningLocation(kinds,local,remote,preference);
    callback={identifier:id.value,kinds,local,remote,preference,host};return host;
  });
  observations.push({label:row.label,callback,entries:[...result]});
}
await writeFile(join(out,'observed.json'),JSON.stringify(observations,null,2)+'\n');
await writeFile(join(out,'fragment.ts'),fragment);await writeFile(join(out,'adapter.ts'),adapted);await writeFile(join(out,'fragment.js'),js);
await writeFile(join(out,'producer.mjs'),await readFile(fileURLToPath(import.meta.url)));
const files={};for(const name of ['requests.json','observed.json','fragment.ts','adapter.ts','fragment.js','producer.mjs'])files[name]=sha(await readFile(join(out,name)));
await writeFile(join(out,'receipt.json'),JSON.stringify({schema:1,kind:'selected-source-caller-and-host-pickers',revision:ledger.revision,node:process.version,selectionSha256:sha(ledgerBytes),files,cases:cases.length,adapters:['enum constants','lowercase fixture identifier normalization','scanned descriptions','two helper-record constructors lowered to explicit fixture field assignment','effective-kind callback','remote/worker constructor facts'],limits:['No manifest deduction, user enablement, extension host, remote connection, web worker, GUI, or activation.','Same source policy may select a host for a disabled extension; host selection is not enablement.']},null,2)+'\n');
console.log(JSON.stringify({capture:out,cases:cases.length}));
