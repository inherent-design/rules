namespace ApplicationStudy.VscodeHandles

/-- Two registrations into an otherwise empty registry, with equal basenames.
    `freshReceiver` drops the first registration's in-memory maps, not IDB.
    Same entry implies the same kind. Case-folding and more names are omitted. -/
structure PairInput where
  firstFile : Bool
  secondFile : Bool
  sameEntry : Bool
  freshReceiver : Bool
  deriving Repr

def secondGetsSuffix (p : PairInput) : Bool :=
  !p.freshReceiver && (p.firstFile == p.secondFile) && !p.sameEntry

/-- Which underlying entry resolves through the first returned URI. -/
def currentIsFirst (p : PairInput) : Bool :=
  if secondGetsSuffix p then true
  else if p.freshReceiver then p.sameEntry
  else if p.firstFile then true
  else if p.secondFile then p.sameEntry
  else true

def currentIsSecond (p : PairInput) : Bool :=
  if secondGetsSuffix p then p.sameEntry
  else if p.freshReceiver then true
  else if p.firstFile then p.sameEntry
  else if p.secondFile then true
  else p.sameEntry

/-- A successful later put replaces the shared IDB key unless suffixed. -/
def persistedIsFirst (p : PairInput) : Bool :=
  if secondGetsSuffix p then true else p.sameEntry

def persistedIsSecond (p : PairInput) : Bool :=
  if secondGetsSuffix p then p.sameEntry else true

theorem distinct_same_kind_suffix (kind : Bool) :
    secondGetsSuffix ⟨kind, kind, false, false⟩ = true := by
  cases kind <;> rfl

theorem cross_kind_alias_collision :
    secondGetsSuffix ⟨true, false, false, false⟩ = false := rfl

theorem file_directory_memory_and_store_disagree :
    currentIsFirst ⟨true, false, false, false⟩ = true ∧
    persistedIsFirst ⟨true, false, false, false⟩ = false := by decide

theorem unloaded_alias_can_rebind :
    secondGetsSuffix ⟨true, true, false, true⟩ = false ∧
    currentIsFirst ⟨true, true, false, true⟩ = false := by decide

/-- Proposed registry: stable opaque keys address immutable entry bindings.
    Allocation, permissions, persistence, and migration are separate proofs. -/
structure HandleRef where
  file : Bool
  entry : Nat
  deriving DecidableEq, Repr

abbrev Registry := Nat → Option HandleRef

def bindFresh (registry : Registry) (key : Nat) (handle : HandleRef) : Registry :=
  if (registry key).isSome then registry
  else fun lookup => if lookup == key then some handle else registry lookup

theorem occupied_key_not_rebound (r : Registry) (key : Nat) (old next : HandleRef)
    (h : r key = some old) : bindFresh r key next key = some old := by
  simp [bindFresh, h]

theorem fresh_key_is_bound (r : Registry) (key : Nat) (next : HandleRef)
    (h : r key = none) : bindFresh r key next key = some next := by
  simp [bindFresh, h]

theorem other_keys_unchanged (r : Registry) (key other : Nat) (next : HandleRef)
    (h : other ≠ key) : bindFresh r key next other = r other := by
  unfold bindFresh
  split <;> simp [h]

end ApplicationStudy.VscodeHandles
