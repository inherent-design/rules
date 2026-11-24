import Base

# The host supplies these witnesses for the exact operation/target/basis.
def draft(retained: Bool, current: Bool, writable: Bool) -> Nat:
  Bool.pick(Nat, Bool.and(retained, Bool.and(current, writable)), 1n, 0n)

# A draft can be incomplete; executing an export also needs full admitted inputs.
def execute(capable: Bool, complete: Bool, approved: Bool) -> Nat:
  Bool.pick(Nat, Bool.and(capable, Bool.and(complete, approved)), 1n, 0n)

# 0 clean/no newer edit; 1 saved prior revision but current work is dirty;
# 2 no confirmed save. A known result is retained even if cancellation was requested.
def save_status(confirmed: Bool, newer_edit: Bool) -> Nat:
  Bool.pick(Nat, confirmed, Bool.pick(Nat, newer_edit, 1n, 0n), 2n)

# Collection includes every owner, including saved drafts, undo, active plans,
# runtime borrowers, and explicit recovery custody.
def collect(covered: Bool, saved: Bool, undo: Bool, plan: Bool, active: Bool) -> Nat:
  Bool.pick(Nat, Bool.and(covered, Bool.not(Bool.or(saved, Bool.or(undo, Bool.or(plan, active))))), 1n, 0n)

# UI close requests stop admission. A native end witness is required for each
# operation's own lease. Other owners still retain theirs.
def retire(closed: Bool, end_confirmed: Bool) -> Nat:
  Bool.pick(Nat, end_confirmed, 1n, 0n)

# A subscriber/view row binds the resource and its authority context. The
# producer's completeness and version must be understood before application.
def consume(identity: Bool, compatible: Bool, covered: Bool) -> Nat:
  Bool.pick(Nat, Bool.and(identity, Bool.and(compatible, covered)), 1n, 0n)

# One cancelled fetch may have reached its server. Only a valid finalization
# receipt supports a complete export/download claim.
def finalized(receipt: Bool, valid: Bool) -> Nat:
  Bool.pick(Nat, Bool.and(receipt, valid), 1n, 0n)

law missing_asset_blocks_save:
  for current: Bool
  for writable: Bool
  {draft(False{}, current, writable) == 0n : Nat}
def missing_asset_blocks_save(current, writable): {==}

law missing_capability_blocks_effect:
  for complete: Bool
  for approved: Bool
  {execute(False{}, complete, approved) == 0n : Nat}
def missing_capability_blocks_effect(complete, approved): {==}

law newer_edit_stays_dirty:
  for newer: Bool
  {save_status(True{}, newer) == Bool.pick(Nat, newer, 1n, 0n) : Nat}
def newer_edit_stays_dirty(newer): {==}

def plan_retains_covered(saved: Bool, undo: Bool, active: Bool) -> {collect(True{}, saved, undo, True{}, active) == 0n : Nat}:
  match saved:
    case True{}: {==}
    case False{}:
      match undo:
        case True{}: {==}
        case False{}: {==}

law plan_retains_content:
  for covered: Bool
  for saved: Bool
  for undo: Bool
  for active: Bool
  {collect(covered, saved, undo, True{}, active) == 0n : Nat}
def plan_retains_content(covered, saved, undo, active):
  match covered:
    case False{}: {==}
    case True{}: plan_retains_covered(saved, undo, active)

law closing_is_not_retiring:
  for closed: Bool
  {retire(closed, False{}) == 0n : Nat}
def closing_is_not_retiring(closed): {==}

law unknown_version_blocks_consumer:
  for identity: Bool
  for covered: Bool
  {consume(identity, False{}, covered) == 0n : Nat}
def unknown_version_blocks_consumer(identity, covered):
  match identity:
    case True{}: {==}
    case False{}: {==}

law missing_finalization:
  for valid: Bool
  {finalized(False{}, valid) == 0n : Nat}
def missing_finalization(valid): {==}

law incomplete_roots:
  for saved: Bool
  for undo: Bool
  for plan: Bool
  for active: Bool
  {collect(False{}, saved, undo, plan, active) == 0n : Nat}
def incomplete_roots(saved, undo, plan, active): {==}
