import assert from 'node:assert/strict';
import Access from '../.build/desktop/build/access.mjs';
import { Coordinator } from '../.build/desktop/src/coordinator.mjs';

for (const [label, error] of [
  ['accepted', null], ['stale', 'STALE_LEASE'], ['wrong-caller', 'NOT_HOLDER'],
]) {
  let now = 0;
  const host = new Coordinator({ clock: () => now, blocked: false });
  const holder = {}, other = {};
  for (const [connection, name] of [[holder, 'holder'], [other, 'other']]) {
    host.call(connection, 'subscribe', { name, workspace: process.cwd() });
  }
  const grant = host.call(holder, 'take');
  const before = host.state;
  assert.deepEqual([before.holder, before.epoch, before.until], [1, 1, 900000]);
  const caller = label === 'wrong-caller' ? other : holder;
  const epoch = label === 'stale' ? 0 : before.epoch;
  now = 100;
  const core = Access.renew(before, caller.session, epoch, now);
  const lease_token = label === 'stale' ? `${host.instance}:0` : grant.lease.token;
  const renew = () => host.call(caller, 'heartbeat', { lease_token });
  if (error) assert.throws(renew, { code: error });
  else renew();

  const snapshot = host.call(holder, 'status');
  assert.equal(snapshot.holder.session_id, grant.holder.session_id);
  assert.equal(snapshot.lease.token, grant.lease.token);
  assert.equal(snapshot.lease.remaining_ms + now, core.until);
  assert.deepEqual([core.holder, core.epoch], [before.holder, before.epoch]);
  console.log(label, core.holder, core.epoch, core.until);
}

// Compare the public mode and grant, including the instant a queued successor
// could have taken over. Each participant belongs to this in-process fixture.
const host = new Coordinator({ clock: () => 0, blocked: false });
const [holder, waiting, newcomer] = [{}, {}, {}];
const ids = new Map();
for (const [index, connection] of [holder, waiting, newcomer].entries()) {
  const { session_id } = host.call(connection, 'subscribe', { name: String(index), workspace: process.cwd() });
  ids.set(session_id, index + 1);
}
function showAccess(label) {
  const { access_mode, holder, grants_allowed } = host.snapshot();
  console.log(label, access_mode, holder ? ids.get(holder.session_id) : 0, grants_allowed);
}
host.pauseAfter();
showAccess('empty');
host.setBlocked(false);
const grant = host.call(holder, 'take');
host.call(waiting, 'take');
host.pauseAfter();
assert.equal(host.call(newcomer, 'take').you.queue_position, null);
showAccess('held');
host.call(holder, 'release', { lease_token: grant.lease.token });
assert.equal(host.call(waiting, 'status').you.queue_position, 1);
showAccess('released');
