// Research-only storage adapter. Not empack's future project wire/API.
export const MAX_FILE=1024*1024, MAX_PROJECT=4*MAX_FILE;
export const FORMAT='rules.empack.draft-study';
const enc=new TextEncoder();
export const hex=bytes=>[...bytes].map(b=>b.toString(16).padStart(2,'0')).join('');
export async function digest(bytes){return hex(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)));}
export function canonical(v){
  if(v===null||typeof v!=='object')return JSON.stringify(v);
  if(Array.isArray(v))return '['+v.map(canonical).join(',')+']';
  return '{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+canonical(v[k])).join(',')+'}';
}
export function path(value){
  if(typeof value!=='string'||value.length>512||!value||value!==value.normalize('NFC')||/[\\\x00-\x1f<>:"|?*]/u.test(value))throw Error('Invalid study path');
  const parts=value.split('/');
  if(parts.some(p=>!p||p==='.'||p==='..'||/[. ]$/.test(p)))throw Error('Invalid study path');
  return value;
}
function assetRef(r){
  if(!r||typeof r.id!=='string'||!/^[a-f0-9-]{36}$/.test(r.id)||typeof r.sha256!=='string'||!/^[a-f0-9]{64}$/.test(r.sha256)||!Number.isSafeInteger(r.bytes)||r.bytes<0||r.bytes>MAX_FILE)throw Error('Invalid asset reference');
  return {id:r.id,sha256:r.sha256,bytes:r.bytes};
}
function revision(s){if(typeof s!=='string'||!/^(0|[1-9][0-9]*)$/.test(s))throw Error('Invalid storage revision');return BigInt(s);}
const dbp=new Promise((resolve,reject)=>{
  const r=indexedDB.open('rules-empack-draft-study',1);
  r.onupgradeneeded=()=>r.result.createObjectStore('projects');
  r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);
});
export async function current(){
  const db=await dbp;
  return new Promise((resolve,reject)=>{
    const tx=db.transaction('projects','readonly');let result;
    const request=tx.objectStore('projects').get('root');request.onsuccess=()=>{result=request.result??null;};
    tx.oncomplete=()=>resolve(result);tx.onabort=()=>reject(tx.error??Error('Read aborted'));tx.onerror=()=>{};
  });
}
export async function read(ref){
  ref=assetRef(ref);const root=await navigator.storage.getDirectory();
  const file=await(await root.getFileHandle('asset-'+ref.id)).getFile();
  if(file.size!==ref.bytes||file.size>MAX_FILE)throw Error('Retained length mismatch');
  const bytes=new Uint8Array(await file.arrayBuffer());
  if(await digest(bytes)!==ref.sha256)throw Error('Retained digest mismatch');
  return bytes;
}
async function retainUnlocked(bytes,phase=async()=>{}){
  if(bytes.byteLength>MAX_FILE)throw Error('Study asset limit');
  const ref={id:crypto.randomUUID(),sha256:await digest(bytes),bytes:bytes.byteLength};const root=await navigator.storage.getDirectory();
  // The random name is never reused or announced as available before close and
  // readback. An interrupted unpublished file remains an orphan,not a CID slot.
  const handle=await root.getFileHandle('asset-'+ref.id,{create:true});
  await phase('asset-created',{asset:ref.id});
  const writer=await handle.createWritable();
  try{await writer.write(bytes);await writer.close();}catch(e){try{await writer.abort();}catch{}throw e;}
  await read(ref);return ref;
}
export function imageProjection(image){
  const semantic=r=>({sha256:r.sha256,bytes:r.bytes});
  return {label:image.label,author:semantic(image.author),entries:image.entries.map(e=>({...e,asset:semantic(e.asset)})),missing:image.missing};
}
export async function importFiles(files){
  if(!Array.isArray(files)||!files.length||files.length>32)throw Error('Study import count');
  const names=new Set();let total=0;
  const selected=files.map(file=>{
    if(!(file instanceof File)||file.size>MAX_FILE)throw Error('Study file limit');
    const destination=path('pack/'+(file.name.endsWith('.jar')?'mods/':'config/')+file.name);
    const key=destination.toLowerCase();if(names.has(key))throw Error('Duplicate study destination');names.add(key);
    total+=file.size;if(total>MAX_PROJECT)throw Error('Study total limit');return {file,destination};
  });
  return navigator.locks.request('rules-empack-content-root',async()=>{
    const entries=[];
    for(const {file,destination}of selected){
      const bytes=new Uint8Array(await file.arrayBuffer());if(bytes.length!==file.size)throw Error('Input length changed');
      entries.push({path:destination,asset:await retainUnlocked(bytes),originalName:file.name,evidence:'observed-only'});
    }
    return entries;
  });
}
export function checkDraft(draft){
  if(!draft||typeof draft.label!=='string'||draft.label.length>256||typeof draft.rawAuthor!=='string'||enc.encode(draft.rawAuthor).length>MAX_FILE||!Array.isArray(draft.entries)||!Array.isArray(draft.missing)||draft.entries.length+draft.missing.length>32)throw Error('Invalid study draft');
  const names=new Set();let total=enc.encode(draft.rawAuthor).length;
  const entries=draft.entries.map(e=>{
    const p=path(e.path),key=p.toLowerCase();if(names.has(key))throw Error('Duplicate study destination');names.add(key);
    const asset=assetRef(e.asset);total+=asset.bytes;
    if(typeof e.originalName!=='string'||e.originalName.length>256||e.evidence!=='observed-only')throw Error('Invalid source provenance');
    return {path:p,asset,originalName:e.originalName,evidence:'observed-only'};
  }).sort((a,b)=>a.path<b.path?-1:a.path>b.path?1:0);
  const missing=draft.missing.map(p=>{p=path(p);const key=p.toLowerCase();if(names.has(key))throw Error('Conflicting missing path');names.add(key);return p;}).sort();
  if(total>MAX_PROJECT)throw Error('Study project limit');
  return {label:draft.label,rawAuthor:draft.rawAuthor,entries,missing};
}
export async function save(expected,draft,attempt,phase){
  revision(expected);draft=checkDraft(draft);
  if(typeof attempt!=='string'||!/^[a-z0-9-]{1,80}$/.test(attempt))throw Error('Invalid attempt');
  return navigator.locks.request('rules-empack-content-root',async()=>{
    const author=await retainUnlocked(enc.encode(draft.rawAuthor),phase);
    for(const e of draft.entries)await read(e.asset);
    const image={label:draft.label,author,entries:draft.entries,missing:draft.missing};
    const id=await digest(enc.encode(canonical(imageProjection(image))));
    await phase('assets-retained',{image:id});
    const db=await dbp;
    const record=await new Promise((resolve,reject)=>{
      const tx=db.transaction('projects','readwrite');const store=tx.objectStore('projects');let record=null,conflict=false;
      const get=store.get('root');
      get.onsuccess=()=>{
        const old=get.result;if((old?.revision??'0')!==expected){conflict=true;return;}
        const next=revision(expected)+1n;
        if(next>18446744073709551615n){tx.abort();return;}
        record={format:FORMAT,schema:1,project:'fixture-project',revision:String(next),attempt,image:id,draft:image};store.put(record,'root');
      };
      tx.oncomplete=()=>conflict?reject(Object.assign(Error('Saved draft changed; reopen before saving'),{code:'STALE_REVISION'})):resolve(record);
      tx.onabort=()=>reject(tx.error??Error('Save transaction aborted'));tx.onerror=()=>{};
    });
    await phase('metadata-committed',{image:record.image,revision:record.revision});
    return record;
  });
}
export async function reopen(){
  const record=await current();if(!record)return {record:null,draft:null};
  if(record.format!==FORMAT||record.schema!==1)throw Error('Unsupported study project');
  const rawAuthor=new TextDecoder('utf-8',{fatal:true}).decode(await read(record.draft.author));
  const draft=checkDraft({...record.draft,rawAuthor});
  for(const e of draft.entries)await read(e.asset);
  if(await digest(enc.encode(canonical(imageProjection(record.draft))))!==record.image)throw Error('Saved image mismatch');
  return {record,draft};
}
function base64(bytes){let value='';for(let i=0;i<bytes.length;i+=16384)value+=String.fromCharCode(...bytes.subarray(i,i+16384));return btoa(value);}
export async function backup(){
  return navigator.locks.request('rules-empack-content-root',async()=>{
    const {record}=await reopen();if(!record)throw Error('No saved draft');
    const refs=new Map([record.draft.author,...record.draft.entries.map(e=>e.asset)].map(ref=>[ref.id,ref]));
    const assets=[];for(const ref of [...refs.values()].sort((a,b)=>a.id<b.id?-1:1))assets.push({...ref,base64:base64(await read(ref))});
    return {format:FORMAT,schema:1,record,assets};
  });
}
