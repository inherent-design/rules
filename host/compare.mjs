import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {d3d12Fence} from './fence.mjs';
import Core from '../.build/host/core.mjs';

// Names belong to this host verifier. The shared stream-capture envelope also
// carries raw bytes; native.py decodes those into the streams predicate below.
const inputs = new Map(Object.entries({
  effect: ['exit_ok', 'comparable', 'differs'],
  file: ['opened_before', 'replaced'],
  streams: ['input', 'output', 'diagnostic'],
  work: ['requested_stop', 'witnessed_end'],
  receipt: ['id_matches', 'complete', 'committed'],
  product: ['owned_completion', 'world_current', 'device_current', 'consumer_ready'],
  reuse: ['retired', 'sole_pool_owner', 'no_more_uses'],
  apply_review: ['actor_allowed', 'target_matches', 'basis_current'],
}));
function readRow(row) {
  if (row.v !== 1) throw Error('unsupported trace version');
  const keys = inputs.get(row.surface);
  if (!keys || !row.case || typeof row.case !== 'string') throw Error('unknown surface or missing case');
  const values = keys.map(k => row.observed?.[k]);
  if (values.some(v => typeof v !== 'boolean')) throw Error('missing or non-boolean observation');
  const value = Core[row.surface](...values);
  assert.equal(row.outcome?.decision, value, row.surface + '/' + row.case);
}
function compareVectors(path) {
  const remaining = new Set();
  for (const [surface, names] of inputs) {
    for (let n=0; n<2**names.length; n++) {
      const flags = names.map((_,i) => Boolean(n & (1<<i)));
      remaining.add([surface,...flags].join(' '));
    }
  }
  const count = remaining.size;
  for (const line of readFileSync(path,'utf8').trim().split('\n')) {
    const [surface,...rest] = line.split(' ');
    const expected = Number(rest.pop());
    assert(remaining.delete([surface,...rest].join(' ')), 'duplicate or unknown Lean vector: '+line);
    assert.equal(Core[surface](...rest.map(x => x === 'true')), expected, line);
  }
  assert.equal(remaining.size,0,'missing Lean vectors');
  return count;
}
const removed = (1n << 64n) - 1n;
assert.equal(d3d12Fence(removed, 7n), 'device-removed');
assert.equal(d3d12Fence(2n ** 53n, 2n ** 53n + 1n), 'pending');
assert.equal(d3d12Fence(7n, 7n), 'reached');
assert.throws(() => d3d12Fence(Number(removed), 7n), /exact uint64/);
const count = compareVectors(new URL('../.build/host/vectors',import.meta.url));
const good = {v:1,surface:'work',case:'control',observed:{requested_stop:true,witnessed_end:false},outcome:{decision:0}};
readRow(good);
for (const v of [undefined,0,2]) assert.throws(() => readRow({...good,v}),/unsupported/);
assert.throws(() => readRow({...good,observed:{requested_stop:true}}),/non-boolean/);
assert.throws(() => readRow({...good,outcome:{decision:1}}),/work\/control/);
const saved = JSON.parse(readFileSync(new URL('./observations.json',import.meta.url),'utf8'));
assert.equal(saved.formatVersion,1);
for (const row of saved.observations) readRow(row);
for (const run of Object.values(saved.runs)) {
  assert.match(run.sha256, /^[a-f0-9]{64}$/);
  for (const ref of run.rows) assert(Number.isInteger(ref) && ref >= 0 && ref < saved.observations.length);
}
for (const path of process.argv.slice(2)) {
  const rows = readFileSync(path,'utf8').trim().split('\n').map(s=>JSON.parse(s));
  for (const row of rows) readRow(row);
  console.log(path, rows.length, 'native observations matched');
}
console.log(count,'Lean vectors matched the freshly emitted Bend core; refusal controls passed');
