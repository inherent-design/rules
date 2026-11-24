namespace ApplicationStudy.ResticCopy

/-- The external decoder labels the scalar time/tree/host/user fields together.
    Snapshot IDs, persistent Original, lineage, and field comparison stay distinct.
    This does not hash, decrypt, transfer, or authorize repository objects. -/
structure Snapshot where
  id : Nat
  original : Option Nat
  parent : Option Nat
  fixed : Nat
  paths : List Nat
  tags : List Nat
  excludes : List Nat
  ignored : Nat -- ProgramVersion/Summary are not compared by similarSnapshots
  deriving BEq, DecidableEq, Repr

def persistent (s : Snapshot) : Nat := s.original.getD s.id
def containsAll (available requested : List Nat) : Bool := requested.all available.contains
/-- This follows the source's equal-length plus membership policy; it is not
    multiset equality. Duplicate-bearing inputs need a separate reachability check. -/
def similar (destination source : Snapshot) : Bool :=
  destination.fixed == source.fixed &&
  destination.paths.length == source.paths.length &&
  destination.tags.length == source.tags.length &&
  destination.excludes == source.excludes &&
  containsAll destination.paths source.paths && containsAll destination.tags source.tags
def indexed (d : Snapshot) (key : Nat) : Bool :=
  d.id == key || d.original.any (fun n => n != 0 && n == key)
def skip (s : Snapshot) (destination : List Snapshot) : Bool :=
  destination.any (fun d => indexed d (persistent s) && similar d s)
def copied (s : Snapshot) (admittedId : Nat) : Snapshot :=
  {s with id := admittedId,original := some (persistent s),parent := none}
/-- 12 is this fixture's source-key refusal, 0 skipped, 1 needs copy. A needs-copy
    decision is not a saved destination snapshot or a data-finalization receipt. -/
def decision (s : Snapshot) (destination : List Snapshot) (sourceKeyAccepted : Bool) : Nat :=
  if !sourceKeyAccepted then 12 else if skip s destination then 0 else 1

theorem existing_original_is_preserved (s : Snapshot) (id original : Nat)
    (h : s.original = some original) : (copied s id).original = some original := by simp [copied,persistent,h]
theorem first_copy_records_source_id (s : Snapshot) (id : Nat) (h : s.original = none) :
    (copied s id).original = some s.id := by simp [copied,persistent,h]
theorem copy_drops_parent (s : Snapshot) (id : Nat) : (copied s id).parent = none := rfl
theorem copy_preserves_compared_fields (s : Snapshot) (id : Nat) :
    (copied s id).fixed = s.fixed ∧ (copied s id).tags = s.tags ∧
    (copied s id).paths = s.paths ∧ (copied s id).excludes = s.excludes := by simp [copied]
theorem transitive_copy_keeps_persistent_identity (s : Snapshot) (b c : Nat) :
    persistent (copied (copied s b) c) = persistent s := by simp [persistent,copied]
theorem parent_is_not_a_similarity_input (a b : Snapshot) (parent : Option Nat) :
    similar {a with parent := parent} b = similar a b := rfl
theorem summary_and_program_are_not_similarity_inputs (a b : Snapshot) (ignored : Nat) :
    similar {a with ignored := ignored} b = similar a b := rfl
theorem source_key_refusal_precedes_selection (s : Snapshot) (ds : List Snapshot) :
    decision s ds false = 12 := by simp [decision]
theorem empty_destination_needs_copy (s : Snapshot) : decision s [] true = 1 := by simp [decision,skip]

private def sample (id : Nat) (tags : List Nat) : Snapshot := ⟨id,none,none,1,[1],tags,[],1⟩
theorem equal_tree_and_metadata_without_origin_does_not_skip :
    skip (sample 1 [1]) [sample 2 [1]] = false := by decide
theorem same_origin_with_changed_tags_is_another_copy :
    skip (sample 1 [1]) [{sample 2 [1,2] with original := some 1}] = false := by decide
theorem exact_existing_copy_skips :
    skip (sample 1 [1]) [copied (sample 1 [1]) 2] = true := by decide
theorem destination_id_is_an_external_admitted_result (s : Snapshot) (id : Nat) :
    (copied s id).id = id := rfl
theorem duplicate_tags_make_the_source_predicate_asymmetric :
    similar (sample 1 [1,2]) (sample 2 [1,1]) = true ∧
    similar (sample 2 [1,1]) (sample 1 [1,2]) = false := by decide

end ApplicationStudy.ResticCopy
