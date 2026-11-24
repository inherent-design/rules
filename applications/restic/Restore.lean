namespace ApplicationStudy.ResticRestore

inductive Policy | always | ifChanged | ifNewer | never
  deriving BEq, ReflBEq, LawfulBEq, DecidableEq, Repr
inductive Existing | missing | correct | different | symlink
  deriving BEq, ReflBEq, LawfulBEq, DecidableEq, Repr
inductive TimeOrder | older | equal | newer
  deriving BEq, ReflBEq, LawfulBEq, DecidableEq, Repr
inductive Action | skip | metadataOnly | rewrite
  deriving BEq, ReflBEq, LawfulBEq, DecidableEq, Repr

structure FileRequest where
  policy : Policy
  existing : Existing
  time : TimeOrder
  sameSize : Bool
  selected : Bool := true
  dry : Bool := false
  verify : Bool := true
  valid : Bool := true
  deriving Repr

/-- Current single-node policy projection. Missing destinations are eligible
    under every policy; if-newer compares snapshot mtime strictly. -/
def eligible (r : FileRequest) : Bool :=
  if r.existing == .missing then true else
  match r.policy with
  | .always | .ifChanged => true
  | .ifNewer => r.time == .older
  | .never => false

def trustsMetadata (r : FileRequest) : Bool :=
  r.existing == .different && r.policy == .ifChanged && r.time == .equal && r.sameSize

def action (r : FileRequest) : Action :=
  if !r.valid || !r.selected || !eligible r then .skip
  else if r.existing == .correct || trustsMetadata r then .metadataOnly
  else .rewrite

def writes (r : FileRequest) : Bool := !r.dry && action r == .rewrite
def after (r : FileRequest) : Existing := if writes r then .correct else r.existing

/-- Source-derived verification scope, not a measured native read counter.
    Metadata-only and policy-skipped files are excluded by VerifyFiles. -/
def verifies (r : FileRequest) : Bool := r.verify && writes r

inductive Filter | all | excludeRootFile | excludeChild | excludeDirectory | includeAlpha
  deriving BEq, ReflBEq, LawfulBEq, DecidableEq, Repr

structure ExtraState where
  rootFile : Bool
  directory : Bool
  protectedChild : Bool
  otherChild : Bool
  deriving BEq, DecidableEq, Repr

def fullExtras : ExtraState := ⟨true, true, true, true⟩

def rootSelected (f : Filter) : Bool := f != .excludeRootFile && f != .includeAlpha
def directorySelected (f : Filter) : Bool := f != .excludeDirectory && f != .includeAlpha

/-- Current RemoveAll projection: child exclusions are not reapplied below an
    unexpected selected directory. Only the owned fixed extra subtree is modeled. -/
def deleteCurrent (remove dry valid : Bool) (f : Filter) (s : ExtraState) : ExtraState :=
  let allowed := remove && !dry && valid
  let rootRemoved := allowed && rootSelected f
  let directoryRemoved := allowed && directorySelected f
  { rootFile := s.rootFile && !rootRemoved
    directory := s.directory && !directoryRemoved
    protectedChild := s.protectedChild && !directoryRemoved
    otherChild := s.otherChild && !directoryRemoved }

/-- Proposed leaf-aware deletion for this tiny tree. Retaining an excluded child
    retains its parent. This is not an implemented recursive filesystem algorithm. -/
def deleteProposed (remove dry valid : Bool) (f : Filter) (s : ExtraState) : ExtraState :=
  let allowed := remove && !dry && valid
  let parentSelected := directorySelected f
  let keptChild := s.protectedChild && !(allowed && parentSelected && f != .excludeChild)
  let other := s.otherChild && !(allowed && parentSelected)
  { rootFile := s.rootFile && !(allowed && rootSelected f)
    directory := s.directory && (!allowed || !parentSelected || keptChild || other)
    protectedChild := keptChild
    otherChild := other }

theorem missing_never_is_created :
    after ⟨.never, .missing, .equal, false, true, false, true, true⟩ = .correct := rfl

theorem never_keeps_existing_content (e : Existing) (t : TimeOrder) (size : Bool)
    (h : e ≠ .missing) : after ⟨.never, e, t, size, true, false, true, true⟩ = e := by
  cases e <;> cases t <;> cases size <;> simp_all [after, writes, action, eligible]

theorem equal_mtime_is_not_newer :
    after ⟨.ifNewer, .different, .equal, true, true, false, true, true⟩ = .different := rfl

theorem newer_target_is_preserved :
    after ⟨.ifNewer, .different, .newer, true, true, false, true, true⟩ = .different := rfl

theorem older_target_is_replaced :
    after ⟨.ifNewer, .different, .older, true, true, false, true, true⟩ = .correct := rfl

theorem matching_metadata_can_keep_wrong_bytes :
    after ⟨.ifChanged, .different, .equal, true, true, false, true, true⟩ = .different := rfl

theorem verify_does_not_check_metadata_only_file :
    verifies ⟨.ifChanged, .different, .equal, true, true, false, true, true⟩ = false := rfl

theorem always_repairs_same_metadata_counterexample :
    after ⟨.always, .different, .equal, true, true, false, true, true⟩ = .correct ∧
    verifies ⟨.always, .different, .equal, true, true, false, true, true⟩ = true := ⟨rfl, rfl⟩

theorem changed_metadata_causes_content_check :
    after ⟨.ifChanged, .different, .newer, true, true, false, true, true⟩ = .correct := rfl

theorem dry_preserves_file (r : FileRequest) :
    after {r with dry := true} = r.existing := by simp [after, writes]

theorem invalid_request_preserves_file (r : FileRequest) :
    after {r with valid := false} = r.existing := by simp [after, writes, action]

theorem unselected_file_is_not_written (r : FileRequest) :
    writes {r with selected := false} = false := by simp [writes, action]

theorem symlink_replaced_as_target_node :
    after ⟨.always, .symlink, .equal, false, true, false, true, true⟩ = .correct := rfl

theorem dry_deletion_preserves_extras (remove valid : Bool) (f : Filter) (s : ExtraState) :
    deleteCurrent remove true valid f s = s := by cases s; simp [deleteCurrent]

theorem invalid_deletion_preserves_extras (remove dry : Bool) (f : Filter) (s : ExtraState) :
    deleteCurrent remove dry false f s = s := by cases s; simp [deleteCurrent]

theorem current_excludes_root_file :
    (deleteCurrent true false true .excludeRootFile fullExtras).rootFile = true := rfl

theorem current_excludes_whole_directory :
    (deleteCurrent true false true .excludeDirectory fullExtras).protectedChild = true := rfl

theorem current_loses_excluded_descendant :
    (deleteCurrent true false true .excludeChild fullExtras).protectedChild = false := rfl

theorem proposed_preserves_excluded_descendant_and_parent :
    (deleteProposed true false true .excludeChild fullExtras).protectedChild = true ∧
    (deleteProposed true false true .excludeChild fullExtras).directory = true := ⟨rfl, rfl⟩

theorem proposed_still_removes_eligible_sibling :
    (deleteProposed true false true .excludeChild fullExtras).otherChild = false := rfl

end ApplicationStudy.ResticRestore
