namespace ApplicationStudy.NpmCache

inductive Backing where
  | missing | verified | corrupt
  deriving BEq, DecidableEq, Repr
inductive Installation where
  | missing | original | editedFixture
  deriving BEq, DecidableEq, Repr
structure State where
  backing : Backing
  installed : Installation
  author : Nat -- selected package.json/.npmrc/lock byte image; not native authority
  deriving BEq, DecidableEq, Repr
structure Result where
  state : State
  exitCode : Nat
  requests : Nat
  deriving Repr

/-- One selected cache object. A live index reference is external evidence, not
    implied by a file's existence. This models neither the full index nor leases. -/
def verify (s : State) (referenced : Bool) : Result :=
  let kept := referenced && s.backing == .verified
  ⟨{s with backing := if kept then .verified else .missing},0,0⟩
/-- Closed one-package/no-script CI projection after metadata/lock admission.
    matchingIndex supplies this request's lookup witness; originReady supplies
    an admitted successful own-origin acquisition. No general fetch/IO proof. -/
def cleanInstall (s : State) (lockAdmitted matchingIndex originReady : Bool) : Result :=
  if !lockAdmitted then ⟨s,1,0⟩ else
  let hit := matchingIndex && s.backing == .verified
  let cleared := {s with installed := .missing}
  if hit || originReady then
    ⟨{cleared with backing := .verified,installed := .original},0,if hit then 0 else 1⟩
  else ⟨cleared,1,0⟩
/-- Owned fault/edit interventions, not npm public APIs. -/
def corruptBacking (s : State) : Result := ⟨{s with backing := .corrupt},0,0⟩
def editInstalled (s : State) : Result := ⟨{s with installed := .editedFixture},0,0⟩
def available (s : State) : Bool := s.installed != .missing
/-- Optional availability-first alternative. Its premises require a retained
    acquisition/lookup witness through clearing; a prior cache verify is not it. -/
def proposedPreflight (s : State) (lockAdmitted matchingIndex originReady : Bool) : Result :=
  if lockAdmitted && !(matchingIndex && s.backing == .verified || originReady) then ⟨s,1,0⟩
  else cleanInstall s lockAdmitted matchingIndex originReady

theorem verify_preserves_installed (s : State) (r : Bool) : (verify s r).state.installed = s.installed := rfl
theorem verify_preserves_author (s : State) (r : Bool) : (verify s r).state.author = s.author := rfl
theorem bad_backing_is_removed (s : State) (r : Bool) (h : s.backing = .corrupt) :
    (verify s r).state.backing = .missing ∧ (verify s r).exitCode = 0 := by
  cases r <;> simp [verify,h] <;> rfl
theorem unreferenced_good_content_is_not_a_retained_asset :
    (verify ⟨.verified,.original,1⟩ false).state.backing = .missing := by decide
theorem successful_cache_verify_does_not_restore_availability :
    (verify ⟨.corrupt,.missing,1⟩ true).exitCode = 0 ∧
    available (verify ⟨.corrupt,.missing,1⟩ true).state = false := by decide
theorem clean_install_preserves_author (s : State) (l i o : Bool) :
    (cleanInstall s l i o).state.author = s.author := by
  cases s with
  | mk b installed author => cases l <;> cases i <;> cases o <;> cases b <;> rfl
theorem lock_refusal_keeps_installation (s : State) (i o : Bool) :
    (cleanInstall s false i o).state = s := by simp [cleanInstall]
theorem missing_offline_payload_can_follow_clear :
    (cleanInstall ⟨.missing,.original,1⟩ true false false).state.installed = .missing ∧
    (cleanInstall ⟨.missing,.original,1⟩ true false false).exitCode = 1 := by decide
theorem a_file_without_matching_lookup_does_not_admit_cache_use :
    (cleanInstall ⟨.verified,.original,1⟩ true false false).exitCode = 1 := by decide
theorem matching_valid_cache_restores_original_without_network :
    (cleanInstall ⟨.verified,.editedFixture,1⟩ true true false).state.installed = .original ∧
    (cleanInstall ⟨.verified,.editedFixture,1⟩ true true false).requests = 0 := by decide
theorem own_origin_can_restore_missing_installation :
    (cleanInstall ⟨.missing,.missing,1⟩ true false true).state.installed = .original ∧
    (cleanInstall ⟨.missing,.missing,1⟩ true false true).requests = 1 := by decide
theorem verify_keeps_the_owned_installed_edit :
    (verify ⟨.verified,.editedFixture,1⟩ true).state.installed = .editedFixture := by decide
theorem proposed_preflight_preserves_old_installation_on_known_miss :
    (proposedPreflight ⟨.missing,.original,1⟩ true false false).state.installed = .original ∧
    (proposedPreflight ⟨.missing,.original,1⟩ true false false).exitCode = 1 := by decide

end ApplicationStudy.NpmCache
