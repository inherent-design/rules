namespace ApplicationStudy.JsOverrides

-- Bounded policy projection: generated catalog {1.0.0,1.1.0,2.0.0},
-- positive-major ^1.0.0 edges, no peers/protocols/workspaces or IO failures.
inductive Version where | one | minor | two deriving BEq, DecidableEq, Repr
inductive Tool where | npm | pnpm | yarn deriving BEq, DecidableEq, Repr
inductive Scope where | global | parent | converge | broad | narrow deriving BEq, DecidableEq, Repr
structure Rule where
  scope : Scope
  version : Version
  deriving BEq, DecidableEq, Repr
structure Pair where
  left : Version
  right : Version
  deriving BEq, DecidableEq, Repr
structure State where
  choices : List Pair := []
  manual : Option Version := none
  deriving BEq, DecidableEq, Repr
inductive Action where | install | setResolution | check | removeLock | query deriving BEq, DecidableEq, Repr
structure Request where
  action : Action
  rules : List Rule := []
  target : Version := .two
  deriving BEq, DecidableEq, Repr
structure Result where
  exitCode : Nat
  state : State
  deriving BEq, DecidableEq, Repr

def permitted (v : Version) : Bool := v != .two
def applicable (left : Bool) (r : Rule) : Bool := match r.scope with
  | .parent => left | _ => true
def explicit (r : Rule) : Bool := r.scope != .converge
def forced (left : Bool) (rules : List Rule) : List Rule :=
  rules.filter (fun r => explicit r && applicable left r)
def preferred (tool : Tool) (left : Bool) (rules : List Rule) : List Rule :=
  let selectedRules := forced left rules
  if tool == .yarn then selectedRules.take 1
  else
    let parents := selectedRules.filter (fun r => r.scope == .parent)
    if !parents.isEmpty then parents else selectedRules
def values (tool : Tool) (left : Bool) (rules : List Rule) : List Version :=
  let selectedRules := preferred tool left rules
  -- The pnpm overlapping-range ordering cause is unresolved. Admit each
  -- matching target; do not predict a winner or silently adopt the comment.
  if !selectedRules.isEmpty then (selectedRules.map (·.version)).eraseDups
  else match (rules.find? (fun r => r.scope == .converge && permitted r.version)) with
    | some r => [r.version] | none => [.minor]
def graph (tool : Tool) (direct : Bool) (rules : List Rule) : List Pair :=
  let left := values tool (!direct) rules
  if direct then left.map (fun v => ⟨v,v⟩)
  else left.flatMap (fun l => (values tool false rules).map (fun r => ⟨l,r⟩))
-- Proposed policy for this strict-containment pair only. No general interval
-- containment algorithm, native comparator correction, or lock migration.
def candidateNarrowest (rules : List Rule) : List Version :=
  match rules.find? (fun r => r.scope == .narrow) with
  | some r => [r.version] | none => values .pnpm true rules
def directConflict (tool : Tool) (direct : Bool) (rules : List Rule) : Bool :=
  tool == .npm && direct && rules.any (fun r => r.scope == .global)
def step (tool : Tool) (direct : Bool) (s : State) (r : Request) : Result :=
  match r.action with
  | .query => ⟨0,s⟩
  | .removeLock => ⟨0,{s with manual := none}⟩
  | .check => ⟨if s.choices.any (fun p => !permitted p.left || !permitted p.right) then 1 else 0,s⟩
  | .setResolution => ⟨0,⟨[⟨r.target,r.target⟩],some r.target⟩⟩
  | .install =>
    if directConflict tool direct r.rules then ⟨1,s⟩
    else match s.manual with
      | some v => ⟨0,⟨[⟨v,v⟩],s.manual⟩⟩
      | none => ⟨0,⟨graph tool direct r.rules,none⟩⟩
def trace (tool : Tool) (direct : Bool) (s : State) : List Request → List Result
  | [] => []
  | r::tail => let result := step tool direct s r
               result :: trace tool direct result.state tail
