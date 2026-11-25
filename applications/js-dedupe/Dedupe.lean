import Std

namespace ApplicationStudy.Dedupe
/-- Labels stand for exact selected versions in a single-name, two-parent
    fixture. They are not semver, peer contexts, payloads, or global roots. -/
structure Selection where
  left : Nat
  right : Nat
  copies : Nat
  deriving BEq, DecidableEq, Repr
structure Plan where
  before : Selection
  proposed : Selection
  allowedLeft : List Nat
  allowedRight : List Nat
  deriving Repr
def admitted (p : Plan) : Bool :=
  p.allowedLeft.contains p.proposed.left && p.allowedRight.contains p.proposed.right &&
  (p.proposed.copies == 1 || p.proposed.copies == 2) &&
  (p.proposed.copies != 1 || p.proposed.left == p.proposed.right)
def changes (p : Plan) : Bool := p.before != p.proposed
structure Outcome where
  selected : Selection
  status : Nat
  selectionChanged : Bool
  placementChanged : Bool
  manifestChanged : Bool
  deriving Repr
/-- `npmStyle` describes the preview status contract. The plan must come from
    the selected program; the model does not invent a shared resolver. Extra
    cache/log/install-state writes are outside these principal effect fields. -/
def run (npmStyle check : Bool) (p : Plan) : Outcome :=
  if !admitted p then ⟨p.before,2,false,false,false⟩ else
  if check then ⟨p.before,if npmStyle || !changes p then 0 else 1,false,false,false⟩ else
  ⟨p.proposed,0,p.before.left != p.proposed.left || p.before.right != p.proposed.right,
    p.before.copies != p.proposed.copies,false⟩

/-- Yarn's selected highest strategy uses saved locator candidates. The caller
    supplies resolver-admitted allowed labels; this is not a semver parser. -/
def highest (current : Nat) (allowed candidates : List Nat) : Nat :=
  (candidates.filter allowed.contains).foldl max current

theorem preview_preserves_selection (npm : Bool) (p : Plan) :
    (run npm true p).selected = p.before := by
  unfold run; split <;> simp
theorem preview_preserves_principal_effects (npm : Bool) (p : Plan) :
    (run npm true p).selectionChanged = false ∧
    (run npm true p).placementChanged = false := by
  unfold run; split <;> simp
theorem invalid_proposal_preserves (npm check : Bool) (p : Plan) (h : admitted p = false) :
    (run npm check p).selected = p.before ∧ (run npm check p).status = 2 := by simp [run,h]
theorem npm_preview_zero_is_not_no_changes (p : Plan) (h : admitted p = true) :
    (run true true p).status = 0 := by simp [run,h]
theorem explicit_check_exits_nonzero_on_change (p : Plan)
    (h : admitted p = true) (changed : changes p = true) :
    (run false true p).status = 1 := by simp [run,h,changed]
theorem application_uses_the_proposal (npm : Bool) (p : Plan) (h : admitted p = true) :
    (run npm false p).selected = p.proposed := by simp [run,h]
theorem keeps_authored_manifest (npm check : Bool) (p : Plan) :
    (run npm check p).manifestChanged = false := by
  unfold run; split <;> simp; split <;> rfl
theorem unchanged_explicit_check_succeeds (p : Plan)
    (h : admitted p = true) (same : changes p = false) :
    (run false true p).status = 0 := by simp [run,h,same]
theorem saved_highest_excludes_unoffered_catalog_version :
    highest 1 [1,2,3] [1,2] = 2 := by decide
theorem exact_constraint_keeps_its_version :
    highest 1 [1] [1,2,3] = 1 := by decide
theorem distinct_versions_can_both_be_required :
    admitted ⟨⟨1,2,2⟩,⟨1,2,2⟩,[1],[2,3]⟩ = true ∧
    changes ⟨⟨1,2,2⟩,⟨1,2,2⟩,[1],[2,3]⟩ = false := by decide
theorem version_update_need_not_reduce_copies :
    (run true false ⟨⟨1,2,2⟩,⟨1,3,2⟩,[1],[2,3]⟩).selectionChanged = true ∧
    (run true false ⟨⟨1,2,2⟩,⟨1,3,2⟩,[1],[2,3]⟩).placementChanged = false := by decide
theorem one_copy_cannot_have_two_plain_fixture_versions :
    admitted ⟨⟨1,2,2⟩,⟨1,2,1⟩,[1],[2]⟩ = false := by decide
end ApplicationStudy.Dedupe
