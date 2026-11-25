namespace ApplicationStudy.JsUpdates

structure Version where
  major : Nat
  minor : Nat
  patch : Nat
  deriving BEq, DecidableEq, Repr
def versionText (v : Version) : String := s!"{v.major}.{v.minor}.{v.patch}"
def older (a b : Version) : Bool := a.major < b.major ||
  (a.major == b.major && (a.minor < b.minor || (a.minor == b.minor && a.patch < b.patch)))
def newerOf (a b : Version) : Version := if older a b then b else a
inductive Spec where
  | exact (version : Version)
  | caret (minimum : Version)
  | local (reference : String)
  deriving BEq, DecidableEq, Repr
def specText : Spec → String
  | .exact v => versionText v | .caret v => "^" ++ versionText v | .local s => s
def permits (spec : Spec) (v : Version) : Bool := match spec with
  | .exact wanted => wanted == v
  | .caret low => low.major > 0 && low.major == v.major && !older v low
  | .local _ => false
structure Catalog where
  stable : List Version
  latest : Version -- named tag, not a monotone/highest-version assertion
  deriving BEq, DecidableEq, Repr
def greatest : List Version → Option Version
  | [] => none
  | v::tail => some (tail.foldl newerOf v)
def within (catalog : Catalog) (spec : Spec) : Option Version :=
  greatest (catalog.stable.filter (permits spec))
-- The research decoder additionally requires a satisfying latest tag to be
-- the greatest admitted version. That makes this bounded projection independent
-- of the tools' differing tag-preference details; it is not a general resolver.
inductive Selection where
  | registry (version : Version)
  | local (basis : Nat) -- finite checked content/reference witness, not an inode
  deriving BEq, DecidableEq, Repr
def selectionText : Selection → String
  | .registry v => versionText v | .local basis => s!"local:{basis}"
inductive Evidence where | online | prior | missing | notQueried deriving BEq, DecidableEq, Repr
inductive Profile where | npm | pnpm | yarn deriving BEq, DecidableEq, Repr
inductive Action where | refresh | rewriteLatest | inspect deriving BEq, DecidableEq, Repr
structure Dependency where
  name : String
  spec : Spec
  installed : Selection
  saved : Selection
  selected : Bool
  evidence : Evidence
  catalog : Option Catalog
  deriving BEq, DecidableEq, Repr

def preservesStyle (spec : Spec) (version : Version) : Spec := match spec with
  | .exact _ => .exact version | .caret _ => .caret version | .local s => .local s
def target (profile : Profile) (action : Action) (spec : Spec) (catalog : Catalog) : Option Version :=
  if action == .refresh then within catalog spec
  else if profile == .pnpm then some ((within catalog spec).map (newerOf catalog.latest) |>.getD catalog.latest)
  else some catalog.latest
def declaration (profile : Profile) (action : Action) (before : Spec) (chosen : Version) : Spec :=
  if profile == .pnpm then preservesStyle before chosen
  else if action == .refresh then before else .caret chosen
def demandsRegistry (profile : Profile) (action : Action) (spec : Spec) : Bool := match spec with
  | .local _ => profile == .yarn && action == .rewriteLatest
  | _ => true
def planOne (profile : Profile) (action : Action) (d : Dependency) : Option Dependency := do
  if !d.selected || !demandsRegistry profile action d.spec then return d
  -- This plan is not an executor. The measured successful native operations
  -- later materialize both selections; interrupted/partial execution is open.
  let catalog ← d.catalog
  let version ← target profile action d.spec catalog
  pure { d with spec := declaration profile action d.spec version
                installed := .registry version
                saved := .registry version }
def plan (profile : Profile) (action : Action) (ds : List Dependency) : Option (List Dependency) :=
  ds.mapM (planOne profile action)

structure QueryRow where
  name : String
  current : Version
  wanted : Version
  latest : Version
  deriving BEq, DecidableEq, Repr
structure QueryResult where
  row : Option QueryRow
  unhandled : Bool
  deriving BEq, DecidableEq, Repr
def current (profile : Profile) (d : Dependency) : Option Version :=
  match (if profile == .pnpm then d.saved else d.installed) with
  | .registry v => some v | .local _ => none
/-- Missing metadata here is the admitted 404/omitted-target profile, not every
    possible transport error. Prior catalog availability is an external basis. -/
