import {loadCore}from './host.mjs';
const ready=fetch('/core.wasm').then(r=>{if(!r.ok)throw Error('Core unavailable');return r.arrayBuffer();}).then(loadCore);
self.onmessage=async({data})=>{const{id,hex}=data;try{
 if(typeof hex!=='string'||hex.length>131072||hex.length%2||!/^[a-f0-9]*$/.test(hex))throw Error('Invalid packet transport');
 const packet=Uint8Array.from(hex.match(/../g)??[],p=>parseInt(p,16)),core=await ready;
 self.postMessage({id,ok:true,result:core.project(packet),imports:core.imports,exports:core.exports});
}catch(error){self.postMessage({id,ok:false,error:error.message});}};
