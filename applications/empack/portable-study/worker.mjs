import * as store from './store.mjs';
const incarnation=crypto.randomUUID();
self.onmessage=async({data})=>{
  const {id,kind,payload}=data;
  try{
    let value;
    if(kind==='import')value=await store.importFiles(payload.files);
    else if(kind==='reopen')value=await store.reopen();
    else if(kind==='backup')value=await store.backup();
    else if(kind==='current')value=await store.current();
    else if(kind==='save')value=await store.save(payload.expected,payload.draft,payload.attempt,async(phase,detail)=>{
      self.postMessage({id,incarnation,kind:'phase',phase,detail});
      // Deliberate test-only loss boundary,not a production cancellation API.
      if(payload.hold===phase)await new Promise(()=>{});
    });
    else throw Error('Unknown study operation');
    self.postMessage({id,incarnation,kind:'result',ok:true,value});
  }catch(error){self.postMessage({id,incarnation,kind:'result',ok:false,error:{name:error.name,message:error.message,code:error.code??null}});}
};
