namespace ApplicationStudy.ResticLocks

/-- Observation projection, not the serialized restic Lock type. `reachable`
    describes the current Unix SIGHUP probe result; it is not authenticated
    creator identity or a universal proof that a process is alive/absent. -/
structure LockView where
  token : String
  owner : Nat
  exclusive : Bool
  readable : Bool := true
  emptyUpload : Bool := false
  old : Bool := false
  sameHost : Bool := true
  reachable : Bool := true
  deriving Repr

def admitted (exclusive : Bool) (locks : List LockView) : Bool :=
  locks.all (fun lock => lock.emptyUpload ||
    (lock.readable && !(exclusive || lock.exclusive)))

/-- Source policy: age expiry, or same-host failure to reach the PID.
    This function deliberately does not improve the source's error taxonomy. -/
def stale (lock : LockView) : Bool := lock.old || (lock.sameHost && !lock.reachable)

def ordinaryUnlock (locks : List LockView) : List LockView :=
  locks.filter (fun lock => !(lock.readable && !lock.emptyUpload && stale lock))

/-- Apply observed retirement/cleanup evidence, not an assumption that unlock
    always succeeds. Native cases supply one known record per owner and no
    refresh overlap; true cleanup means those selected records disappeared. -/
def retired (owner : Nat) (cleanup : Bool) (locks : List LockView) : List LockView :=
  if cleanup then locks.filter (fun lock => lock.owner != owner)
  else locks.map (fun lock => if lock.owner == owner then { lock with reachable := false } else lock)

def tokens (locks : List LockView) : List String := locks.map (·.token)

/-- Observable publication is weaker evidence than a confirmed successful
    admission. `published` means admission is unknown, not known false. -/
inductive Evidence | none | published | confirmedAdmission
  deriving BEq, DecidableEq, Repr

def canClaimAdmission : Evidence → Bool
  | .confirmedAdmission => true | _ => false

structure Runtime where
  stopRequested : Bool
  retirementConfirmed : Bool
  deriving BEq, DecidableEq, Repr

def requestStop (runtime : Runtime) : Runtime := { runtime with stopRequested := true }

inductive Probe | reachable | absent | unknown
  deriving BEq, DecidableEq, Repr

/-- Candidate classification: do not turn permission/observation failure into
    absence. Keep the existing age-expiry policy separate. Not implemented. -/
def candidateStale (old sameHost : Bool) (probe : Probe) : Bool :=
  old || (sameHost && probe == .absent)

theorem no_locks_admit (exclusive : Bool) : admitted exclusive [] = true := rfl

theorem shared_compatible (a b : String) (x y : Nat) :
    admitted false [{token:=a,owner:=x,exclusive:=false},{token:=b,owner:=y,exclusive:=false}] = true := rfl

theorem exclusive_conflicts_with_shared (token : String) (owner : Nat) :
    admitted true [{token:=token,owner:=owner,exclusive:=false}] = false := rfl

theorem published_exclusive_blocks_append (token : String) (owner : Nat) :
    admitted false [{token:=token,owner:=owner,exclusive:=true}] = false := rfl

theorem unreadable_is_not_absent (exclusive : Bool) (token : String) (owner : Nat) :
    admitted exclusive [{token:=token,owner:=owner,exclusive:=false,readable:=false}] = false := rfl

theorem ordinary_unlock_keeps_live (token : String) (owner : Nat) :
    tokens (ordinaryUnlock [{token:=token,owner:=owner,exclusive:=false}]) = [token] := rfl

theorem dead_record_blocks_until_removed (token : String) (owner : Nat) :
    let lock : LockView := { token := token, owner := owner, exclusive := false, reachable := false }
    admitted true [lock] = false ∧ tokens (ordinaryUnlock [lock]) = [] := by constructor <;> rfl

theorem abrupt_retirement_keeps_lock_identity (owner : Nat) (locks : List LockView) :
    tokens (retired owner false locks) = tokens locks := by
  simp only [retired, Bool.false_eq_true, ↓reduceIte, tokens, List.map_map]
  congr 1
  funext lock
  dsimp only [Function.comp_def]
  split <;> rfl

theorem published_is_not_admission_evidence : canClaimAdmission .published = false := rfl

theorem stop_request_does_not_confirm_retirement (runtime : Runtime) :
    (requestStop runtime).retirementConfirmed = runtime.retirementConfirmed := rfl

theorem candidate_preserves_unknown_owner : candidateStale false true .unknown = false := rfl

theorem source_negative_probe_can_remove (token : String) (owner : Nat) :
    stale { token := token, owner := owner, exclusive := false, reachable := false } = true := rfl

end ApplicationStudy.ResticLocks
