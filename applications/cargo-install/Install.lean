namespace ApplicationStudy.CargoInstall

/-- Closed fixture bodies, not a file-type or executable-validity classifier. -/
inductive Body where
  | missing | v1 | v2 | manual | untracked | directory
  deriving BEq, DecidableEq, Repr
structure Bin where
  body : Body
  owner : Nat -- 0 absent, 1/2 exact fixture package IDs; source included externally
  deriving BEq, DecidableEq, Repr
structure State where
  a : Bin
  b : Bin
  metadata : Bool
  deriving BEq, DecidableEq, Repr
structure Result where
  state : State
  exitCode : Nat
  deriving Repr
def present (b : Bin) : Bool := b.body != .missing
def collision (b : Bin) : Bool := present b && b.owner == 0
def published (b : Bin) (ok : Bool) (version : Nat) : Bin :=
  if ok then ⟨if version == 1 then .v1 else .v2,version⟩ else b

/-- Both outputs compiled and staged, successful tracking writes, no orphan bins,
    A-before-B replacement order, and only the owned directory rename failure.
    This is not Cargo's general filesystem/publication or metadata codec. -/
def publish (s : State) (version : Nat) (keepNewOnFailure : Bool) : Result :=
  let newA := !present s.a
  let newB := !present s.b
  let failA := s.a.body == .directory
  let failB := !failA && s.b.body == .directory
  let okA := newA || !failA
  let okB := newB || (!failA && !failB)
  let a := published s.a okA version
  let b := published s.b okB version
  let failed := failA || failB
  let rollback := failed && !keepNewOnFailure
  ⟨⟨if rollback && newA then {a with body := .missing} else a,
     if rollback && newB then {b with body := .missing} else b,true⟩,
    if failed then 101 else 0⟩

/-- Path installs always reach compilation after duplicate admission. Loading
    tracking files can create empty metadata even on an early refusal. -/
def install (s : State) (force compileOk : Bool) (version : Nat)
    (keepNewOnFailure : Bool := false) : Result :=
  let loaded := {s with metadata := true}
  if (!force && (collision s.a || collision s.b)) || !compileOk then ⟨loaded,101⟩
  else publish loaded version keepNewOnFailure

/-- Source preflight examines all bins of the selected registered package before
    filtering --bin. Selected removals here are successful regular-file removals. -/
def uninstall (s : State) (selectA selectB : Bool) : Result :=
  if (s.a.owner != 0 && !present s.a) || (s.b.owner != 0 && !present s.b) then ⟨s,101⟩
  else ⟨{s with a := if selectA && s.a.owner != 0 then ⟨.missing,0⟩ else s.a,
                b := if selectB && s.b.owner != 0 then ⟨.missing,0⟩ else s.b},0⟩

/-- Explicit study interventions, not Cargo operations. -/
def control (s : State) (action : Nat) : State :=
  match action with
  | 0 | 5 => {s with a := {s.a with body := .manual}}
  | 1 => {s with b := {s.b with body := .directory}}
  | 2 => {s with b := {s.b with body := .v1}}
  | 3 => {s with b := {s.b with body := .missing}}
  | 4 => {s with b := {s.b with body := .v2}}
  | _ => s
def observe (s : State) : Result := ⟨s,0⟩
def initial : State := ⟨⟨.untracked,0⟩,⟨.missing,0⟩,false⟩
def v1 : State := ⟨⟨.v1,1⟩,⟨.v1,1⟩,true⟩
def mixed : State := ⟨⟨.directory,0⟩,⟨.missing,0⟩,false⟩

theorem catalog_is_not_content_verification (s : State) : (observe s).state = s := rfl
theorem compile_refusal_preserves_bins (s : State) (f : Bool) (v : Nat) :
    (install s f false v).state.a = s.a ∧ (install s f false v).state.b = s.b := by
  simp [install]
theorem untracked_refusal_can_create_empty_metadata :
    (install initial false true 1).exitCode = 101 ∧
    (install initial false true 1).state.metadata = true := by decide
theorem force_replaces_the_owned_untracked_fixture :
    (install initial true true 1).state = v1 := by decide
theorem a_path_reinstall_replaces_manual_bytes :
    (install (control v1 0) false true 1).state = v1 := by decide
theorem failed_existing_replacement_keeps_successful_prefix :
    (install (control v1 1) false true 2).state.a = ⟨.v2,2⟩ ∧
    (install (control v1 1) false true 2).state.b = ⟨.directory,1⟩ ∧
    (install (control v1 1) false true 2).exitCode = 101 := by decide
theorem current_new_bin_cleanup_can_outlive_tracking_save :
    (install mixed true true 2).state.b = ⟨.missing,2⟩ ∧
    (install mixed true true 2).exitCode = 101 := by decide
theorem catalog_keeps_the_dangling_registration :
    (observe (install mixed true true 2).state).state.b.owner = 2 ∧
    (observe (install mixed true true 2).state).exitCode = 0 := by decide
theorem uninstall_refuses_that_dangling_registration :
    (uninstall (install mixed true true 2).state false true).exitCode = 101 := by decide
theorem missing_unselected_bin_blocks_filtered_uninstall :
    (uninstall (control v1 3) true false).state = control v1 3 ∧
    (uninstall (control v1 3) true false).exitCode = 101 := by decide
theorem registered_manual_bytes_are_removed :
    (uninstall (control v1 0) true false).state.a = ⟨.missing,0⟩ ∧
    (uninstall (control v1 0) true false).state.b = v1.b := by decide
theorem proposed_keep_committed_new_bin_does_not_claim_total_success :
    (install mixed true true 2 true).state.b = ⟨.v2,2⟩ ∧
    (install mixed true true 2 true).exitCode = 101 := by decide

end ApplicationStudy.CargoInstall
