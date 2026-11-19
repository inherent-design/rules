# re:desktop

A socket connects a bridge to a shared host. The host binds a private session identity, retains a FIFO queue and issues an epoch per grant. Human pause revokes the grant; connectedness, presence heartbeats and access renewal measure different facts. Confirmed disconnection releases access, while a surviving bridge can remain connected beyond its user's last action. A deadline therefore remains an independent invalidation input.

[Model.lean](Model.lean) projects the epoch check of the pure renewal transition. Its premise is the core after host-side expiry processing and authenticated caller attribution. The upstream [six Bend laws](../../re-desktop/LAWS.bend) cover pause, paused scheduling, stale release/renewal and a FIFO head grant. Run their original proofs with `scripts/check-sources`. They provide a concrete example of a host enforcing a grant while a read-only projection merely reports it. [Source pins](../sources.json)
