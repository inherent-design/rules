import assert from 'node:assert/strict';
import {readFile,writeFile,mkdir,appendFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {gzipSync,gunzipSync} from 'node:zlib';
const paths=['.build/host/core.mjs','.build/host/vectors','.build/lifecycles/core.mjs','.build/lifecycles/vectors'];
const sources=['common/Core.lean','common/Host.bend','common/Host.lean','common/Lifecycle.bend','common/Lifecycle.lean','host/Vectors.lean','host/lifecycles/Vectors.lean'];
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
if(process.argv[2]==='export'){
 const record={version:1,sources:{},files:{}};
 for(const path of sources)record.sources[path]=sha(await readFile(path));
 for(const path of paths){
  const bytes=await readFile(path);
  record.files[path]={sha256:sha(bytes),data:bytes.toString('base64')};
 }
 const output=gzipSync(JSON.stringify(record)).toString('base64');
 assert(output.length<60000,'generated rule handoff exceeds small-output budget');
 assert(process.env.GITHUB_OUTPUT,'GITHUB_OUTPUT required');
 await appendFile(process.env.GITHUB_OUTPUT,'rules='+output+'\n');
 console.log('Exported verified rule modules and model vectors ('+output.length+' encoded bytes)');
}else if(process.argv[2]==='import'){
 const text=process.env.RULES_BUNDLE;
 assert(text && text.length<60000 && /^[A-Za-z0-9+/]+=*$/.test(text),'invalid rules bundle');
 const bytes=Buffer.from(text,'base64');
 assert.equal(bytes.toString('base64'),text);
 const record=JSON.parse(gunzipSync(bytes,{maxOutputLength:524288}).toString());
 assert.equal(record.version,1);
 assert.deepEqual(Object.keys(record.sources),sources);
 assert.deepEqual(Object.keys(record.files),paths);
 for(const path of sources)assert.equal(sha(await readFile(path)),record.sources[path],'source identity changed: '+path);
 for(const path of paths){
  const file=record.files[path],data=Buffer.from(file.data,'base64');
  assert.equal(sha(data),file.sha256,'emitted identity changed');
  await mkdir(path.slice(0,path.lastIndexOf('/')),{recursive:true});
  await writeFile(path,data);
 }
 console.log('Imported emitted rules bound to the exact checked-out sources');
}else throw Error('Use export or import');
