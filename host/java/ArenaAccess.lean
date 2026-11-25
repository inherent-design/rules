import Std

namespace Host.Java25.ArenaAccess

inductive Operation | read | write | close
  deriving DecidableEq, BEq, Repr
structure State where
  alive : Bool
  historicalValue : Nat
  deriving DecidableEq, BEq, Repr
structure Context where
  shared : Bool
  actorIsOwnerThread : Bool
  deriving DecidableEq, BEq, Repr

/-- Reasons are a set encoded by bits: 1 closed,2 wrong thread. No assertion
    about exception precedence when both checks fail. Valid aligned long only. -/
def refusalReasons (s : State) (c : Context) : Nat :=
  (if s.alive then 0 else 1) + (if c.shared || c.actorIsOwnerThread then 0 else 2)
def allowed (s : State) (c : Context) : Bool := refusalReasons s c == 0
def after (s : State) (c : Context) (op : Operation) : State :=
  if allowed s c then match op with
    | .close => {s with alive := false}
    | .write => {s with historicalValue := 99}
    | .read => s
  else s
def returnedValue (s : State) (c : Context) (op : Operation) : Option Nat :=
  if allowed s c then match op with
    | .read => some s.historicalValue | .write => some 99 | .close => none
  else none

theorem owner_reads_open_confined : allowed ⟨true,42⟩ ⟨false,true⟩ = true := by decide
theorem other_thread_cannot_read_confined : refusalReasons ⟨true,42⟩ ⟨false,false⟩ = 2 := by decide
theorem wrong_thread_close_preserves_scope :
    after ⟨true,42⟩ ⟨false,false⟩ .close = ⟨true,42⟩ := by decide
theorem successful_close_revokes_access :
    allowed (after ⟨true,42⟩ ⟨false,true⟩ .close) ⟨false,true⟩ = false := by decide
theorem closed_owner_has_temporal_reason : refusalReasons ⟨false,42⟩ ⟨false,true⟩ = 1 := by decide
theorem both_failures_are_retained : refusalReasons ⟨false,42⟩ ⟨false,false⟩ = 3 := by decide
theorem shared_other_thread_can_write :
    after ⟨true,42⟩ ⟨true,false⟩ .write = ⟨true,99⟩ := by decide
theorem joined_sequential_write_is_next_read_basis :
    returnedValue (after ⟨true,42⟩ ⟨true,false⟩ .write) ⟨true,true⟩ .read = some 99 := by decide
theorem shared_other_thread_can_close :
    after ⟨true,42⟩ ⟨true,false⟩ .close = ⟨false,42⟩ := by decide
theorem closed_access_returns_no_value :
    returnedValue ⟨false,42⟩ ⟨true,true⟩ .read = none := by decide
theorem refusal_preserves_state (s : State) (c : Context) (op : Operation)
    (refused : allowed s c = false) : after s c op = s := by simp [after,refused]
theorem read_preserves_state (s : State) (c : Context) : after s c .read = s := by
  simp [after]

end Host.Java25.ArenaAccess
