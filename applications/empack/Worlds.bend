import Base

# One validated group. Unknown/failed observation is outside this Boolean profile.
def initialized(recorded: Bool, old: Bool, incoming: Bool) -> Bool:
  Bool.or(Bool.or(recorded, old), incoming)
def protected_group(recorded: Bool, old: Bool, incoming: Bool, overlap: Bool, occupied: Bool) -> Bool:
  Bool.or(Bool.or(recorded, old), Bool.and(incoming, Bool.or(overlap, occupied)))
def plan_members(recorded: Bool, old: Bool, +incoming: Bool, overlap: Bool, occupied: Bool) -> Bool:
  Bool.and(incoming, Bool.not(protected_group(recorded, old, incoming, overlap, occupied)))
def may_seed(recorded: Bool, old: Bool, incoming: Bool, overlap: Bool, occupied: Bool, captured: Bool, current: Bool) -> Bool:
  # Pure conjunction, not an ordering of native operations.
  Bool.and(current, Bool.and(captured, plan_members(recorded, old, incoming, overlap, occupied)))

law recorded_group_is_protected:
  for old: Bool
  for incoming: Bool
  for overlap: Bool
  for occupied: Bool
  {protected_group(True{}, old, incoming, overlap, occupied) == True{} : Bool}
def recorded_group_is_protected(old, incoming, overlap, occupied):
  {==}
law omitted_group_keeps_initialization:
  for old: Bool
  {initialized(True{}, old, False{}) == True{} : Bool}
def omitted_group_keeps_initialization(old):
  {==}
law occupied_group_is_not_filled:
  {plan_members(False{}, False{}, True{}, False{}, True{}) == False{} : Bool}
def occupied_group_is_not_filled():
  {==}
law fresh_group_is_planned:
  {plan_members(False{}, False{}, True{}, False{}, False{}) == True{} : Bool}
def fresh_group_is_planned():
  {==}
law stale_absence_does_not_authorize:
  for recorded: Bool
  for old: Bool
  for incoming: Bool
  for overlap: Bool
  for occupied: Bool
  for captured: Bool
  {may_seed(recorded, old, incoming, overlap, occupied, captured, False{}) == False{} : Bool}
def stale_absence_does_not_authorize(recorded, old, incoming, overlap, occupied, captured):
  {==}

def main() -> IO(Unit):
  IO.print("World-group preservation before per-file reconciliation; source publication premises separate.")
