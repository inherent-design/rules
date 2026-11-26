namespace ApplicationStudy.CargoLockSources

/-- Selected fixture identities. Path/patch origins remain distinct even when
    source is null in metadata; Git revisions share a logical package key. -/
inductive Selection | missing | pathV1 | pathV2 | gitA | gitB | patched
  deriving Repr, BEq, DecidableEq
inductive Source | path | git | patch
  deriving Repr, BEq, DecidableEq
inductive Operation | metadata | generate | update
  deriving Repr, BEq, DecidableEq

def selectionId : Selection → Nat
  | .missing => 0 | .pathV1 => 1 | .pathV2 => 2 | .gitA => 3 | .gitB => 4 | .patched => 5
def packageKey : Selection → Nat
  | .missing => 0 | .pathV1 => 1 | .pathV2 => 2 | .gitA | .gitB => 3 | .patched => 4
def gitRevision : Selection → Nat
  | .gitA => 1 | .gitB => 2 | _ => 0
def revisionSelection : Nat → Selection
  | 1 => .gitA | 2 => .gitB | _ => .missing

structure Cache where
  head : Nat
  hasA : Bool
  hasB : Bool
  deriving Repr, BEq, DecidableEq

def cacheMask (c : Cache) : Nat := (if c.hasA then 1 else 0) + (if c.hasB then 2 else 0)
def cached (c : Cache) : Selection → Bool
  | .gitA => c.hasA | .gitB => c.hasB | _ => false
def retain (c : Cache) (s : Selection) : Cache :=
  ⟨gitRevision s, c.hasA || s == .gitA, c.hasB || s == .gitB⟩

structure Request where
  source : Source
  operation : Operation
  locked : Bool
  offline : Bool
  pathV2 : Bool
  remoteB : Bool
  beforeLock : Selection
  cache : Cache
  deriving Repr

/-- Candidate selection is a premise-bounded projection: one dependency,
    two known Git commits, one compatible patch, no registry resolution. -/
def desired (r : Request) : Selection :=
  match r.source with
  | .path => if r.pathV2 then .pathV2 else .pathV1
  | .patch => .patched
  | .git =>
    if r.operation == .metadata && gitRevision r.beforeLock != 0 then r.beforeLock
    else if r.offline then revisionSelection r.cache.head
    else if r.remoteB then .gitB else .gitA

structure Outcome where
  code : Nat
  afterLock : Selection
  cache : Cache
  metadata : Selection
  selectionChanged : Bool
  deriving Repr, BEq, DecidableEq

def run (r : Request) : Outcome :=
  let wanted := desired r
  let needsGit := r.source == .git
  let available := wanted != .missing && (!needsGit || cached r.cache wanted || !r.offline)
  let nextCache := if needsGit && available && !cached r.cache wanted then retain r.cache wanted else r.cache
  if !available then ⟨101, r.beforeLock, r.cache, .missing, false⟩
  else if r.locked && r.beforeLock != wanted then ⟨101, r.beforeLock, nextCache, .missing, false⟩
  else ⟨0, wanted, nextCache, if r.operation == .metadata then wanted else .missing, r.beforeLock != wanted⟩

def observed (o : Outcome) : List Nat :=
  [o.code, selectionId o.afterLock, o.cache.head, cacheMask o.cache,
   selectionId o.metadata, packageKey o.metadata, if o.selectionChanged then 1 else 0]

def emptyCache : Cache := ⟨0, false, false⟩
def cacheA : Cache := ⟨1, true, false⟩

theorem git_key_is_not_precise_revision : packageKey .gitA = packageKey .gitB ∧ Selection.gitA ≠ .gitB := by decide
theorem same_version_patch_is_a_different_origin : packageKey .gitA ≠ packageKey .patched := by decide
theorem path_source_null_cannot_identify_origin : packageKey .pathV1 ≠ packageKey .patched := by decide
theorem offline_path_can_create_lock :
    observed (run ⟨.path, .generate, false, true, false, false, .missing, emptyCache⟩) = [0,1,0,0,0,0,1] := by decide
theorem frozen_missing_path_lock_refuses :
    observed (run ⟨.path, .metadata, true, true, false, false, .missing, emptyCache⟩) = [101,0,0,0,0,0,0] := by decide
theorem semantic_same_lock_does_not_change_selection :
    (run ⟨.path, .metadata, true, true, false, false, .pathV1, emptyCache⟩).selectionChanged = false := by decide
theorem changed_path_lock_is_preserved_on_refusal :
    (run ⟨.path, .metadata, true, true, true, false, .pathV1, emptyCache⟩).afterLock = .pathV1 := by decide
theorem cold_offline_git_refuses_before_lock_creation :
    observed (run ⟨.git, .metadata, false, true, false, false, .missing, emptyCache⟩) = [101,0,0,0,0,0,0] := by decide
theorem locked_refusal_can_retain_cache_effect :
    observed (run ⟨.git, .metadata, true, false, false, false, .missing, emptyCache⟩) = [101,0,1,1,0,0,0] := by decide
theorem frozen_uses_retained_git_revision :
    observed (run ⟨.git, .metadata, true, true, false, true, .gitA, cacheA⟩) = [0,3,1,1,3,3,0] := by decide
theorem offline_update_does_not_claim_latest_source :
    (run ⟨.git, .update, false, true, false, true, .gitA, cacheA⟩).afterLock = .gitA := by decide
theorem online_local_update_changes_commit_without_changing_key :
    observed (run ⟨.git, .update, false, false, false, true, .gitA, cacheA⟩) = [0,4,2,3,0,0,1] := by decide
theorem locked_patch_refuses_source_switch :
    (run ⟨.patch, .metadata, true, true, false, true, .gitB, ⟨2,true,true⟩⟩).code = 101 := by decide
theorem offline_patch_can_change_source :
    observed (run ⟨.patch, .metadata, false, true, false, true, .gitB, ⟨2,true,true⟩⟩) = [0,5,2,3,5,4,1] := by decide

end ApplicationStudy.CargoLockSources
