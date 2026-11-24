import applications.empack.Ownership

namespace ApplicationStudy.EmpackObservation
open ApplicationStudy.EmpackOwnership

/-- Proposed evidence vocabulary. A regular path need not imply its bytes were
    read. These are admitted host observations, never project-supplied proofs. -/
inductive Evidence
  | unavailable
  | absent
  | directory
  | regular (bytes : Option Content)
  deriving Repr

inductive Step
  | preserveUserNoByteClaim
  | prepareAbsentPlan
  | missingSource
  | needByteFacts
  | compareContent
  | rejectKind
  | needObservation
  deriving DecidableEq, Repr

/-- `distributionSource` is a selected materialized/local file source here.
    Admissible remote reference obligations belong to a different projection. -/
inductive Role | installedDestination | distributionSource deriving Repr

/-- Classification only. No variant constructs a native file change or grant.
    Scope: selected incoming file, valid metadata/root, no world-group bypass.
    Explicit changes conservatively require a new exact content-bound plan. -/
def destinationStep (incoming : Policy) (explicitChange : Bool) : Evidence → Step
  | .unavailable => .needObservation
  | .directory => .rejectKind
  | .absent => .prepareAbsentPlan
  | .regular bytes =>
    if incoming == .seed && !explicitChange then .preserveUserNoByteClaim
    else if bytes.isSome then .compareContent else .needByteFacts

/-- Distribution source bytes remain required even when their installation
    policy will be seed. The operation chooses this role, not author input. -/
def nextStep (role : Role) (incoming : Policy) (explicitChange : Bool) (evidence : Evidence) : Step :=
  match role with
  | .installedDestination => destinationStep incoming explicitChange evidence
  | .distributionSource => match evidence with
    | .unavailable => .needObservation
    | .absent => .missingSource
    | .directory => .rejectKind
    | .regular bytes => if bytes.isSome then .compareContent else .needByteFacts

/-- Current native regular-file snapshot admission, not the whole capture or
    installation protocol. Default per-file bound is 8GiB in pinned source. -/
def currentByteGate (size maximum : Nat) : Bool := size ≤ maximum

def label : Step → String
  | .preserveUserNoByteClaim => "preserve-no-byte-claim"
  | .prepareAbsentPlan => "prepare-absent-plan"
  | .missingSource => "missing-source"
  | .needByteFacts => "need-byte-facts"
  | .compareContent => "compare-content"
  | .rejectKind => "reject-kind"
  | .needObservation => "need-observation"

theorem default_seed_needs_no_byte_facts :
    nextStep .installedDestination .seed false (.regular none) = .preserveUserNoByteClaim := rfl

theorem byte_facts_do_not_change_default_seed (content : Content) :
    nextStep .installedDestination .seed false (.regular (some content)) = nextStep .installedDestination .seed false (.regular none) := rfl

theorem unknown_is_not_absence (role : Role) (policy : Policy) (explicitChange : Bool) :
    nextStep role policy explicitChange .unavailable = .needObservation := by cases role <;> rfl

theorem directory_does_not_become_file (role : Role) (policy : Policy) (explicitChange : Bool) :
    nextStep role policy explicitChange .directory = .rejectKind := by cases role <;> rfl

theorem managed_content_still_needs_bytes :
    nextStep .installedDestination .managed false (.regular none) = .needByteFacts := rfl

theorem explicit_seed_change_requires_bytes :
    nextStep .installedDestination .seed true (.regular none) = .needByteFacts := rfl

theorem seed_distribution_source_still_needs_bytes :
    nextStep .distributionSource .seed false (.regular none) = .needByteFacts := rfl

theorem absent_distribution_source_is_not_initialization :
    nextStep .distributionSource .seed false .absent = .missingSource := rfl

theorem oversized_snapshot_is_refused (size maximum : Nat) (h : maximum < size) :
    currentByteGate size maximum = false := by simp [currentByteGate, Nat.not_le.mpr h]

end ApplicationStudy.EmpackObservation