def queryOne (profile : Profile) (d : Dependency) : QueryResult := Id.run do
  if !d.selected then return ⟨none,false⟩
  if let .local _ := d.spec then return ⟨none,false⟩
  let some catalog := d.catalog | return ⟨none,profile != .npm⟩
  let some actual := current profile d | return ⟨none,true⟩
  let some allowed := within catalog d.spec | return ⟨none,profile != .npm⟩
  let wanted := if profile == .pnpm then actual else allowed
  let showRow := if profile == .pnpm then older actual catalog.latest
    else actual != wanted || wanted != catalog.latest
  return ⟨if showRow then some ⟨d.name,actual,wanted,catalog.latest⟩ else none,false⟩
structure Report where
  exitCode : Nat
  states : List Dependency
  rows : List QueryRow
  deriving BEq, DecidableEq, Repr
-- The states below are the selected planning/qualified-success projection.
-- This model executes no installer and proves no rollback after partial IO.
def run (profile : Profile) (action : Action) (ds : List Dependency) : Report :=
  if action == .inspect then
    let queried := ds.map (queryOne profile)
    let rows := queried.filterMap (·.row)
    ⟨if queried.any (·.unhandled) || !rows.isEmpty then 1 else 0,ds,rows⟩
  else match plan profile action ds with
    | none => ⟨1,ds,[]⟩ | some after => ⟨0,after,[]⟩
-- Facts available to an improved report, distinct from current native fields.
def unavailable (d : Dependency) : Bool := d.selected && d.evidence == .missing
def retainedBasis (d : Dependency) : Bool := d.selected && d.evidence == .prior
inductive Direction where | older | same | newer | unknown deriving BEq, DecidableEq, Repr
inductive CurrentBasis where | installed | saved deriving BEq, DecidableEq, Repr
structure Explanation where
  evidence : Evidence
  currentBasis : CurrentBasis
  constrainedTarget : Option Version
  tagDirection : Direction
  exactConstraint : Bool
  deriving BEq, DecidableEq, Repr
/-- Proposed additive facts, not the current native query schema. The evidence
    constructor remains an admitted observation; this does not probe a cache. -/
def explain (profile : Profile) (d : Dependency) : Explanation :=
  let direction := match current profile d,d.catalog with
    | some v,some c => if older v c.latest then Direction.newer
      else if older c.latest v then .older else .same
    | _,_ => .unknown
  ⟨d.evidence,if profile == .pnpm then .saved else .installed,
    d.catalog.bind (fun c => within c d.spec),direction,
    match d.spec with | .exact _ => true | _ => false⟩
def firstSpec (r : Report) : Option Spec := r.states.head?.map (·.spec)
def firstSelection (r : Report) : Option Selection := r.states.head?.map (·.installed)
def dependencyText (d : Dependency) : String :=
  d.name ++ "=" ++ specText d.spec ++ "," ++ selectionText d.saved ++ "," ++ selectionText d.installed ++ ";"
def rowText (r : QueryRow) : String :=
  r.name ++ "=" ++ versionText r.current ++ "," ++ versionText r.wanted ++ "," ++ versionText r.latest ++ ";"
def reportText (r : Report) : String :=
  toString r.exitCode ++ "/" ++ String.join (r.states.map dependencyText) ++ "/" ++ String.join (r.rows.map rowText)

def one : Version := ⟨1,0,0⟩
def minor : Version := ⟨1,1,0⟩
def two : Version := ⟨2,0,0⟩
def advanced : Catalog := ⟨[one,minor,two],two⟩
def retagged : Catalog := {advanced with latest := minor}
def dep (spec : Spec) : Dependency := ⟨"sample",spec,.registry one,.registry one,true,.online,some advanced⟩
def pinned : Dependency := dep (.exact one)
def ranged : Dependency := dep (.caret one)
def localInput : Dependency := ⟨"local",.local "file:../local",.local 1,.local 1,true,.notQueried,none⟩

theorem range_and_pin_have_different_admission :
    within advanced (.caret one) = some minor ∧ within advanced (.exact one) = some one := by decide
theorem selected_refresh_preserves_pin_in_all_profiles :
    [Profile.npm,.pnpm,.yarn].all (fun p => firstSpec (run p .refresh [pinned]) == some (.exact one)) = true := by decide
