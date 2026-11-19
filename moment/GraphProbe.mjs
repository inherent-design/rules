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