def versionText : Version → String | .one => "1.0.0" | .minor => "1.1.0" | .two => "2.0.0"
def text (r : Result) : String :=
  s!"{r.exitCode}/" ++ (r.state.manual.map versionText).getD "-" ++ "/" ++
  String.intercalate ";" (r.state.choices.map (fun p => versionText p.left ++ "," ++ versionText p.right))

def globalOne : Rule := ⟨.global,.one⟩
def parentTwo : Rule := ⟨.parent,.two⟩
def base : State := ⟨[⟨.minor,.minor⟩],none⟩
def manual : State := ⟨[⟨.two,.two⟩],some .two⟩

theorem query_preserves_state (t : Tool) (d : Bool) (s : State) :
    (step t d s {action := .query}).state = s := rfl
theorem check_preserves_state (t : Tool) (d : Bool) (s : State) :
    (step t d s {action := .check}).state = s := rfl
theorem lock_removal_preserves_installed_choices (t : Tool) (d : Bool) (s : State) :
    (step t d s {action := .removeLock}).state.choices = s.choices := rfl
theorem lock_removal_drops_manual_authority (t : Tool) (d : Bool) (s : State) :
    (step t d s {action := .removeLock}).state.manual = none := rfl
theorem npm_direct_refusal_preserves_state (s : State) :
    step .npm true s {action := .install, rules := [⟨.global,.two⟩]} = ⟨1,s⟩ := by rfl
theorem npm_parent_precedes_global :
    graph .npm false [globalOne,parentTwo] = [⟨.two,.one⟩] := by decide
theorem pnpm_parent_precedes_global :
    graph .pnpm false [globalOne,parentTwo] = [⟨.two,.one⟩] := by decide
theorem yarn_first_match_changes_graph :
    graph .yarn false [globalOne,parentTwo] = [⟨.one,.one⟩] ∧
    graph .yarn false [parentTwo,globalOne] = [⟨.two,.one⟩] := by decide
theorem npm_order_swap_same_in_selected_profile :
    graph .npm false [globalOne,parentTwo] = graph .npm false [parentTwo,globalOne] := by decide
theorem pnpm_order_swap_same_in_selected_profile :
    graph .pnpm false [globalOne,parentTwo] = graph .pnpm false [parentTwo,globalOne] := by decide
theorem direct_forcing_is_tool_specific :
    (step .pnpm true base {action := .install, rules := [⟨.global,.two⟩]}).state.choices = [⟨.two,.two⟩] ∧
    (step .yarn true base {action := .install, rules := [⟨.global,.two⟩]}).state.choices = [⟨.two,.two⟩] := by decide
theorem incompatible_convergence_does_not_force :
    graph .pnpm false [⟨.converge,.two⟩] = [⟨.minor,.minor⟩] := by decide
theorem compatible_convergence_selects_target :
    graph .pnpm false [⟨.converge,.one⟩] = [⟨.one,.one⟩] := by decide
theorem force_is_not_convergence :
    graph .pnpm false [⟨.global,.two⟩] ≠ graph .pnpm false [⟨.converge,.two⟩] := by decide
theorem set_resolution_materializes_outside_range :
    step .yarn true base {action := .setResolution} = ⟨0,manual⟩ := by decide
theorem stricter_check_refuses_without_repair :
    step .yarn true manual {action := .check} = ⟨1,manual⟩ := by decide
theorem lock_regeneration_loses_manual_choice :
    (step .yarn true (step .yarn true manual {action := .removeLock}).state {action := .install}).state = base := by decide
theorem overlap_does_not_qualify_narrowest_winner :
    values .pnpm true [⟨.broad,.one⟩,⟨.narrow,.two⟩] = [.one,.two] := by decide
theorem proposed_strict_containment_prefers_narrow :
    candidateNarrowest [⟨.broad,.one⟩,⟨.narrow,.two⟩] = [.two] := by decide
theorem proposed_containment_is_order_independent_in_this_pair :
    candidateNarrowest [⟨.broad,.one⟩,⟨.narrow,.two⟩] =
    candidateNarrowest [⟨.narrow,.two⟩,⟨.broad,.one⟩] := by decide

end ApplicationStudy.JsOverrides
