// Selected VS Code method bodies with admitted dependency adapters. No app,
// extension host, workspace, prompt, or native process is launched.
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {stripTypeScriptTypes} from 'node:module';
import {gzipSync} from 'node:zlib';
import {fileURLToPath} from 'node:url';
import {resolve,join} from 'node:path';
import vm from 'node:vm';

const root=resolve(fileURLToPath(new URL('../..',import.meta.url)));
const producer=await readFile(fileURLToPath(import.meta.url));
const sha=data=>createHash('sha256').update(data).digest('hex');
const ledgerBytes=await readFile(join(root,'applications/sources/vscode-trust-selections.json'));
const ledger=JSON.parse(ledgerBytes);const sources={};
for(const source of ledger.sources){const bytes=await readFile(join(root,source.cache));if(sha(bytes)!==source.sha256)throw Error('Selected source mismatch.');sources[source.id]=bytes.toString('utf8');}
const between=(source,start,end)=>{const a=source.indexOf(start),b=source.indexOf(end,a+start.length);if(a<0||b<0)throw Error('Pinned method boundary missing.');return source.slice(a,b);};
const support=between(sources.manifest,'\tgetExtensionUntrustedWorkspaceSupportType(manifest:', '\n\tgetExtensionVirtualWorkspaceSupportType');
const helpers=between(sources.manifest,'\tprivate getConfiguredExtensionWorkspaceTrustRequest(manifest:', '\n\tprivate toArray');
const disabled=between(sources.enablement,'\tprivate _isDisabledByWorkspaceTrust(extension:', '\n\tprivate _isDisabledByExtensionDependency');
const enabled=between(sources.trust,'\tisWorkspaceTrustEnabled(): boolean {','\n}\n\nexport class WorkspaceTrustManagementService');
const typescript=`
const WORKSPACE_TRUST_ENABLED='security.workspace.trust.enabled';
// Lowercase generated IDs only; real identifier normalization is not modeled.
const getGalleryExtensionId=(publisher,name)=>publisher+'.'+name;
class SupportFragment {
  constructor(enabled,configured,product){
    this.workspaceTrustEnablementService={isWorkspaceTrustEnabled:()=>enabled};
    this._configuredExtensionWorkspaceTrustRequestMap=new Map(configured?[["fixture.extension",configured]]:[]);
    this._productExtensionWorkspaceTrustRequestMap=new Map(product?[["fixture.extension",product]]:[]);
  }
${support}
${helpers}
}
class EnablementFragment {
  constructor(support,inside){this.extensionManifestPropertiesService=support;this.contextService={isInsideWorkspace:()=>inside};}
${disabled}
}
class TrustEnabledFragment {
  constructor(disable,value){this.environmentService={disableWorkspaceTrust:disable};this.configurationService={getValue:()=>value};}
${enabled}
}
globalThis.fragments={SupportFragment,EnablementFragment,TrustEnabledFragment};
`;
const javascript=stripTypeScriptTypes(typescript,{mode:'strip'});
const context=vm.createContext({});new vm.Script(javascript).runInContext(context);
const {SupportFragment,EnablementFragment,TrustEnabledFragment}=context.fragments;
const run=join(root,'applications/evidence','vscode-trust-'+new Date().toISOString().replace(/[-:.]/g,''));
const work=join(run,'work');await mkdir(work,{recursive:true});
await writeFile(join(work,'fragment.ts'),typescript);await writeFile(join(work,'fragment.js'),javascript);
await writeFile(join(run,'probe.mjs'),producer);
const values=[undefined,false,true,'limited'];const supportRows=[];
// Codes:0 absent,1 false,2 true,3 limited. Version:0 unrestricted,1 exact,2 mismatch.
for(const trustEnabled of [false,true])for(const hasEntry of [false,true])for(let configured=0;configured<4;configured++)for(let version=0;version<3;version++)for(let override=0;override<4;override++)for(let declared=0;declared<4;declared++)for(let fallback=0;fallback<4;fallback++){
  const manifest={publisher:'fixture',name:'extension',version:'1.0.0',...(hasEntry?{main:'index.js'}:{}),capabilities:{untrustedWorkspaces:{supported:values[declared]}}};
  const config=configured?{supported:values[configured],...(version?{version:version===1?'1.0.0':'2.0.0'}:{})}:undefined;
  const product={override:values[override],default:values[fallback]};
  const service=new SupportFragment(trustEnabled,config,product);
  const selected=service.getExtensionUntrustedWorkspaceSupportType(manifest);const observed=values.indexOf(selected);
  if(observed<1)throw Error('Unexpected supported value.');
  const blocked=[];
  for(const trusted of [false,true])for(const inside of [false,true]){
    const check=new EnablementFragment(service,inside);
    blocked.push(check._isDisabledByWorkspaceTrust({manifest,location:'fixture-location'},{trusted}));
  }
  supportRows.push({trustEnabled,hasEntry,configured,version,override,declared,fallback,observed,blocked});
}
const enabledRows=[];
for(const disabled of [false,true])for(const value of [undefined,false,true,'invalid']){
  const selected=new TrustEnabledFragment(disabled,value).isWorkspaceTrustEnabled();
  enabledRows.push({disabled,setting:value===undefined?'absent':value,observed:selected});
}
const observed={schema:1,supportRows,enabledRows};
const bytes=Buffer.from(JSON.stringify(observed)+'\n');const compressed=gzipSync(bytes,{level:9});
await writeFile(join(run,'observed.json.gz'),compressed);
const receipt={schema:1,kind:'unmodified-source-methods-with-adapters',revision:ledger.revision,node:process.version,
  producerSha256:sha(producer),selectionSha256:sha(ledgerBytes),typescriptSha256:sha(typescript),javascriptSha256:sha(javascript),
  observedSha256:sha(bytes),compressedSha256:sha(compressed),supportCases:supportRows.length,blockedPredicates:supportRows.length*4,enabledCases:enabledRows.length,
  scope:'Selected source methods executed under Node with admitted maps/configuration/resource-membership adapters;not VS Code application,extension execution,actual trust UI or security sandbox.'};
await writeFile(join(run,'receipt.json'),JSON.stringify(receipt,null,2)+'\n');console.log(JSON.stringify({run,...receipt},null,2));
