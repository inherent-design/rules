import assert from 'node:assert/strict';
import { applyGraph } from '../../moment/runtime/graph.mjs';
import { digest } from '../../moment/runtime/json.mjs';
const snapshot = {records: [], assertions: []};
const rec = {id:'record'};
const assertion = {id:'a', record:{systemId:'sys', contextId:'ctx', id:'record'}};
const put = {kind:'assertion.put', assertion};
const apply = changes => applyGraph(snapshot, changes, value => ({value, digest:digest(value)}),
  {systemId:'sys', contextId:'ctx', revision:4});
apply([put, {kind:'record.put', record:rec}]);
apply([put]);
assert.equal(snapshot.assertions.length,1);
assert.equal(snapshot.assertions[0].status,'asserted');
apply([{kind:'assertion.withdraw', assertionId:'a'}]);
assert.equal(snapshot.assertions[0].withdrawnAtRevision,4);
assert.throws(()=>apply([put]), {code:'IDENTITY_CONFLICT'});
assert.throws(()=>apply([{...put, assertion:{...assertion,id:'b',record:{...assertion.record,contextId:'other'}}}]), {code:'NOT_FOUND'});

const {validateTopology} = await import('../../moment/runtime/builtins.mjs');
const topology = (edges) => {
  const records = edges.map(([perspective,child,parent],index) => ({value:{
    id:String(index),kind:'relation',schema:{name:'moment.within'},
    roles:{perspective:[{id:perspective}],child:[{id:child}],parent:[{id:parent}]}
  }}));
  return {records,assertions:records.map(({value})=>({status:'asserted',assertion:{value:{record:{id:value.id}}}}))};
};
validateTopology(topology([['map','a','b'],['incident','a','c']]));
assert.throws(()=>validateTopology(topology([['map','a','b'],['map','a','c']])), {code:'INVALID_ARGUMENT'});
assert.throws(()=>validateTopology(topology([['map','a','b'],['map','b','a']])), {code:'INVALID_ARGUMENT'});
