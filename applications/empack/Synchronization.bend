import Base

# Independent local scope predicates. Closure/alias construction is compared by
# Lean; the owner-local adapter also constructs a separate graph traversal.
def old_ok(exists: Bool, allowed: Bool, retained_root: Bool, same_record: Bool, same_metadata: Bool, same_selection: Bool, retained_dependent: Bool) -> Bool:
  Bool.and(exists,Bool.pick(Bool,Bool.or(Bool.not(allowed),retained_root),
    Bool.and(same_record,same_metadata),Bool.not(Bool.and(Bool.not(same_selection),retained_dependent))))

def runtime_ok(old_satisfies: Bool, same_runtime: Bool) -> Bool:
  Bool.or(Bool.not(old_satisfies),same_runtime)

def new_ok(existed: Bool, allowed: Bool) -> Bool:
  Bool.or(existed,allowed)

law root_demotion_does_not_authorize_deletion:
  {old_ok(False{},False{},False{},True{},True{},True{},False{}) == False{} : Bool}
def root_demotion_does_not_authorize_deletion():
  {==}

law explicit_root_remains_protected_inside_closure:
  {old_ok(True{},True{},True{},False{},True{},False{},False{}) == False{} : Bool}
def explicit_root_remains_protected_inside_closure():
  {==}

law retained_dependent_needs_resolution:
  {old_ok(True{},True{},False{},False{},True{},False{},True{}) == False{} : Bool}
def retained_dependent_needs_resolution():
  {==}

law in_scope_metadata_can_change_without_record_change:
  {old_ok(True{},True{},False{},True{},False{},True{},False{}) == True{} : Bool}
def in_scope_metadata_can_change_without_record_change():
  {==}

law still_valid_runtime_cannot_be_reselected:
  {runtime_ok(True{},False{}) == False{} : Bool}
def still_valid_runtime_cannot_be_reselected():
  {==}

law unjustified_new_record_is_refused:
  {new_ok(False{},False{}) == False{} : Bool}
def unjustified_new_record_is_refused():
  {==}

def main() -> IO(Unit):
  IO.print("Retained records,closure scope,and exact runtime retention.")
