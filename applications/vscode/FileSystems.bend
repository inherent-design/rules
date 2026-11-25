import Base

# 0 unknown, 1 read-only, 2 writable; serialized event for its own scheme.
def current_knowledge(present: Bool, readonly: Bool) -> Nat:
  Bool.pick(Nat, present, Bool.pick(Nat, readonly, 1n, 2n), 0n)
def proposed_knowledge(added: Bool, present: Bool, readonly: Bool) -> Nat:
  Bool.pick(Nat, added, current_knowledge(present, readonly), 0n)
def reaches_callback(readonly: Bool) -> Bool:
  Bool.not(readonly)
def refused(readonly: Bool, denied: Bool) -> Bool:
  Bool.or(readonly, denied)
def creates_parent(readonly: Bool, missing: Bool) -> Bool:
  Bool.and(Bool.not(readonly), missing)
def dispatch_sees_mutation(copied: Bool, mutated: Bool) -> Bool:
  Bool.and(Bool.not(copied), mutated)
def completion_target(captured: Nat, current: Nat) -> Nat:
  captured

law current_removal_retains_writable:
  {current_knowledge(True{}, False{}) == 2n : Nat}
def current_removal_retains_writable():
  {==}
law proposed_removal_clears:
  for present: Bool
  for readonly: Bool
  {proposed_knowledge(False{}, present, readonly) == 0n : Nat}
def proposed_removal_clears(present, readonly):
  {==}
law readonly_blocks_callback:
  {reaches_callback(True{}) == False{} : Bool}
def readonly_blocks_callback():
  {==}
law refusal_can_create_parent:
  {creates_parent(False{}, True{}) == True{} : Bool}
def refusal_can_create_parent():
  {==}
law caller_copy_preserves_input:
  for mutated: Bool
  {dispatch_sees_mutation(True{}, mutated) == False{} : Bool}
def caller_copy_preserves_input(mutated):
  {==}
law completion_keeps_provider:
  for +captured: Nat
  for current: Nat
  {completion_target(captured, current) == captured : Nat}
def completion_keeps_provider(captured, current):
  {==}

def main() -> IO(Unit):
  IO.print("Selected filesystem capability, callback, and captured-input contracts.")
