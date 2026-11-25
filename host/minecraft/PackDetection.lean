namespace Host.Minecraft.PackDetection

/- Bounded detection, not opening, metadata admission or repository selection.
   Nodes describe quiescent fixture bindings. IDs are case-local observations,
   not permanent filesystem identities or mutation authority. -/
inductive Kind where
  | missing | regular | directory | link | other
  deriving BEq, DecidableEq, Repr

structure Node where
  kind : Kind
  identity : Nat := 0
  zipSuffix : Bool := false
  metadataRegular : Bool := false
  nestedLinks : Nat := 0
  deriving BEq, DecidableEq, Repr

inductive FactoryMode where
  | returned | nullValue | failed
  deriving BEq, DecidableEq, Repr

structure Input where
  entry : Node
  rawTarget : Node
  parentTarget : Node
  targetAbsolute : Bool
  allowLinks : Bool
  factoryMode : FactoryMode
  deriving BEq, DecidableEq, Repr

structure Outcome where
  error : Nat := 0 -- 0 return; 1 missing raw target; 2 authored factory IOException
  value : Nat := 0 -- 0 null; 1 zip callback result; 2 directory callback result
  factory : Nat := 0
  binding : Nat := 0
  issues : Nat := 0
  matcherCalls : Nat := 0
  deriving BEq, DecidableEq, Repr

def invoke (mode : FactoryMode) (kind binding : Nat) : Outcome :=
  match mode with
  | .returned => ⟨0, kind, kind, binding, 0, 0⟩
  | .nullValue => ⟨0, 0, kind, binding, 0, 0⟩
  | .failed => ⟨2, 0, kind, binding, 0, 0⟩

def classify (node : Node) (allowLinks : Bool) (mode : FactoryMode) : Outcome :=
  match node.kind with
  | .directory =>
    let issues := if allowLinks then 0 else node.nestedLinks
    if issues != 0 then ⟨0, 0, 0, 0, issues, node.nestedLinks⟩
    else
      let result := if node.metadataRegular then invoke mode 2 node.identity else {}
      { result with matcherCalls := node.nestedLinks }
  | .regular => if node.zipSuffix then invoke mode 1 node.identity else {}
  | _ => {}

def follow (input : Input) (target : Node) : Outcome :=
  if !input.allowLinks then ⟨0, 0, 0, 0, 1, 1⟩
  else if target.kind = .missing then ⟨1, 0, 0, 0, 0, 1⟩
  else
    let result := classify target input.allowLinks input.factoryMode
    { result with matcherCalls := result.matcherCalls + 1 }

def run (input : Input) : Outcome :=
  if input.entry.kind = .link then follow input input.rawTarget
  else classify input.entry input.allowLinks input.factoryMode

/- A proposed parent anchor, not an implemented or race-safe backport. -/
def parentAnchored (input : Input) : Outcome :=
  if input.entry.kind = .link then
    follow input (if input.targetAbsolute then input.rawTarget else input.parentTarget)
  else classify input.entry input.allowLinks input.factoryMode

theorem missing_returns_without_factory (allow : Bool) (mode : FactoryMode) :
    classify { kind := .missing } allow mode = {} := rfl

theorem non_zip_file_returns_without_factory (identity : Nat) (allow : Bool) (mode : FactoryMode) :
    classify { kind := .regular, identity := identity, zipSuffix := false } allow mode = {} := rfl

theorem regular_file_ignores_link_matcher (identity : Nat) (suffix allow : Bool) (mode : FactoryMode) :
    (classify { kind := .regular, identity := identity, zipSuffix := suffix } allow mode).matcherCalls = 0 := by
  cases suffix <;> cases mode <;> rfl

theorem denied_top_link_never_invokes_factory (input : Input) (target : Node)
    (denied : input.allowLinks = false) :
    follow input target = ⟨0, 0, 0, 0, 1, 1⟩ := by simp [follow, denied]

theorem missing_allowed_target_throws (input : Input) (allowed : input.allowLinks = true) :
    follow input { kind := .missing } = ⟨1, 0, 0, 0, 0, 1⟩ := by simp [follow, allowed]

theorem missing_directory_metadata_keeps_validator_calls (identity links : Nat) (mode : FactoryMode) :
    classify ⟨.directory, identity, false, false, links⟩ true mode = ⟨0, 0, 0, 0, 0, links⟩ := by
  simp [classify]

theorem forbidden_directory_stops_before_metadata (identity links : Nat) (metadata : Bool) (mode : FactoryMode)
    (nonzero : links ≠ 0) :
    classify ⟨.directory, identity, false, metadata, links⟩ false mode = ⟨0, 0, 0, 0, links, links⟩ := by
  simp [classify, nonzero]

theorem null_factory_preserves_invocation (kind binding : Nat) :
    invoke .nullValue kind binding = ⟨0, 0, kind, binding, 0, 0⟩ := rfl

theorem throwing_factory_preserves_invocation (kind binding : Nat) :
    invoke .failed kind binding = ⟨2, 0, kind, binding, 0, 0⟩ := rfl

theorem absolute_anchor_preserves_link_decision (input : Input) (absolute : input.targetAbsolute = true) :
    parentAnchored input = run input := by simp [parentAnchored, run, absolute]

theorem non_link_anchor_preserves_decision (input : Input) (notLink : input.entry.kind ≠ .link) :
    parentAnchored input = run input := by simp [parentAnchored, run, notLink]

def shadowExample : Input :=
  ⟨{ kind := .link, identity := 1 }, { kind := .regular, identity := 3, zipSuffix := true }, { kind := .regular, identity := 2, zipSuffix := true }, false, true, .returned⟩

def missingExample : Input :=
  { shadowExample with rawTarget := { kind := .missing } }

theorem successful_factory_can_receive_cwd_shadow :
    run shadowExample = ⟨0, 1, 1, 3, 0, 1⟩ := rfl

theorem parent_anchor_selects_different_binding :
    parentAnchored shadowExample = ⟨0, 1, 1, 2, 0, 1⟩ := rfl

theorem existing_parent_target_can_still_fail_current_lookup :
    run missingExample = ⟨1, 0, 0, 0, 0, 1⟩ := rfl

theorem parent_anchor_changes_missing_cwd_example :
    parentAnchored missingExample = ⟨0, 1, 1, 2, 0, 1⟩ := rfl

end Host.Minecraft.PackDetection
