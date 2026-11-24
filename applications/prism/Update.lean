namespace ApplicationStudy.Prism

structure PackFile where
  path : String
  hash : String
  deriving DecidableEq, Repr

/-- false is the inspected source filter; true is a proposed path-aware rule. -/
def canReuse (pathAware : Bool) (a b : PackFile) : Bool :=
  (a.hash == b.hash) && (!pathAware || a.path == b.path)

def consumeFirst (pathAware : Bool) (requested : PackFile) : List PackFile → Option (List PackFile)
  | [] => none
  | old :: tail =>
    if canReuse pathAware requested old then some tail
    else (consumeFirst pathAware requested tail).map (old :: ·)

structure Plan where
  pendingNew : List PackFile
  unmatchedOld : List PackFile
  deriving DecidableEq, Repr

def filterPlan (pathAware : Bool) : List PackFile → List PackFile → Plan
  | [], old => ⟨[], old⟩
  | head :: tail, old =>
    match consumeFirst pathAware head old with
    | some remaining => filterPlan pathAware tail remaining
    | none =>
      let rest := filterPlan pathAware tail old
      ⟨head :: rest.pendingNew, rest.unmatchedOld⟩

/-- Successful, required-only manifest reparse is an explicit surrounding-flow
    premise. This is not a model of optional dialogs or instance publication. -/
def creationDownloads (allNew : List PackFile) (p : Plan) : List PackFile :=
  if p.pendingNew.isEmpty then allNew else p.pendingNew

/-- Simulated overlay effect, not a native filesystem observation. -/
def applyPlan (installed allNew : List PackFile) (p : Plan) : List PackFile :=
  let downloads := creationDownloads allNew p
  installed.filter (fun f => !p.unmatchedOld.any (fun old => old.path == f.path) &&
    !downloads.any (fun new => new.path == f.path)) ++ downloads

theorem path_aware_reuse_requires_path (a b : PackFile) (h : canReuse true a b = true) :
    a.path = b.path := by
  simp [canReuse] at h
  exact h.2

theorem path_aware_reuse_requires_hash (a b : PackFile) (h : canReuse true a b = true) :
    a.hash = b.hash := by
  simp [canReuse] at h
  exact h.1

theorem path_aware_reuse_allows_hash_reuse (a b : PackFile) (h : canReuse true a b = true) :
    canReuse false a b = true := by
  simp [canReuse, path_aware_reuse_requires_hash a b h]

theorem empty_pending_reparses (files : List PackFile) (old : List PackFile) :
    creationDownloads files ⟨[], old⟩ = files := rfl

example : canReuse false ⟨"old", "same"⟩ ⟨"new", "same"⟩ = true := rfl
example : canReuse true ⟨"old", "same"⟩ ⟨"new", "same"⟩ = false := rfl

end ApplicationStudy.Prism
