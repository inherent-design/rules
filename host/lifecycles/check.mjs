import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {predicates,revision,decodeTrace} from './protocol.mjs';
import Core from '../../.build/lifecycles/core.mjs';

const remaining=new Set();
for(const [surface,keys] of Object.entries(predicates)) {
  for(let n=0;n<2**keys.length;n++) remaining.add([surface,...keys.map((_,i)=>!!(n&(1<<i)))].join(' '));
}
const count=remaining.size;
for(const line of readFileSync(new URL('../../.build/lifecycles/vectors',import.meta.url),'utf8').trim().split('\n')) {
 const [surface,...parts]=line.split(' '),value=Number(parts.pop());
 assert(remaining.delete([surface,...parts].join(' ')),'duplicate or unknown vector '+line);
 assert.equal(Core[surface](...parts.map(x=>x==='true')),value,line);
}
assert.equal(remaining.size,0);
const control={v:2,profile:'control',app:'control',feature:'save',operationId:'first',target:'root/doc',
  basis:'9007199254740993',predicate:'draft',observed:{retained:true,current:true,writable:true},outcome:{decision:1}};
assert.equal(revision(control.basis),9007199254740993n);
assert.notEqual(revision(control.basis),revision('9007199254740992'));
assert.equal(String(revision(control.basis)),control.basis);
for(const value of [9007199254740993,'01','-1','1e3','']) assert.throws(()=>revision(value),/decimal/);
for(const v of [undefined,1,3])assert.throws(()=>decodeTrace({...control,v}),/version/);
assert.throws(()=>decodeTrace({...control,target:''}),/identity/);
assert.throws(()=>decodeTrace({...control,observed:{retained:true}}),/witness/);

// Expected disagreements remain failures of conformance, recorded explicitly.
// A producer cannot exempt an arbitrary trace by inventing a contradiction label.
const counterexamples=new Map([
 ['uncoordinated-cross-store-delete',{predicate:'collect',actual:1,model:0}],
 ['vscode-provider-dirty-marker',{predicate:'save_status',actual:0,model:1}],
]);
let checked=0,disagreements=0;
const seen=new Set();
function check(row) {
  const {flags,key}=decodeTrace(row);
  assert(!seen.has(key),'duplicate native operation '+key);seen.add(key);
  const model=Core[row.predicate](...flags);
  if(row.outcome.contradiction) {
    const allowed=counterexamples.get(row.outcome.contradiction);
    assert(allowed,'unknown counterexample label');
    assert.equal(row.predicate,allowed.predicate);
    assert.equal(row.outcome.decision,allowed.actual);
    assert.equal(model,allowed.model);
    assert.notEqual(model,row.outcome.decision);
    if(row.outcome.contradiction==='vscode-provider-dirty-marker') {
      assert.equal(row.app,'vscode-desktop');
      assert.equal(row.feature,'save-raced-edit');
      assert.equal(row.outcome.saveReturn,false);
      assert.equal(row.outcome.dirty,false);
      assert.notEqual(row.outcome.buffer,row.outcome.written);
    } else {
      assert.equal(row.app,'browser-unsafe-control');
      assert.equal(row.feature,'gc-publish-race');
      assert.equal(row.outcome.missingAsset,true);
    }
    disagreements++;
  } else {
    assert.equal(model,row.outcome.decision,key);
    checked++;
  }
}
assert.throws(()=>check({...control,operationId:'mutated',outcome:{decision:0}}),/AssertionError/);
seen.clear();
for(const path of process.argv.slice(2)) {
 const text=readFileSync(path,'utf8');
 const data=path.endsWith('.jsonl')?text.trim().split('\n').map(x=>JSON.parse(x)):JSON.parse(text);
 const rows=Array.isArray(data)?data:(data.rows??[]);
 assert(rows.length>0,'no observation rows in '+path);
 for(const row of rows)check(row);
}
console.log(JSON.stringify({finiteVectors:count,nativeMatches:checked,
  retainedDisagreements:disagreements,negativeControls:'versions, missing identity/witness, revision narrowing, mutated decision'}));
