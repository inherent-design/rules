namespace ApplicationStudy.JSPatches

inductive Profile | pnpm | yarn
  deriving BEq, DecidableEq, Repr
/-- Closed fixture labels: recipe 0=none,1=valid,2=inapplicable;
    lock/live 0=absent,1=base,2=valid patch,3=invalid patch.
    Yarn's flat node-modules path stays live=1 independently of its bytes. -/
structure Image where
  recipe : Nat
  lock : Nat
  live : Nat
  payload : Nat
  patchFile : Bool
  deriving BEq, ReflBEq, LawfulBEq, DecidableEq, Repr
inductive Action
  | observe
  | prepare (importExisting : Bool)
  | commit
  | install (frozen force : Bool)
  | remove (keyMatches : Bool)
  | unplug
  deriving BEq, DecidableEq, Repr
structure Outcome where
  status : Nat
  image : Image
  prepared : Nat
  deriving BEq, ReflBEq, LawfulBEq, DecidableEq, Repr

def target (s : Image) : Nat := s.recipe + 1
def okay (s : Image) : Outcome := ⟨0,s,0⟩
def refused (s : Image) : Outcome := ⟨1,s,0⟩
def materialize (p : Profile) (s : Image) : Image :=
  let selected := target s
  let location := if p == .yarn then 1 else selected
  let bytes := if s.recipe == 0 then 1 else 2
  {s with lock := selected,live := location,payload := bytes}

/-- Observed profile projection, not the complete source's admission algorithm.
    `lock == target` summarizes the measured up-to-date case; the full source
    has additional host/configuration/state premises not inferred here. -/
def installCurrent (p : Profile) (s : Image) (frozen force : Bool) : Outcome :=
  if frozen && s.lock != target s then refused s
  else if s.recipe == 2 then
    if p == .pnpm then ⟨1,{s with live := 3,payload := 1},0⟩ else refused s
  else if p == .pnpm && !force && s.lock == target s && s.payload != 0 then okay s
  else okay (materialize p s)

/-- Conservative alternative: private candidate failure preserves the old live
    scope; no reuse without a separately established backing admission proof.
    Efficient reuse and native publication remain implementation obligations. -/
def installProposed (p : Profile) (s : Image) (frozen : Bool) : Outcome :=
  if frozen && s.lock != target s then refused s
  else if s.recipe == 2 then refused s
  else okay (materialize p s)

def run (p : Profile) (s : Image) (a : Action) (proposed : Bool := false) : Outcome :=
  let install := fun image frozen force =>
    if proposed then installProposed p image frozen else installCurrent p image frozen force
  match a with
  | .observe => okay s
  | .prepare existing => ⟨0,s,if existing && s.recipe == 1 then 2 else 1⟩
  | .commit =>
    let saved := {s with recipe := 1,patchFile := true}
    if p == .pnpm then install saved false false else okay saved
  | .install frozen force => install s frozen force
  | .remove keyMatches =>
    if p == .pnpm && keyMatches then install {s with recipe := 0,patchFile := false} false false
    else refused s
  | .unplug => refused s

def empty : Image := ⟨0,0,0,0,false⟩
def base : Image := ⟨0,1,1,1,false⟩
def patched : Image := ⟨1,2,2,2,true⟩
def yarnPatched : Image := ⟨1,2,1,2,true⟩
def badAfterFailure : Image := ⟨2,2,3,1,true⟩
def restored : Image := {badAfterFailure with recipe := 1}

theorem initial_install_materializes_base :
    run .pnpm empty (.install false false) = ⟨0,base,0⟩ := by decide
theorem preparation_does_not_publish (p : Profile) (s : Image) (existing : Bool) :
    (run p s (.prepare existing)).image = s := rfl
theorem importing_existing_patch_differs_from_clean_preparation :
    (run .pnpm patched (.prepare true)).prepared = 2 ∧
    (run .yarn yarnPatched (.prepare false)).prepared = 1 := by decide
theorem pnpm_commit_installs_in_selected_profile :
    run .pnpm base .commit = ⟨0,patched,0⟩ := by decide
theorem yarn_save_is_not_installation :
    run .yarn base .commit = ⟨0,⟨1,1,1,1,true⟩,0⟩ := by decide
theorem immutable_install_refuses_saved_unresolved_patch :
    run .yarn ⟨1,1,1,1,true⟩ (.install true false) = ⟨1,⟨1,1,1,1,true⟩,0⟩ := by decide
theorem pnpm_bad_hunk_can_change_live_target :
    run .pnpm {patched with recipe := 2} (.install false false) = ⟨1,badAfterFailure,0⟩ := by decide
theorem yarn_bad_hunk_preserves_observed_live_scope :
    (run .yarn {yarnPatched with recipe := 2} (.install false false)).image = {yarnPatched with recipe := 2} := by decide
theorem current_success_need_not_restore_valid_payload :
    run .pnpm restored (.install false false) = ⟨0,restored,0⟩ := by decide
theorem force_repairs_observed_counterexample :
    run .pnpm restored (.install false true) = ⟨0,patched,0⟩ := by decide
theorem repeated_invalid_patch_is_still_refused :
    (run .pnpm ⟨2,1,3,1,true⟩ (.install false false)).status = 1 := by decide
theorem valid_patch_with_unpatched_lock_materializes :
    run .pnpm ⟨1,1,3,1,true⟩ (.install false false) = ⟨0,patched,0⟩ := by decide
theorem missing_selector_cannot_remove_another_patch :
    run .pnpm patched (.remove false) = ⟨1,patched,0⟩ := by decide
theorem pnpm_remove_and_install_differ_from_yarn_reference_edit :
    run .pnpm patched (.remove true) = ⟨0,base,0⟩ ∧
    (run .yarn {yarnPatched with recipe := 0} (.install false false)).image = ⟨0,1,1,1,true⟩ := by decide
theorem unplug_refusal_does_not_mean_unpatch :
    run .yarn yarnPatched .unplug = ⟨1,yarnPatched,0⟩ := by decide
theorem proposed_failure_preserves_live_scope (p : Profile) (s : Image) (h : s.recipe = 2) :
    (installProposed p s false).image = s := by simp [installProposed,h,refused]
theorem proposed_materialization_repairs_counterexample :
    run .pnpm restored (.install false false) true = ⟨0,patched,0⟩ := by decide
theorem selected_link_identity_alone_is_not_byte_evidence :
    (⟨1,2,2,1,true⟩ : Image).live = patched.live ∧
    (⟨1,2,2,1,true⟩ : Image).payload ≠ patched.payload := by decide
theorem flat_path_is_not_a_patch_identity :
    base.live = yarnPatched.live ∧ base.payload ≠ yarnPatched.payload := by decide
theorem conservative_alternative_keeps_old_target_then_restores :
    let failed := run .pnpm {patched with recipe := 2} (.install false false) true
    let valid := {failed.image with recipe := 1}
    failed.image.live = patched.live ∧ run .pnpm valid (.install false false) true = ⟨0,patched,0⟩ := by decide

end ApplicationStudy.JSPatches
