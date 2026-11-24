namespace ApplicationStudy.JsRemoval

/-- Two fixed package identities: parent requires leaf. No peers, optional
    edges, version selection, scripts, or concurrent publication are modeled. -/
structure Roots where
  parent : Bool
  leaf : Bool
  deriving BEq, DecidableEq, Repr

inductive Profile | npm | pnpm | yarn deriving Repr
inductive Action | removeLeaf | addLeaf | removeParent deriving Repr

def liveLeaf (roots : Roots) : Bool := roots.parent || roots.leaf

/-- Bounded node-modules fixture lookup, not the general linker algorithm.
    Visibility from a root is not the root's declaration or a retention proof. -/
def rootCanLoadLeaf (profile : Profile) (roots : Roots) : Bool :=
  match profile with
  | .pnpm => roots.leaf
  | .npm | .yarn => liveLeaf roots

def acceptsMissingRoot : Profile → Bool
  | .npm => true
  | .pnpm | .yarn => false

def accepted (profile : Profile) (action : Action) (roots : Roots) : Bool :=
  match action with
  | .removeLeaf => roots.leaf || acceptsMissingRoot profile
  | .addLeaf => true
  | .removeParent => roots.parent || acceptsMissingRoot profile

def edit (action : Action) (roots : Roots) : Roots :=
  match action with
  | .removeLeaf => { roots with leaf := false }
  | .addLeaf => { roots with leaf := true }
  | .removeParent => { roots with parent := false }

def next (profile : Profile) (action : Action) (roots : Roots) : Roots :=
  if accepted profile action roots then edit action roots else roots

theorem removing_direct_leaf_preserves_parent (profile : Profile) (parent : Bool) :
    (next profile .removeLeaf ⟨parent, true⟩).parent = parent := by cases profile <;> rfl

theorem remaining_parent_retains_leaf : liveLeaf ⟨true, false⟩ = true := rfl

theorem identical_readoption_adds_declaration (profile : Profile) (parent : Bool) :
    next profile .addLeaf ⟨parent, false⟩ = ⟨parent, true⟩ := rfl

theorem readoption_is_idempotent (profile : Profile) (roots : Roots) :
    next profile .addLeaf (next profile .addLeaf roots) = next profile .addLeaf roots := rfl

theorem transitive_only_removal_keeps_declarations (profile : Profile) :
    next profile .removeLeaf ⟨true, false⟩ = ⟨true, false⟩ := by cases profile <;> rfl

theorem removing_parent_preserves_direct_leaf (profile : Profile) (leaf : Bool) :
    next profile .removeParent ⟨true, leaf⟩ = ⟨false, leaf⟩ := by cases profile <;> rfl

theorem no_roots_no_live_leaf : liveLeaf ⟨false, false⟩ = false := rfl

theorem retained_leaf_need_not_be_root_visible :
    liveLeaf ⟨true, false⟩ = true ∧ rootCanLoadLeaf .pnpm ⟨true, false⟩ = false := ⟨rfl, rfl⟩

theorem root_visibility_need_not_be_declaration :
    rootCanLoadLeaf .npm ⟨true, false⟩ = true ∧ (Roots.mk true false).leaf = false := ⟨rfl, rfl⟩

end ApplicationStudy.JsRemoval
