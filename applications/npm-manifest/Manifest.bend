import Base

def present(+field: Bool,array: Bool,length: Nat) -> Bool:
  Bool.or(Bool.not(field),Bool.or(Bool.not(array),Bool.not(Nat.is_eq(length,0n))))
def truthy(field: Bool,array: Bool,+length: Nat,+leaf: Bool) -> Bool:
  Bool.pick(Bool,field,
    Bool.pick(Bool,array,Bool.pick(Bool,Nat.is_eq(length,0n),False{},Bool.pick(Bool,Nat.is_eq(length,1n),leaf,True{})),leaf),True{})
def current_array(success: Bool,field: Bool,array: Bool,+length: Nat) -> Bool:
  Bool.and(success,Bool.and(field,Bool.and(array,Bool.and(Bool.not(Nat.is_eq(length,0n)),Bool.not(Nat.is_eq(length,1n))))))
def shape_array(success: Bool,field: Bool,array: Bool) -> Bool:
  Bool.and(success,Bool.and(field,array))
def current(success: Bool,+field: Bool,+array: Bool,+length: Nat,leaf: Bool) -> Bool:
  Bool.and(success,Bool.and(present(field,array,length),truthy(field,array,length,leaf)))
def display_candidate(success: Bool,field: Bool,array: Bool,length: Nat) -> Bool:
  Bool.and(success,present(field,array,length))
def shape_truthy(field: Bool,array: Bool,leaf: Bool) -> Bool:
  Bool.or(Bool.not(field),Bool.or(array,leaf))
def shape_candidate(success: Bool) -> Bool:
  success
def policy_current(+success: Bool,preserve: Bool,wrapped: Bool,+field: Bool,+array: Bool,length: Nat,+leaf: Bool) -> Bool:
  Bool.pick(Bool,wrapped,success,Bool.pick(Bool,preserve,Bool.and(success,shape_truthy(field,array,leaf)),current(success,field,array,length,leaf)))
def policy_array(+success: Bool,preserve: Bool,+wrapped: Bool,+field: Bool,+array: Bool,length: Nat) -> Bool:
  Bool.pick(Bool,wrapped,False{},Bool.pick(Bool,preserve,shape_array(success,field,array),current_array(success,field,array,length)))
def policy_display_candidate(+success: Bool,preserve: Bool,+wrapped: Bool,field: Bool,array: Bool,length: Nat) -> Bool:
  Bool.pick(Bool,wrapped,success,Bool.pick(Bool,preserve,success,display_candidate(success,field,array,length)))

# Save steps:0 invalid;1 valid no-op;2 valid changed document.
# The model assumes admitted writes succeed; it is not atomic-I/O evidence.
def attempted(steps: List<&2,Nat>) -> Nat:
  match steps:
    case Nil{}: 0n
    case Con{head,tail}:
      Bool.pick(Nat,Nat.is_eq(head,0n),1n,(1n + attempted(tail) : Nat))
def changed(steps: List<&2,Nat>) -> Nat:
  match steps:
    case Nil{}: 0n
    case Con{+head,tail}:
      Bool.pick(Nat,Nat.is_eq(head,0n),0n,(Bool.pick(Nat,Nat.is_eq(head,2n),1n,0n) + changed(tail) : Nat))
def successful(steps: List<&2,Nat>) -> Bool:
  match steps:
    case Nil{}: True{}
    case Con{head,tail}: Bool.and(Bool.not(Nat.is_eq(head,0n)),successful(tail))
def append_count(count: Nat) -> Nat:
  (count + 1n : Nat)

law falsy_scalar_lost:
  {current(True{},True{},False{},0n,False{}) == False{} : Bool}
def falsy_scalar_lost(): {==}
law truthy_scalar_kept:
  {current(True{},True{},False{},0n,True{}) == True{} : Bool}
def truthy_scalar_kept(): {==}
law empty_array_lost:
  {current(True{},True{},True{},0n,False{}) == False{} : Bool}
def empty_array_lost(): {==}
law display_preserves_falsy:
  {display_candidate(True{},True{},False{},0n) == True{} : Bool}
def display_preserves_falsy(): {==}
law display_cannot_restore_array:
  {display_candidate(True{},True{},True{},0n) == False{} : Bool}
def display_cannot_restore_array(): {==}
law shape_preserves_scalar_predicate:
  {shape_truthy(True{},False{},False{}) == False{} : Bool}
def shape_preserves_scalar_predicate(): {==}
law workspace_prefix_retained:
  {changed([2n,0n]) == 1n : Nat}
def workspace_prefix_retained(): {==}
law workspace_failure_retained:
  {successful([2n,0n]) == False{} : Bool}
def workspace_failure_retained(): {==}
law noop_no_changed_file:
  {changed([1n]) == 0n : Nat}
def noop_no_changed_file(): {==}
law append_changes_count:
  {append_count(append_count(3n)) == 5n : Nat}
def append_changes_count(): {==}

law current_single_array_tag:
  {current_array(True{},True{},True{},1n) == False{} : Bool}
def current_single_array_tag(): {==}
law candidate_single_array_tag:
  {shape_array(True{},True{},True{}) == True{} : Bool}
def candidate_single_array_tag(): {==}

law wrapped_falsy_emitted:
  {policy_current(True{},True{},True{},True{},False{},0n,False{}) == True{} : Bool}
def wrapped_falsy_emitted(): {==}
law wrapped_wire_is_object:
  {policy_array(True{},True{},True{},True{},True{},1n) == False{} : Bool}
def wrapped_wire_is_object(): {==}
law unwrapped_preserved_single_array:
  {policy_array(True{},True{},False{},True{},True{},1n) == True{} : Bool}
def unwrapped_preserved_single_array(): {==}

law array_retention_alone_not_falsy_fix:
  {policy_current(True{},True{},False{},True{},False{},0n,False{}) == False{} : Bool}
def array_retention_alone_not_falsy_fix(): {==}
