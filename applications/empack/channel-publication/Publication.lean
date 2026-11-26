namespace ApplicationStudy.EmpackChannelPublication

/-- Closed source-comparison profile: prior authentication and candidate runtime,
    identity, origin and codec admission are witnesses, not crypto implemented here. -/
structure Request where
  priorAuthenticated : Bool
  oldSequence : Nat
  sequence : Nat
  sameDocument : Bool
  samePayload : Bool
  sameEnvelope : Bool
  deriving Repr

def current (r : Request) : Bool :=
  r.priorAuthenticated && (decide (r.oldSequence < r.sequence) ||
    (r.sequence == r.oldSequence && r.sameDocument))

def subscriber (r : Request) : Option Bool :=
  if r.priorAuthenticated then
    some (decide (r.oldSequence < r.sequence) ||
      (r.sequence == r.oldSequence && r.samePayload))
  else none

/-- Additional exact-payload requirement at an unchanged sequence. This does not
    implement publication, hashing, acquisition or legacy-pointer authentication. -/
def proposed (r : Request) : Bool :=
  current r && (decide (r.oldSequence < r.sequence) || r.samePayload)

structure Outcome where
  publisher : Bool
  subscriber : Option Bool
  proposed : Bool
  deriving Repr

def run (r : Request) : Outcome := ⟨current r, subscriber r, proposed r⟩

theorem no_authenticated_prior_no_publisher (r : Request) (h : r.priorAuthenticated = false) :
    current r = false := by simp [current, h]

theorem no_prior_floor_no_subscriber (r : Request) (h : r.priorAuthenticated = false) :
    subscriber r = none := by simp [subscriber, h]

theorem exact_payload_retry (n : Nat) (envelope : Bool) :
    run ⟨true, n, n, true, true, envelope⟩ = ⟨true, some true, true⟩ := by
  simp [run, current, subscriber, proposed]

theorem semantic_retry_publisher_accepts (n : Nat) (envelope : Bool) :
    current ⟨true, n, n, true, false, envelope⟩ = true := by simp [current]

theorem semantic_retry_subscriber_refuses (n : Nat) (envelope : Bool) :
    subscriber ⟨true, n, n, true, false, envelope⟩ = some false := by simp [subscriber]

theorem strict_retry_refuses_payload_change (n : Nat) (envelope : Bool) :
    proposed ⟨true, n, n, true, false, envelope⟩ = false := by simp [proposed, current]

theorem envelope_is_not_payload (r : Request) (value : Bool) :
    run { r with sameEnvelope := value } = run r := rfl

theorem advancing_publisher (r : Request) (auth : r.priorAuthenticated = true)
    (newer : r.oldSequence < r.sequence) : current r = true := by simp [current, auth, newer]

theorem advancing_subscriber (r : Request) (auth : r.priorAuthenticated = true)
    (newer : r.oldSequence < r.sequence) : subscriber r = some true := by simp [subscriber, auth, newer]

theorem changed_metadata_same_sequence (n : Nat) :
    current ⟨true, n, n, false, false, false⟩ = false := by simp [current]

theorem proposed_keeps_current_admission (r : Request) (h : proposed r = true) :
    current r = true := by simp only [proposed, Bool.and_eq_true] at h; exact h.1

theorem proposed_agrees_with_subscriber (r : Request) (h : proposed r = true) :
    subscriber r = some true := by
  cases auth : r.priorAuthenticated <;>
    cases doc : r.sameDocument <;> cases payload : r.samePayload <;>
    by_cases newer : r.oldSequence < r.sequence <;>
    simp_all [proposed, current, subscriber]

end ApplicationStudy.EmpackChannelPublication
