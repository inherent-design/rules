import {readFile,writeFile}from'node:fs/promises';
import {loadCore}from'./host.mjs';
const [wasm,cases,output]=process.argv.slice(2);const core=await loadCore(await readFile(wasm)),rows=[];
for(const row of JSON.parse(await readFile(cases,'utf8')))rows.push({id:row.id,...core.project(Uint8Array.from(Buffer.from(row.packetHex,'hex')))});
await writeFile(output,JSON.stringify({schema:1,imports:core.imports,exports:core.exports,rows},null,2)+'\n');
