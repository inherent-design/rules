namespace ApplicationStudy.YarnVersions

/-- The stable, numeric version profile used by these fixtures. No prerelease,
    range parser, build-metadata, or complete semver conformance claim. -/
structure Version where
  major : Nat
  minor : Nat
  patch : Nat
  deriving DecidableEq, Repr

def patch (v : Version) : Version := {v with patch := v.patch + 1}
def minor (v : Version) : Version := ⟨v.major, v.minor + 1, 0⟩
def lower (a b : Version) : Bool :=
  a.major < b.major || (a.major == b.major &&
    (a.minor < b.minor || (a.minor == b.minor && a.patch < b.patch)))

/-- Selected fixture topology: beta depends on alpha; gamma depends on beta.
    Indices alpha=0, beta=1, gamma=2. This is not a general graph decoder. -/
def dependencyScope (root candidate : Nat) (recursive : Bool) : Bool :=
  if recursive then candidate ≤ root else candidate == root
def dependentCandidate (root candidate : Nat) : Bool := root ≤ candidate

structure RecordRequest where
  current : Version
  target : Version
  priorDecision : Bool
  priorBump : Bool
  decline : Bool
  force : Bool
  dryRun : Bool
  deriving Repr
structure RecordResult where
  accepted : Bool
  decision : Bool
  bump : Bool
  deriving DecidableEq, Repr

def record (r : RecordRequest) : RecordResult :=
  let accepted := r.decline || !lower r.target r.current || r.force
  if !accepted || r.dryRun then ⟨accepted,r.priorDecision,r.priorBump⟩
  else ⟨true,true,!r.decline⟩

structure ApplyRequest where
  current : Version
  target : Version
  hasRelease : Bool
  anySelectedLower : Bool
  force : Bool
  dryRun : Bool
  /-- Closed source premise: the declared local source exists and resolution
      proceeds to the admitted successful persistence path. No I/O/crash law. -/
  inputAvailable : Bool
  selected : Bool
  deriving Repr
structure ApplyResult where
  version : Version
  retained : Bool
  announced : Bool
  saved : Bool
  successful : Bool
  deriving DecidableEq, Repr

def apply (r : ApplyRequest) : ApplyResult :=
  let allowed := !r.anySelectedLower || r.force
  let announced := allowed && r.selected && r.hasRelease
  let consumed := announced && !r.dryRun
  let saved := consumed && r.inputAvailable
  ⟨if saved then r.target else r.current,
    r.hasRelease && !consumed, announced, saved,
    allowed && (r.dryRun || r.inputAvailable)⟩

/-- Rewritable numeric dependency-range target. The source reader separately
    admits the workspace/caret/tilde prefix; exact byte formatting stays outside. -/
def rangeTarget (old target : Version) (saved : Bool) : Version :=
  if saved then target else old

/-- Three-workspace check after lock admission. A decline is a decision but
    creates no obligation to release that workspace's own dependent. -/
def check (changedA changedB changedC decidedA decidedB decidedC bumpA bumpB : Bool) : Bool :=
  (!changedA || decidedA) && (!changedB || decidedB) && (!changedC || decidedC) &&
    (!bumpA || decidedB) && (!bumpB || decidedC)

/-- Proposed resolved-apply acknowledgement, distinct from current relative
    version records. Keep exact target/recovery custody until saved evidence is
    confirmed; ambiguous or conflicting observations retain it. -/
inductive SavedEvidence where
  | unobserved | targetConfirmed | conflicting | unknown
  deriving DecidableEq, Repr

def candidateRetained : SavedEvidence → Bool
  | .targetConfirmed => false
  | _ => true

def candidateMayRetry (e : SavedEvidence) (basisMatches : Bool) : Bool :=
  e == .unobserved && basisMatches

/-- Once the exact target is observed, acknowledgement never increments again. -/
def candidateRetryTarget (resolved : Version) : Version := resolved

theorem patch_keeps_minor (v : Version) : (patch v).minor = v.minor := by rfl
theorem patch_advances (v : Version) : (patch v).patch = v.patch + 1 := by rfl
theorem minor_resets_patch (v : Version) : (minor v).patch = 0 := by rfl
theorem alpha_scope_excludes_beta : dependencyScope 0 1 true = false := by decide
theorem beta_scope_includes_alpha : dependencyScope 1 0 true = true := by decide
theorem documented_direction_differs : dependentCandidate 0 1 = true := by decide
theorem immediate_scope_is_single (r c : Nat) : dependencyScope r c false = (c == r) := by rfl
theorem lower_record_requires_force :
    (record ⟨⟨1,2,3⟩,⟨1,1,0⟩,false,false,false,false,false⟩).accepted = false := by decide
theorem force_is_not_stored_authority :
    (apply ⟨⟨1,2,3⟩,⟨1,1,0⟩,true,true,false,false,true,true⟩).successful = false := by decide
theorem preview_keeps_release (current target : Version) :
    (apply ⟨current,target,true,false,false,true,true,true⟩).retained = true := by rfl
theorem preview_does_not_save (current target : Version) :
    (apply ⟨current,target,true,false,false,true,true,true⟩).version = current := by rfl
theorem failed_input_consumes_current_record (current target : Version) :
    (apply ⟨current,target,true,false,false,false,false,true⟩).retained = false := by rfl
theorem failed_input_keeps_old_version (current target : Version) :
    (apply ⟨current,target,true,false,false,false,false,true⟩).version = current := by rfl
theorem announcement_is_not_persistence (current target : Version) :
    (apply ⟨current,target,true,false,false,false,false,true⟩).announced = true ∧
    (apply ⟨current,target,true,false,false,false,false,true⟩).saved = false := by exact ⟨rfl,rfl⟩
theorem unselected_release_is_retained (current target : Version) :
    (apply ⟨current,target,true,false,false,false,true,false⟩).retained = true := by rfl
theorem unselected_lower_does_not_require_force :
    (apply ⟨⟨1,2,3⟩,⟨1,1,0⟩,true,false,false,false,true,false⟩).successful = true := by rfl
theorem absent_decision_cannot_recreate_target (v target : Version) :
    (apply ⟨v,target,false,false,false,false,true,true⟩).version = v := by rfl
theorem missing_dependent_decision_blocks : check true false false true false false true false = false := by decide
theorem dependent_decline_is_sufficient : check true false false true true false true false = true := by decide
theorem failed_target_keeps_range (old target : Version) : rangeTarget old target false = old := by rfl
theorem saved_target_updates_range (old target : Version) : rangeTarget old target true = target := by rfl
theorem candidate_retains_unknown : candidateRetained .unknown = true := by rfl
theorem candidate_retains_unobserved : candidateRetained .unobserved = true := by rfl
theorem candidate_conflict_needs_review : candidateMayRetry .conflicting true = false := by rfl
theorem candidate_stale_basis_blocks_retry : candidateMayRetry .unobserved false = false := by rfl
theorem candidate_ack_does_not_increment (v : Version) : candidateRetryTarget v = v := by rfl

end ApplicationStudy.YarnVersions
