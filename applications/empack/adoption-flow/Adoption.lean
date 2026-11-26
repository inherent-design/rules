namespace ApplicationStudy.AdoptionFlow

/-- Selected single ordinary URL/local file, explicit placement, no declared digest or provider.
0 means absent/unrecorded; 1 and 2 identify the two generated payloads. -/
structure Request where
  firstLock : Bool
  allRoots : Bool
  repeated : Bool
  localSource : Bool
  sourceBytes : Nat
  installedBytes : Nat
  acceptedBefore : Nat
  preview : Bool
  deriving Repr, DecidableEq

def reason (r : Request) : Nat :=
  if r.repeated then 2
  else if r.firstLock && !r.allRoots then 1
  else if r.installedBytes == 0 then 3
  else if r.localSource && r.sourceBytes != r.installedBytes then 4
  else 0

def candidate (r : Request) : Nat := if reason r == 0 then r.installedBytes else 0
/-- Publication and changed documents are distinct; this profile omits no-op apply. -/
def publish (r : Request) : Bool := reason r == 0 && !r.preview

def acceptedAfter (r : Request) : Nat := if publish r then r.installedBytes else r.acceptedBefore

def documentsChanged (r : Request) : Bool := publish r && r.acceptedBefore != r.installedBytes

structure State where
  accepted : Nat
  installed : Nat
  sourceBytes : Nat
  deriving Repr, DecidableEq

def transition (r : Request) : State := ⟨acceptedAfter r,r.installedBytes,r.sourceBytes⟩

theorem duplicate_refused (r : Request) (h : r.repeated = true) : reason r = 2 := by
  simp [reason, h]
theorem incomplete_first_refused (r : Request) (d : r.repeated = false)
    (f : r.firstLock = true) (a : r.allRoots = false) : reason r = 1 := by
  simp [reason, d, f, a]
theorem absent_refused (r : Request) (d : r.repeated = false)
    (a : (r.firstLock && !r.allRoots) = false) (b : r.installedBytes = 0) : reason r = 3 := by
  simp [reason, d, a, b]
theorem mismatch_refused (r : Request) (d : r.repeated = false)
    (a : (r.firstLock && !r.allRoots) = false) (b : r.installedBytes ≠ 0)
    (l : r.localSource = true) (m : r.sourceBytes ≠ r.installedBytes) : reason r = 4 := by
  simp [reason, d, a, b, l, m]
theorem preview_preserves_accepted (r : Request) (h : r.preview = true) :
    acceptedAfter r = r.acceptedBefore := by simp [acceptedAfter, publish, h]
theorem preview_no_document_write (r : Request) (h : r.preview = true) :
    documentsChanged r = false := by simp [documentsChanged, publish, h]
theorem refusal_preserves_accepted (r : Request) (h : reason r ≠ 0) :
    acceptedAfter r = r.acceptedBefore := by simp [acceptedAfter, publish, h]
theorem refusal_has_no_candidate (r : Request) (h : reason r ≠ 0) : candidate r = 0 := by
  simp [candidate, h]
theorem publication_records_installed (r : Request) (h : publish r = true) :
    acceptedAfter r = r.installedBytes := by simp [acceptedAfter, h]
theorem installed_unchanged (r : Request) : (transition r).installed = r.installedBytes := by rfl
theorem source_unchanged (r : Request) : (transition r).sourceBytes = r.sourceBytes := by rfl
theorem unchanged_observation_no_document_change (r : Request)
    (h : r.acceptedBefore = r.installedBytes) : documentsChanged r = false := by
  simp [documentsChanged, h]

end ApplicationStudy.AdoptionFlow
