namespace ApplicationStudy.PrismExport

/-- Finite projection of enumerated regular files and file links with existing targets.
Directory traversal has already completed; this is not a general filesystem model. -/
structure Entry where
  id : Nat
  leafHidden : Bool
  excluded : Bool
  missingAtWrite : Bool
  link : Bool
  deriving Repr, DecidableEq
structure Request where
  rootExists : Bool
  outputDirectory : Bool
  canceled : Bool -- Constant caller-supplied branch witness, not QFuture liveness.
  follow : Bool
  placement : Nat
  entries : List Entry
  extras : List Nat
  deriving Repr, DecidableEq
structure Member where
  id : Nat
  placement : Nat
  link : Bool
  deriving Repr, DecidableEq

/-- QDir::Files omits hidden leaves; directories were traversed with Hidden. -/
def selected (entries : List Entry) : List Entry :=
  entries.filter fun e => !e.leafHidden && !e.excluded

def member (follow : Bool) (placement : Nat) (e : Entry) : Member :=
  ⟨e.id, placement, e.link && !follow⟩

def writeFiles (follow : Bool) (placement : Nat) : List Entry → Nat × List Member
  | [] => (2, [])
  | e :: rest =>
    if e.missingAtWrite then (3, [])
    else let result := writeFiles follow placement rest
         (result.1, member follow placement e :: result.2)

/-- 0 collector declined; 1 open failed; 2 method completed; 3 read failed;
4 cancellation branch returned. Output mutation precedes entry processing. -/
def state (r : Request) : Nat :=
  if !r.rootExists then 0
  else if r.outputDirectory then 1
  else if r.canceled && (!(selected r.entries).isEmpty || !r.extras.isEmpty) then 4
  else (writeFiles r.follow r.placement (selected r.entries)).1

def members (r : Request) : List Member :=
  if !r.rootExists || r.outputDirectory then []
  else if r.canceled && (!(selected r.entries).isEmpty || !r.extras.isEmpty) then []
  else r.extras.map (fun id => ⟨id, 0, false⟩) ++
       (writeFiles r.follow r.placement (selected r.entries)).2

def errorPresent (s : Nat) : Bool := s == 1 || s == 3
/-- Opening the direct output replaces the previous ordinary file, including on failure. -/
def outputReplaced (r : Request) : Bool := r.rootExists && !r.outputDirectory
/-- Empty optional error alone does not establish completion. -/
def methodCompleted (r : Request) : Bool := state r == 2 && !r.canceled
/-- Design-only publication decision; no atomic staging implementation is executed. -/
def proposedPublish (s : Nat) (canceled : Bool) : Bool := s == 2 && !canceled

theorem hidden_leaf_omitted (e : Entry) (h : e.leafHidden = true) : selected [e] = [] := by
  simp [selected, h]
theorem excluded_omitted (e : Entry) (h : e.excluded = true) : selected [e] = [] := by
  simp [selected, h]
theorem visible_retained (e : Entry) (h : e.leafHidden = false) (x : e.excluded = false) :
    selected [e] = [e] := by simp [selected, h, x]
theorem follows_link_as_regular (e : Entry) (placement : Nat) : (member true placement e).link = false := by
  simp [member]
theorem retains_link (e : Entry) (h : e.link = true) (placement : Nat) :
    (member false placement e).link = true := by simp [member, h]
theorem placement_kept (e : Entry) (follow : Bool) (placement : Nat) :
    (member follow placement e).id = e.id ∧ (member follow placement e).placement = placement := by
  simp [member]
theorem missing_stops (e : Entry) (h : e.missingAtWrite = true) (rest : List Entry)
    (follow : Bool) (placement : Nat) : writeFiles follow placement (e :: rest) = (3, []) := by
  simp [writeFiles, h]
theorem empty_completes (follow : Bool) (placement : Nat) : writeFiles follow placement [] = (2, []) := by rfl
theorem cancellation_no_error : errorPresent 4 = false := by rfl
theorem read_failure_has_error : errorPresent 3 = true := by rfl
theorem open_failure_has_error : errorPresent 1 = true := by rfl
theorem missing_root_preserves (r : Request) (h : r.rootExists = false) :
    state r = 0 ∧ outputReplaced r = false ∧ members r = [] := by
  simp [state, outputReplaced, members, h]
theorem open_failure_preserves (r : Request) (h : r.outputDirectory = true) :
    outputReplaced r = false := by simp [outputReplaced, h]
theorem canceled_not_completed (r : Request) (h : r.canceled = true) : methodCompleted r = false := by
  simp [methodCompleted, h]
theorem proposed_failure_keeps : proposedPublish 3 false = false := by rfl
theorem proposed_canceled_keeps (s : Nat) : proposedPublish s true = false := by
  simp [proposedPublish]

end ApplicationStudy.PrismExport
