import common.Core

namespace Host

def file (openedBefore replaced : Bool) : Nat := if replaced && !openedBefore then 1 else 0
def streams (input output diagnostic : Bool) := input.toNat + 2*output.toNat + 4*diagnostic.toNat
def work (_requestedStop witnessedEnd : Bool) := witnessedEnd.toNat
def receipt (matchesId complete committed : Bool) : Nat :=
  if matchesId && complete then (if committed then 2 else 1) else 0
def product (ownedCompletion worldCurrent deviceCurrent consumerReady : Bool) : Nat :=
  if ownedCompletion then (if worldCurrent && deviceCurrent && consumerReady then 2 else 1) else 0
def applyReview (actorAllowed targetMatches basisCurrent : Bool) :=
  (actorAllowed && targetMatches && basisCurrent).toNat
def reuse (retired solePoolOwner noMoreUses : Bool) :=
  (retired && solePoolOwner && noMoreUses).toNat

theorem prior_handle (changed : Bool) : file true changed = 0 := by cases changed <;> rfl
theorem streams_roundtrip (i o e : Bool) :
    let mask := streams i o e
    (mask.testBit 0, mask.testBit 1, mask.testBit 2) = (i,o,e) := by
  cases i <;> cases o <;> cases e <;> decide
theorem stopping_is_not_completion (stop : Bool) : work stop false = 0 := rfl
theorem missing_ack_ambiguous (matched : Bool) :
    receipt matched false true = receipt matched false false := by cases matched <;> rfl
theorem publication_requires_current (done world device ready : Bool) :
    product done world device ready = 2 ↔ done ∧ world ∧ device ∧ ready := by
  cases done <;> cases world <;> cases device <;> cases ready <;> decide
theorem approval_requires_current (actor target basis : Bool) :
    applyReview actor target basis = 1 ↔ actor ∧ target ∧ basis := by
  cases actor <;> cases target <;> cases basis <;> decide
theorem owner_blocks_recycling (retired clean : Bool) :
    reuse retired false clean = 0 := by cases retired <;> rfl

/-- Private receipt format for one attempt on one authenticated connection.
    The version and identity checks run before the committed field is usable. -/
structure Ack where
  version : Nat
  attempt : Nat
  committed : Bool
def observeAck (expected : Nat) (r : Option Ack) : Nat :=
  r.elim 0 fun a => receipt (a.attempt == expected) (a.version == 1) a.committed
theorem accepted_ack (id : Nat) (success : Bool) :
    observeAck id (some ⟨1,id,success⟩) = (if success then 2 else 1) := by
  cases success <;> simp [observeAck, receipt]
theorem incompatible (expected : Nat) (a : Ack) (h : a.version ≠ 1) :
    observeAck expected (some a) = 0 := by simp [observeAck, receipt, h]
theorem withheld_receipt : ¬ ∃ recover : Nat → Bool, ∀ actual : Bool,
    recover (receipt true false actual) = actual := by
  rintro ⟨recover, h⟩
  have h₁ := h true
  have h₂ := h false
  simp [receipt] at h₁ h₂
  simp [h₁] at h₂

/-- Comparison of one named scope at two defined instants. Equal observations
    do not rule out an intervening write that restored the original value. -/
def effect (_exitOk comparable differs : Bool) : Nat :=
  if comparable then (if differs then 2 else 1) else 0
theorem exit_cannot_determine_change :
    ¬ ∃ decideFromExit : Bool → Nat, ∀ changed, decideFromExit false = effect false true changed := by
  rintro ⟨f, h⟩
  have h₁ := h true
  have h₂ := h false
  simp [effect] at h₁ h₂
  omega

/-- An expected generation cannot serialize writers by itself. One transition
    applies the review atomically; the other models an intervening writer. -/
inductive WriterEvent | edit | apply (reviewed : Nat)
def writerStep (revision : Nat) : WriterEvent → Nat
  | .edit => revision + 1
  | .apply reviewed => if reviewed = revision then revision + 1 else revision
theorem intervening_edit (rev : Nat) :
    Rules.replay writerStep rev [.edit,.apply rev] = rev+1 := by
  simp [Rules.replay, writerStep]
theorem order_is_visible (rev : Nat) :
    Rules.replay writerStep rev [.apply rev,.edit] ≠ Rules.replay writerStep rev [.edit,.apply rev] := by
  simp [Rules.replay, writerStep]

end Host

namespace Host
inductive Fence | removed | pending | reached deriving DecidableEq
/-- Normalized mathematical value after a lossless uint64 decode. -/
def d3d12Fence (value awaited : Nat) : Fence :=
  if value = 2^64-1 then .removed else if awaited ≤ value then .reached else .pending
theorem removed_not_complete (awaited : Nat) :
    d3d12Fence (2^64-1) awaited ≠ .reached := by simp [d3d12Fence]
example : d3d12Fence (2^53) (2^53+1) = .pending := by decide
end Host
