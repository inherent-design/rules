namespace ApplicationStudy.EmpackWorlds

/-- One incoming group after side/choice projection. Roots have already been
    validated and portable overlap computed by the caller. Observation errors
    are not an `occupied = false` witness. -/
structure Basis where
  recorded : Bool
  oldGroup : Bool
  incoming : Bool
  overlapsProtected : Bool
  occupied : Bool
  deriving Repr

/-- Candidate metadata; preparation alone does not persist this value. Native
    comparisons below use only successful completed installations. -/
def initialized (b : Basis) : Bool := b.recorded || b.oldGroup || b.incoming
def protectedGroup (b : Basis) : Bool :=
  b.recorded || b.oldGroup || (b.incoming && (b.overlapsProtected || b.occupied))
def planMembers (b : Basis) : Bool := b.incoming && !protectedGroup b
def needsAbsentCapture (b : Basis) : Bool := planMembers b

theorem recorded_group_is_protected (old incoming overlap occupied : Bool) :
    protectedGroup ⟨true, old, incoming, overlap, occupied⟩ = true := rfl
theorem omitted_group_keeps_initialization (old overlap occupied : Bool) :
    initialized ⟨true, old, false, overlap, occupied⟩ = true := rfl
theorem reintroduction_does_not_reseed (old overlap occupied : Bool) :
    planMembers ⟨true, old, true, overlap, occupied⟩ = false := rfl
theorem old_inventory_also_initializes (incoming overlap occupied : Bool) :
    initialized ⟨false, true, incoming, overlap, occupied⟩ = true := rfl
theorem occupied_group_is_not_filled :
    planMembers ⟨false, false, true, false, true⟩ = false := rfl
theorem overlapping_group_is_not_filled (occupied : Bool) :
    planMembers ⟨false, false, true, true, occupied⟩ = false := rfl
theorem fresh_group_requires_absent_capture :
    planMembers ⟨false, false, true, false, false⟩ = true ∧
    needsAbsentCapture ⟨false, false, true, false, false⟩ = true := by decide

/-- This is a publication obligation, not the complete native snapshot API.
    Both the captured absence and later currency must be established. -/
def mayPublishNewSeed (b : Basis) (capturedAbsent stillCurrent : Bool) : Bool :=
  planMembers b && capturedAbsent && stillCurrent
theorem stale_absence_does_not_authorize (b : Basis) (captured : Bool) :
    mayPublishNewSeed b captured false = false := by simp [mayPublishNewSeed]
theorem planning_is_not_publication (b : Basis) (current : Bool) :
    mayPublishNewSeed b false current = false := by simp [mayPublishNewSeed]

end ApplicationStudy.EmpackWorlds
