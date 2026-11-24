import {checkDraft} from './store.mjs';
const status=document.querySelector('#status'),label=document.querySelector('#label'),author=document.querySelector('#author');
let draft={label:label.value,rawAuthor:author.value,entries:[],missing:['pack/config/not-supplied.cfg']},savedRevision='0',savedImage=null,epoch=0;
let worker,generation=0,next=0;const pending=new Map();const phases=[];
function render(){
  label.value=draft.label;author.value=draft.rawAuthor;
  const body=document.querySelector('#entries');body.replaceChildren();
  for(const entry of draft.entries){const row=document.createElement('tr');for(const text of [entry.path,String(entry.asset.bytes),entry.evidence]){const cell=document.createElement('td');cell.textContent=text;row.append(cell);}body.append(row);}
  document.querySelector('#missing').textContent=draft.missing.length?'Missing: '+draft.missing.join(', '):'No missing inputs recorded';
}
function start(){
  const own=++generation;worker=new Worker('/worker.mjs',{type:'module'});
  worker.onmessage=({data})=>{
    if(own!==generation)return;
    if(data.kind==='phase'){phases.push(data);return;}
    const request=pending.get(data.id);if(!request)return;pending.delete(data.id);
    if(data.ok)request.resolve(data.value);else request.reject(Object.assign(Error(data.error.message),data.error));
  };
  worker.onerror=e=>{for(const {reject}of pending.values())reject(Error(e.message));pending.clear();};
}
function call(kind,payload={}){const id=++next;return new Promise((resolve,reject)=>{pending.set(id,{resolve,reject});worker.postMessage({id,kind,payload});});}
function edited(){draft=checkDraft({...draft,label:label.value,rawAuthor:author.value});epoch++;status.textContent='Unsaved draft';}
label.addEventListener('input',edited);author.addEventListener('input',edited);
async function save(hold=null){
  const captured=structuredClone(draft),attempt='attempt-'+crypto.randomUUID(),capturedEpoch=epoch;
  try{
    const record=await call('save',{expected:savedRevision,draft:captured,attempt,hold});
    savedRevision=record.revision;savedImage=record.image;
    status.textContent=capturedEpoch===epoch?'Saved draft revision '+record.revision:'Saved an earlier draft; current edits remain unsaved';return record;
  }catch(e){status.textContent=e.code==='OUTCOME_UNKNOWN'?'Save result unknown. Reopen saved draft to check.':e.message;throw e;}
}
async function reopen(){const result=await call('reopen');if(result.record){draft=result.draft;savedRevision=result.record.revision;savedImage=result.record.image;epoch++;render();status.textContent='Opened saved draft revision '+savedRevision;}return result;}
async function download(){
  const bundle=await call('backup'),blob=new Blob([JSON.stringify(bundle)],{type:'application/json'}),url=URL.createObjectURL(blob);
  const link=document.createElement('a');link.href=url;link.download='empack-draft-study.json';link.textContent='Study backup';document.body.append(link);link.click();link.remove();
  // A download request is not a browser/OS delivery receipt.
  status.textContent='Backup download requested';setTimeout(()=>URL.revokeObjectURL(url),10000);return {bytes:blob.size,image:bundle.record.image};
}
function stop(){worker.terminate();generation++;for(const {reject}of pending.values())reject(Object.assign(Error('Save outcome unknown'),{code:'OUTCOME_UNKNOWN'}));pending.clear();start();}
document.querySelector('#files').addEventListener('change',async e=>{
  try{const entries=await call('import',{files:[...e.target.files]});draft=checkDraft({...draft,entries:[...draft.entries,...entries]});epoch++;render();status.textContent='Imported '+entries.length+' files; draft is unsaved';}
  catch(error){status.textContent=error.message;}
});
document.querySelector('#supply').addEventListener('change',async e=>{
  try{
    if(draft.missing.length!==1||e.target.files.length!==1)throw Error('Select one explicitly missing input');
    const [entry]=await call('import',{files:[...e.target.files]});
    // This is an explicit manual placement with no prior source assertion.
    // It is not restricted-download verification by filename.
    entry.path=draft.missing[0];draft=checkDraft({...draft,entries:[...draft.entries,entry],missing:[]});epoch++;render();status.textContent='Supplied the selected missing input; draft is unsaved';
  }catch(error){status.textContent=error.message;}
});
document.querySelector('#save').addEventListener('click',()=>save().catch(()=>{}));
document.querySelector('#reopen').addEventListener('click',()=>reopen().catch(e=>status.textContent=e.message));
document.querySelector('#backup').addEventListener('click',()=>download().catch(e=>status.textContent=e.message));
start();render();
window.study={save,reopen,download,stop,phases,current:()=>call('current'),
  snapshot:()=>({draft:structuredClone(draft),savedRevision,savedImage,epoch,status:status.textContent}),
  replace:(value)=>{draft=checkDraft(value);epoch++;render();status.textContent='Unsaved draft';},
  // Deliberate harness port,not an SDK or production import API.
  rawCall:call};
