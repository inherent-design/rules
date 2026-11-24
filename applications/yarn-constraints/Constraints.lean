namespace ApplicationStudy.YarnConstraints

/-- Selected fields from six owned callback examples, not a Yarn constraint DSL,
    manifest codec, resolver, or arbitrary JavaScript evaluation model. -/
structure Image where
  counter : Nat
  rootLicense : Nat -- absent/MIT/other
  childLicense : Nat
  object : Nat -- absent/{mode:plain}
  deriving BEq, DecidableEq, Repr
structure Pass where
  image : Image
  remaining : Bool
  throws : Bool
  deriving Repr
structure Result where
  image : Image
  exitCode : Nat
  evaluations : Nat
  deriving Repr

def hasFixable (mode : Nat) (s : Image) : Bool :=
  match mode with
  | 0 => s.rootLicense != 1 || s.childLicense != 1
  | 1 => s.childLicense != 1
  | 2 => s.counter < 12
  | 3 => s.counter != 1
  | 4 => s.object != 1
  | _ => false
/-- With --json, the current fixable-error guidance still uses the human
    StreamReport path; tree diagnostics use NDJSON separately. -/
def humanGuidance (mode : Nat) (fix : Bool) (s : Image) : Bool := !fix && hasFixable mode s

/-- Modes: simple assignment, mixed conflict+safe assignment, monotone chain,
    throw after an earlier saved pass, shared-object proposal, equal objects.
    Map reference identity differs from JSON equality in the latter two cases. -/
def process (mode : Nat) (fix : Bool) (s : Image) : Pass :=
  match mode with
  | 0 =>
    let needed := s.rootLicense != 1 || s.childLicense != 1
    ⟨if fix then {s with rootLicense := 1,childLicense := 1} else s,!fix && needed,false⟩
  | 1 => ⟨if fix then {s with childLicense := 1} else s,true,false⟩
  | 2 =>
    let needed := s.counter < 12
    ⟨if fix && needed then {s with counter := s.counter+1} else s,!fix && needed,false⟩
  | 3 =>
    if s.counter == 1 then ⟨s,false,true⟩
    else ⟨if fix then {s with counter := 1} else s,!fix,false⟩
  | 4 => ⟨if fix then {s with object := 1} else s,!fix && s.object != 1,false⟩
  | _ => ⟨s,true,false⟩

/-- The inspected command does not break on a stationary report. With a present
    ModernEngine it evaluates the whole selected budget unless a callback throws.
    Each successful pass's writes are awaited before the next callback. -/
def loop (mode : Nat) (fix : Bool) : Nat → Image → Result
  | 0,s => ⟨s,0,0⟩ -- no native input selects this branch directly
  | n+1,s =>
    let p := process mode fix s
    if p.throws then ⟨s,1,1⟩
    else if n == 0 then ⟨p.image,if p.remaining then 1 else 0,1⟩
    else
      let r := loop mode fix n p.image
      {r with evaluations := r.evaluations+1}
def current (mode : Nat) (fix : Bool) (s : Image) : Result := loop mode fix (if fix then 10 else 1) s
def inputs (mode : Nat) (fix : Bool) : Nat → Image → List Image
  | 0,_ => []
  | n+1,s =>
    let p := process mode fix s
    s :: (if p.throws then [] else inputs mode fix n p.image)
def unmet (mode : Nat) (s : Image) : Bool :=
  let report := process mode false s
  report.throws || report.remaining
/-- A separate proposal validates the captured final image before claiming
    success. This pure rule is not an implemented/native Yarn fix. Actual extra
    callback execution, changed graph/config and side effects require qualification. -/
def proposedStatus (mode : Nat) (r : Result) : Nat :=
  if r.exitCode != 0 || unmet mode r.image then 1 else 0

def empty : Image := ⟨0,0,0,0⟩
theorem check_keeps_image (mode : Nat) (s : Image) : (current mode false s).image = s := by
  have unchanged : (process mode false s).image = s := by
    unfold process
    split <;> try rfl
    split <;> rfl
  simp [current,loop,unchanged]
  split <;> rfl
theorem check_evaluates_once (mode : Nat) (s : Image) : (current mode false s).evaluations = 1 := by
  simp [current,loop]; split <;> rfl
theorem simple_fix_reaches_both_workspaces :
    (current 0 true empty).image = ⟨0,1,1,0⟩ := by decide
theorem stationary_simple_fix_still_evaluates_ten_times :
    (current 0 true empty).evaluations = 10 := by decide
theorem conflict_preserves_independent_fix :
    (current 1 true empty).image = ⟨0,0,1,0⟩ ∧ (current 1 true empty).exitCode = 1 := by decide
theorem bounded_chain_can_succeed_without_convergence :
    (current 2 true empty).image.counter = 10 ∧
    (current 2 true empty).exitCode = 0 ∧ unmet 2 (current 2 true empty).image = true := by decide
theorem post_cap_check_reports_remaining_work :
    (current 2 false (current 2 true empty).image).exitCode = 1 := by decide
theorem later_fix_can_finish_the_chain :
    (current 2 true (current 2 true empty).image).image.counter = 12 ∧
    unmet 2 (current 2 true (current 2 true empty).image).image = false := by decide
theorem late_throw_does_not_undo_earlier_pass :
    (current 3 true empty).image.counter = 1 ∧
    (current 3 true empty).exitCode = 1 ∧ (current 3 true empty).evaluations = 2 := by decide
theorem shared_object_is_one_assignment :
    (current 4 true empty).image.object = 1 ∧ (current 4 true empty).exitCode = 0 := by decide
theorem separate_equal_objects_still_conflict :
    (current 5 true empty).image.object = 0 ∧ (current 5 true empty).exitCode = 1 := by decide
theorem proposed_success_requires_final_check (mode : Nat) (r : Result)
    (h : proposedStatus mode r = 0) : unmet mode r.image = false := by
  unfold proposedStatus at h
  split at h <;> simp_all
theorem proposed_failure_preserves_current_failure (mode : Nat) (r : Result) (h : r.exitCode != 0) :
    proposedStatus mode r = 1 := by simp [proposedStatus,h]
theorem proposed_chain_status_retains_saved_effect :
    proposedStatus 2 (current 2 true empty) = 1 ∧
    (current 2 true empty).image.counter = 10 := by decide
theorem unmet_simple_check_has_human_guidance : humanGuidance 0 false empty = true := by decide
theorem fixing_has_no_fixable_error_guidance (mode : Nat) (s : Image) :
    humanGuidance mode true s = false := by simp [humanGuidance]

end ApplicationStudy.YarnConstraints
