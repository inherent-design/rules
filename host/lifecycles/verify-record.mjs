import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {spawnSync} from 'node:child_process';
const record=JSON.parse(readFileSync(new URL('./record.json',import.meta.url),'utf8'));
assert.equal(record.formatVersion,1);
for(const [path,digest] of Object.entries(record.sourceDigests)) {
  const actual=createHash('sha256').update(readFileSync(new URL('../../'+path,import.meta.url))).digest('hex');
  assert.equal(actual,digest,'changed lifecycle input: '+path+'; review and requalify evidence');
}
for(const run of record.runs) {
  assert(/^[a-f0-9]{64}$/.test(run.rawSha256));
  assert(Number.isInteger(run.firstRow) && run.firstRow>=0);
  assert(run.firstRow+run.rows<=record.rows.length);
}
const checked=spawnSync(process.execPath,[new URL('./check.mjs',import.meta.url).pathname,
    new URL('./record.json',import.meta.url).pathname],{stdio:'inherit'});
if(checked.error)throw checked.error;
assert.equal(checked.status,0,'retained observation comparison failed');
console.log('Retained lifecycle source identities verified');