theorem npm_refresh_keeps_declared_range :
    (run .npm .refresh [ranged]).states = [{ranged with installed := .registry minor,saved := .registry minor}] := by decide
theorem pnpm_refresh_advances_written_lower_bound :
    firstSpec (run .pnpm .refresh [ranged]) = some (.caret minor) := by decide
theorem yarn_recursive_refresh_keeps_declared_range :
    firstSpec (run .yarn .refresh [ranged]) = some (.caret one) := by decide
theorem rewriting_is_distinct_from_refreshing :
    firstSpec (run .npm .rewriteLatest [pinned]) = some (.caret two) ∧
    firstSpec (run .pnpm .rewriteLatest [pinned]) = some (.exact two) := by decide
theorem pnpm_latest_rewrite_preserves_range_style :
    firstSpec (run .pnpm .rewriteLatest [ranged]) = some (.caret two) := by decide
theorem a_latest_tag_need_not_be_highest : greatest retagged.stable = some two ∧ retagged.latest = minor := by decide
def currentTwo : Dependency := {ranged with spec := .caret two,installed := .registry two,saved := .registry two,catalog := some retagged}
theorem explicit_tag_rewrite_can_downgrade :
    firstSelection (run .npm .rewriteLatest [currentTwo]) = some (.registry minor) ∧
    firstSelection (run .yarn .rewriteLatest [currentTwo]) = some (.registry minor) := by decide
theorem pnpm_latest_keeps_higher_permitted_version :
    firstSelection (run .pnpm .rewriteLatest [currentTwo]) = some (.registry two) := by decide
theorem wanted_labels_have_distinct_meanings :
    (queryOne .npm ranged).row.map (·.wanted) = some minor ∧
    (queryOne .pnpm ranged).row.map (·.wanted) = some one := by decide
theorem older_target_can_be_reported_as_outdated_by_npm :
    (run .npm .inspect [currentTwo]).exitCode = 1 ∧ (run .pnpm .inspect [currentTwo]).exitCode = 0 := by decide
theorem empty_success_can_hide_unavailable_metadata :
    let missing := {pinned with evidence := .missing,catalog := none}
    (run .npm .inspect [missing]).exitCode = 0 ∧ (run .npm .inspect [missing]).rows = [] ∧ unavailable missing = true := by decide
theorem retained_catalog_is_not_a_new_successful_lookup :
    let prior := {pinned with evidence := .prior}
    (queryOne .pnpm prior).row.isSome = true ∧ retainedBasis prior = true := by decide
theorem current_query_basis_can_differ :
    let split := {ranged with installed := .registry minor}
    current .npm split = some minor ∧ current .pnpm split = some one := by decide
theorem inspection_preserves_selected_project_state (p : Profile) (ds : List Dependency) :
    (run p .inspect ds).states = ds := by rfl
theorem ignored_local_source_is_preserved :
    (run .pnpm .rewriteLatest [localInput]).states = [localInput] := by decide
theorem selected_yarn_local_conversion_demands_registry_evidence :
    (run .yarn .rewriteLatest [localInput]).exitCode = 1 ∧
    (run .yarn .rewriteLatest [localInput]).states = [localInput] := by decide
theorem planning_refusal_does_not_publish_an_earlier_change :
    (run .yarn .rewriteLatest [ranged,localInput]).states = [ranged,localInput] := by decide
theorem unselected_local_does_not_block_registry_updates :
    (run .yarn .rewriteLatest [ranged,{localInput with selected := false}]).exitCode = 0 := by decide
theorem proposed_explanation_retains_missing_observation :
    (explain .npm {pinned with evidence := .missing,catalog := none}).tagDirection = .unknown ∧
    (explain .npm {pinned with evidence := .missing,catalog := none}).evidence = .missing := by decide
theorem proposed_explanation_preserves_retained_basis :
    (explain .pnpm {pinned with evidence := .prior}).evidence = .prior := by decide
theorem proposed_explanation_names_the_older_target :
    (explain .npm currentTwo).tagDirection = .older := by decide
theorem proposed_explanation_keeps_current_basis_distinct :
    (explain .npm ranged).currentBasis = .installed ∧ (explain .pnpm ranged).currentBasis = .saved := by decide

end ApplicationStudy.JsUpdates
