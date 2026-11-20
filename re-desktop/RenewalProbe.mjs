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
