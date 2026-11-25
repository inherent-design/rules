// Byte transport only. All domain selection stays in the shared Rust core.
export const LIMIT=65536;
export async function loadCore(bytes){
  const module=await WebAssembly.compile(bytes);const imports=WebAssembly.Module.imports(module);
  if(imports.length)throw Error('Unexpected WASM imports');
  const instance=await WebAssembly.instantiate(module,{}),api=instance.exports;
  for(const key of ['prepare_input','run_project','output_ptr','output_len'])if(typeof api[key]!=='function')throw Error('Missing study ABI');
  if(!(api.memory instanceof WebAssembly.Memory))throw Error('Missing study memory');
  return {imports,exports:WebAssembly.Module.exports(module).map(e=>({name:e.name,kind:e.kind})),project(packet){
    if(!(packet instanceof Uint8Array)||packet.length>LIMIT)throw Error('Study request limit');
    const ptr=api.prepare_input(packet.length)>>>0;
    if(!ptr||ptr+packet.length>api.memory.buffer.byteLength)throw Error('Study input reservation');
    new Uint8Array(api.memory.buffer,ptr,packet.length).set(packet);
    const status=api.run_project()>>>0,p=api.output_ptr()>>>0,n=api.output_len()>>>0;
    if(n>LIMIT||p+n>api.memory.buffer.byteLength)throw Error('Study output bounds');
    const output=new Uint8Array(api.memory.buffer,p,n).slice();
    if(status>1)throw Error('Unknown study result');
    return {status,hex:[...output].map(b=>b.toString(16).padStart(2,'0')).join(''),memoryBytes:api.memory.buffer.byteLength};
  }};
}
