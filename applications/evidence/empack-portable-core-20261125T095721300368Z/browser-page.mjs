// Research API harness, not a production editor or browser export interface.
const worker=new Worker('/worker.mjs',{type:'module'});let id=0;const pending=new Map();
worker.onmessage=({data})=>{const p=pending.get(data.id);if(!p)return;pending.delete(data.id);data.ok?p.resolve(data):p.reject(Error(data.error));};
worker.onerror=e=>{for(const p of pending.values())p.reject(Error(e.message));pending.clear();};
window.study={project(hex){const request=++id;return new Promise((resolve,reject)=>{pending.set(request,{resolve,reject});worker.postMessage({id:request,hex});});},close(){worker.terminate();for(const p of pending.values())p.reject(Error('Worker closed;no result'));pending.clear();}};
document.querySelector('#status').textContent='Shared core study ready';
