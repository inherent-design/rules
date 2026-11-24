namespace ApplicationStudy.Restic

/-- Opaque exact identities: a parent ID is not a lifetime grant. -/
structure Snapshot where
  id : String
  parent : Option String
  reachableData : List String
  deriving DecidableEq, Repr

/-- Projection of plaintext blob availability, not physical encrypted pack IDs.
    reachableData must be a complete traversal for the selected projection.
    This is not an implementation of the repository's tree decoder. -/
structure Repository where
  snapshots : List Snapshot
  availableData : List String
  deriving DecidableEq, Repr

def retained (r : Repository) (blob : String) : Bool :=
  r.snapshots.any (fun s => s.reachableData.contains blob)

def forget (id : String) (r : Repository) : Repository :=
  { r with snapshots := r.snapshots.filter (fun s => s.id != id) }

/-- Selected full-reclamation recipe (the fixture passes --max-unused 0).
    Complete stationary roots and exclusive coordination are host premises.
    Partial-prune modes and unsafe no-lock overrides are not represented.
    The refusal branch is the proposed safe admission boundary, not a claim
    that every restic flag combination enforces this witness. -/
def prune (exclusive : Bool) (r : Repository) : Repository :=
  if exclusive then
    { r with availableData := r.availableData.filter (retained r) }
  else r

theorem forget_preserves_data (id : String) (r : Repository) :
    (forget id r).availableData = r.availableData := rfl

theorem no_exclusive_no_reclamation (r : Repository) : prune false r = r := rfl

theorem retained_available_survives (r : Repository) (blob : String)
    (available : blob ∈ r.availableData) (held : retained r blob = true) :
    blob ∈ (prune true r).availableData := by
  simp [prune, available, held]

theorem shared_snapshot_holds (r : Repository) (s : Snapshot) (blob : String)
    (live : s ∈ r.snapshots) (member : blob ∈ s.reachableData) :
    retained r blob = true := by
  simp only [retained, List.any_eq_true]
  exact ⟨s, live, by simpa using member⟩

theorem changing_lineage_does_not_change_retention (r : Repository) (blob : String) :
    retained { r with snapshots := r.snapshots.map (fun s => { s with parent := none }) } blob =
      retained r blob := by
  simp [retained, Function.comp_def]

theorem prune_is_idempotent (r : Repository) :
    prune true (prune true r) = prune true r := by
  cases r with
  | mk snapshots available =>
    let p := fun blob => snapshots.any (fun s => s.reachableData.contains blob)
    change Repository.mk snapshots ((available.filter p).filter p) =
      Repository.mk snapshots (available.filter p)
    have filtered : (available.filter p).filter p = available.filter p := by
      rw [List.filter_filter]
      apply List.filter_congr
      intro blob _
      cases p blob <;> rfl
    exact congrArg (Repository.mk snapshots) filtered

example : retained ⟨[⟨"B", some "A", ["shared", "new"]⟩], ["old", "shared", "new"]⟩ "old" = false := rfl
example : (forget "A" ⟨[⟨"A", none, ["old"]⟩, ⟨"B", some "A", ["new"]⟩], ["old", "new"]⟩).snapshots.length = 1 := rfl

end ApplicationStudy.Restic
