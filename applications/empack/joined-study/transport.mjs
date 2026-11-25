// Framing only. The generated wasm-bindgen module supplies its declared host imports.
const encoder=new TextEncoder(),decoder=new TextDecoder('utf-8',{fatal:true});
export function transport(api){
 for(const key of['prepare_input','run_project','output_ptr','output_len'])if(typeof api[key]!=='function')throw Error('Missing study ABI');
 return {call(request){
  const bytes=encoder.encode(JSON.stringify({schema:1,...request}));if(bytes.length>65536)throw Error('Study request bound');
  const ptr=api.prepare_input(bytes.length)>>>0;if(!ptr||ptr+bytes.length>api.memory.buffer.byteLength)throw Error('Input reservation');
  new Uint8Array(api.memory.buffer,ptr,bytes.length).set(bytes);if(api.run_project()!==0)throw Error('Unknown ABI status');
  const p=api.output_ptr()>>>0,n=api.output_len()>>>0;if(n>65536||p+n>api.memory.buffer.byteLength)throw Error('Output bound');
  return JSON.parse(decoder.decode(new Uint8Array(api.memory.buffer,p,n).slice()));
 }};
}
