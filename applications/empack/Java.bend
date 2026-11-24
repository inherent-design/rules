import Base

# Selection admission projection. The admitted set belongs to the game policy,
# not to the set of JVMs installed on this host.
def admitted(major: Nat, minimum: Nat, known: Bool, member: Bool) -> Bool:
  Bool.and(Nat.is_le(minimum,major),Bool.or(Bool.not(known),member))

def actual_admitted(preferred_ok: Bool, actual_ok: Bool, known: Bool, same_major: Bool) -> Bool:
  Bool.and(Bool.and(preferred_ok,actual_ok),Bool.or(known,same_major))

law known_preference_does_not_require_exact_actual:
  {actual_admitted(True{},True{},True{},False{}) == True{} : Bool}
def known_preference_does_not_require_exact_actual():
  {==}

law unknown_requires_exact_actual:
  {actual_admitted(True{},True{},False{},False{}) == False{} : Bool}
def unknown_requires_exact_actual():
  {==}

law invalid_preference_cannot_be_repaired_by_actual:
  for actual_ok: Bool
  for known: Bool
  for same: Bool
  {actual_admitted(False{},actual_ok,known,same) == False{} : Bool}
def invalid_preference_cannot_be_repaired_by_actual(actual_ok,known,same):
  {==}

law unknown_does_not_remove_floor:
  {admitted(7n,8n,False{},False{}) == False{} : Bool}
def unknown_does_not_remove_floor():
  {==}

law known_exclusion_is_refused:
  {admitted(27n,21n,True{},False{}) == False{} : Bool}
def known_exclusion_is_refused():
  {==}

def main() -> IO(Unit):
  IO.print("Finite policy admission,declared preference,and observed Java major.")
