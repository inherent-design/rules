// Each test browser context owns this origin's complete storage. These are
// candidate host adapters, not installed application implementations.
export const database = new Promise((resolve,reject) => {
  const open=indexedDB.open('host-lifecycle',1);
  open.onupgradeneeded=()=>open.result.createObjectStore('projects');
  open.onsuccess=()=>resolve(open.result);
  open.onerror=()=>reject(open.error);
});
export async function current() {
  const db=await database;
  return new Promise((resolve,reject)=>{
    const tx=db.transaction('projects','readonly');
    const r=tx.objectStore('projects').get('root');
    r.onerror=()=>reject(r.error);
    r.onsuccess=()=>resolve(r.result ?? {revision:'0',refs:[]});
  });
}
export async function asset(name,text) {
  const root=await navigator.storage.getDirectory();
  const handle=await root.getFileHandle(name,{create:true});
  const writer=await handle.createWritable();
  await writer.write(text);
  await writer.close();
  return name;
}
export async function readAsset(name) {
  const root=await navigator.storage.getDirectory();
  return (await (await root.getFileHandle(name)).getFile()).text();
}
async function saveUnlocked(base,refs) {
  const root=await navigator.storage.getDirectory();
  for(const name of refs) {
    try { await root.getFileHandle(name); } catch { return false; }
  }
  const db=await database;
  return new Promise((resolve,reject)=>{
    let changed=false;
    const tx=db.transaction('projects','readwrite');
    const store=tx.objectStore('projects');
    const request=store.get('root');
    request.onsuccess=()=>{
      const previous=request.result ?? {revision:'0',refs:[]};
      if(previous.revision===base) {
        store.put({revision:String(BigInt(base)+1n),refs},'root');
        changed=true;
      }
    };
    tx.oncomplete=()=>resolve(changed);
    tx.onabort=()=>reject(tx.error ?? Error('transaction aborted'));
    tx.onerror=()=>{};
  });
}
async function collectUnlocked(name,undo,plans,active) {
  const saved=await current();
  if([...saved.refs,...undo,...plans,...active].includes(name)) return false;
  const root=await navigator.storage.getDirectory();
  await root.removeEntry(name);
  return true;
}


// Every owner publishing references or reclaiming bytes participates in the
// same origin-scoped protocol. IDB transaction ordering alone covers metadata.
export function save(base,refs) {
  return navigator.locks.request("content-and-root",()=>saveUnlocked(base,refs));
}
export function collect(name,undo,plans,active) {
  return navigator.locks.request("content-and-root",()=>collectUnlocked(name,undo,plans,active));
}
