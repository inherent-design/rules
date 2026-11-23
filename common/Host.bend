import Base

# First/second generation of an isolated file in one directory.
def file(opened_before: Bool, replaced: Bool) -> Nat:
  match opened_before:
    case True{}: 0n
    case False{}: Bool.pick(Nat, replaced, 1n, 0n)

# Bit n records terminal attachment of fd n, independent of prompt policy.
def streams(input: Bool, output: Bool, diagnostic: Bool) -> Nat:
  Nat.add(Bool.pick(Nat, input, 1n, 0n), Nat.add(Bool.pick(Nat, output, 2n, 0n), Bool.pick(Nat, diagnostic, 4n, 0n)))

# Timed out or cancelled waiters cannot infer the worker's end. This
# classifies knowledge at observation time, assuming a valid completion signal.
def work(requested_stop: Bool, witnessed_end: Bool) -> Nat:
  Bool.pick(Nat, witnessed_end, 1n, 0n)

# Authenticated, correctly framed application receipt for this request.
# 0 unknown, 1 confirmed refusal, 2 confirmed commit.
def receipt(id_matches: Bool, complete: Bool, committed: Bool) -> Nat:
  Bool.pick(Nat, Bool.and(id_matches, complete), Bool.pick(Nat, committed, 2n, 1n), 0n)

# 0 await evidence, 1 complete but obsolete, 2 eligible to publish.
# Completion here includes successful outcome and ownership of this submission.
def product(owned_completion: Bool, world_current: Bool, device_current: Bool, consumer_ready: Bool) -> Nat:
  match owned_completion:
    case False{}: 0n
    case True{}: Bool.pick(Nat, Bool.and(world_current, Bool.and(device_current, consumer_ready)), 2n, 1n)

# All checks at one serialized effect boundary.
def apply_review(actor_allowed: Bool, target_matches: Bool, basis_current: Bool) -> Nat:
  Bool.pick(Nat, Bool.and(actor_allowed, Bool.and(target_matches, basis_current)), 1n, 0n)

law old_handle:
  for replaced: Bool
  {file(True{}, replaced) == 0n : Nat}
def old_handle(replaced):
  {==}

law cancelled_unwitnessed:
  for requested: Bool
  {work(requested, False{}) == 0n : Nat}
def cancelled_unwitnessed(requested):
  {==}

law lost_receipt:
  for matched: Bool
  for committed: Bool
  {receipt(matched, False{}, committed) == 0n : Nat}
def lost_receipt(matched, committed):
  match matched:
    case False{}: {==}
    case True{}: {==}

law stale_world:
  for device: Bool
  for ready: Bool
  {product(True{}, False{}, device, ready) == 1n : Nat}
def stale_world(device, ready):
  {==}

law revoked:
  for target: Bool
  for basis: Bool
  {apply_review(False{}, target, basis) == 0n : Nat}
def revoked(target, basis):
  {==}

# For a healthy compatible pool entry: the submission has retired (successful
# completion or confirmed non-execution), no other owner or lease needs it.
def reuse(retired: Bool, sole_pool_owner: Bool, no_more_uses: Bool) -> Nat:
  Bool.pick(Nat, Bool.and(retired, Bool.and(sole_pool_owner, no_more_uses)), 1n, 0n)

law retained_image:
  for uses_clear: Bool
  {reuse(True{}, False{}, uses_clear) == 0n : Nat}
def retained_image(uses_clear):
  {==}

# One named scope and reliable before/after observations. A final error code
# cannot supply the missing comparison. 0 unknown, 1 unchanged, 2 changed.
def effect(exit_ok: Bool, comparable: Bool, differs: Bool) -> Nat:
  Bool.pick(Nat, comparable, Bool.pick(Nat, differs, 2n, 1n), 0n)

law failed_with_effect:
  for changed: Bool
  {effect(False{}, True{}, changed) == effect(True{}, True{}, changed) : Nat}
def failed_with_effect(changed):
  {==}
