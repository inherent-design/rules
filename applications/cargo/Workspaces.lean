namespace ApplicationStudy.CargoWorkspaces

/-- Root=0,A=1,B=2. Only normal A-to-B path dependencies are admitted.
    Metadata/package identities remain opaque to the observation adapter. -/
structure Profile where
  rootPackage : Bool
  explicitA : Bool
  memberB : Bool
  deriving BEq, DecidableEq, Repr

def members (p : Profile) : List Nat :=
  if p.rootPackage then [0,1,2] else [1,2]

/-- Default members belong to the effective manifest context, not only the
    immutable root manifest text. An explicit --manifest-path selects that
    context even when the process current directory is a member. -/
def defaults (p : Profile) : List Nat :=
  if p.memberB then [2]
  else if p.explicitA then [1]
  else if p.rootPackage then [0] else [1,2]

inductive Mode | defaultRequest | workspaceExcludeB | explicitA | invalidExclude
  deriving BEq, DecidableEq, Repr

def selection (p : Profile) : Mode → List Nat
  | .defaultRequest => defaults p
  | .workspaceExcludeB => (members p).filter (· != 2)
  | .explicitA => [1]
  | .invalidExclude => []

/-- Compiler-reported package membership for the captured check profile.
    It is not a full target/feature unit graph or verified artifact content. -/
def checkedClosure (selected : List Nat) : List Nat :=
  [0,1,2].filter (fun id => selected.contains id || (id == 2 && selected.contains 1))

def checked (p : Profile) (mode : Mode) : List Nat :=
  checkedClosure (selection p mode)

theorem member_context_overrides_root_defaults (root explicit : Bool) :
    defaults ⟨root,explicit,true⟩ = [2] := rfl

theorem explicit_defaults_select_a (root : Bool) :
    defaults ⟨root,true,false⟩ = [1] := rfl

theorem nonvirtual_unset_selects_root : defaults ⟨true,false,false⟩ = [0] := rfl

theorem virtual_unset_selects_all : defaults ⟨false,false,false⟩ = [1,2] := rfl

theorem excluded_b_not_selected (p : Profile) :
    !(selection p .workspaceExcludeB).contains 2 = true := by
  cases p with
  | mk root explicit member => cases root <;> simp [selection, members]

theorem excluded_b_still_checked (explicit member : Bool) :
    (checked ⟨false,explicit,member⟩ .workspaceExcludeB).contains 2 = true := by
  simp only [checked, selection, members, Bool.false_eq_true, ↓reduceIte]
  decide

theorem explicit_a_requires_b (p : Profile) : checked p .explicitA = [1,2] := by
  simp only [checked, selection]
  decide

theorem same_members_different_default_context :
    members ⟨true,true,false⟩ = members ⟨true,true,true⟩ ∧
    defaults ⟨true,true,false⟩ ≠ defaults ⟨true,true,true⟩ := by decide

theorem invalid_selection_checks_nothing (p : Profile) : checked p .invalidExclude = [] := by
  simp only [checked, selection]
  decide

end ApplicationStudy.CargoWorkspaces
