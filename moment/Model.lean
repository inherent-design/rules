import common.Core
namespace Moment
open Rules

inductive Support | absent | asserted | withdrawn deriving DecidableEq, Repr

/-- A single immutable assertion identity. Foreign and missing endpoints both
    fail lookup. None denotes refusal before the staged batch can commit. -/
def put (localRecord sameDigest : Bool) (s : Support) : Option Support :=
  match s with
  | .absent => if localRecord then some .asserted else none
  | .asserted => if localRecord && sameDigest then some .asserted else none
  | .withdrawn => none

theorem withdrawn_final (localRecord sameDigest : Bool) :
    put localRecord sameDigest .withdrawn = none := rfl

structure EdgeState where
  cursor : Nat
  matched : Bool
  pending : Nat
  deriving DecidableEq

/-- Visible selected event, recurring edge mode, no coalescing. The observation
    is selected at the event revision. The caller checks current authorization. -/
def scan (s : EdgeState) (seq : Nat) (authorized matchesAtEvent : Bool) :=
  if !authorized || seq ≤ s.cursor then s
  else if matchesAtEvent && !s.matched then
    if admit s.pending 1 128 then ⟨seq, true, s.pending + 1⟩ else s
  else ⟨seq, matchesAtEvent, s.pending⟩

def dispatch (s : EdgeState) (stillAuthorized : Bool) (remaining cost : Nat) : Bool :=
  stillAuthorized && decide (0 < s.pending) && admit 0 cost remaining

theorem trigger_cannot_grant (s : EdgeState) (cost cap : Nat) :
    dispatch s false cap cost = false := rfl

example : scan ⟨9,false,128⟩ 10 true true = ⟨9,false,128⟩ := by decide
example : scan (scan ⟨9,false,0⟩ 10 true true) 11 true true = ⟨11,true,1⟩ := by decide
example : commit (⟨5, Support.withdrawn⟩ : Snapshot Support) 5
    (put true true .withdrawn) = ⟨5,.withdrawn⟩ := by decide
end Moment

namespace Moment
structure Placement where
  perspective : Nat
  child : Nat
  parent : Nat
  deriving DecidableEq

/-- Final visible support graph. Several assertions may support the same
    placement. Withdrawing an assertion removes only that assertion's support. -/
structure Assertion where
  id : Nat
  placement : Placement
  active : Bool
  readable : Bool
  deriving DecidableEq

def visible (rows : List Assertion) := (rows.filter (fun a => a.active && a.readable)).map (·.placement)
def withdraw (id : Nat) (rows : List Assertion) :=
  rows.map fun a => if a.id = id then {a with active := false} else a

theorem hidden_extension (rows : List Assertion) (a : Assertion) (h : a.readable = false) :
    visible (rows ++ [a]) = visible rows := by simp [visible, h]

def ParentAt (rows : List Assertion) (p c w : Nat) : Prop :=
  ⟨p,c,w⟩ ∈ visible rows

def uniqueParent (rows : List Assertion) : Prop :=
  ∀ p c x y, ParentAt rows p c x → ParentAt rows p c y → x = y

/-- Distinct perspectives stay distinct through composition. -/
def grandparent (rows : List Assertion) (p : Nat) :=
  Rules.joinRel (ParentAt rows p) (ParentAt rows p)

example : visible (withdraw 1 [⟨1,⟨0,4,5⟩,true,true⟩,⟨2,⟨0,4,5⟩,true,true⟩]) =
    [⟨0,4,5⟩] := by decide
end Moment
