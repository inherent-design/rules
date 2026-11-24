namespace ApplicationStudy.EmpackSynchronization

/-- Research profile: fictional Modrinth mods, common/required participation,
    automatic placements, version-only record changes, and complete observations.
    Record strings are equality labels over the captured typed records. -/
structure Root where
  key : String
  /-- None is the specific captured Modrinth Search form, not arbitrary unknown identity. -/
  project : Option Nat
  pin : Option Nat
  deriving BEq, Repr
structure Node where
  key : String
  project : Nat
  version : Nat
  record : String
  /-- 0 complete, 1 partial; unknown coverage is outside this captured profile. -/
  coverage : Nat
  /-- Stored map-entry presence is separate from outgoing adjacency and coverage. -/
  edgesPresent : Bool
  edges : List String
  deriving BEq, Repr
structure Runtime where
  game : String
  loader : String
  version : Option String
  deriving BEq, Repr
structure Input where
  roots : List Root
  prior : List Node
  proposed : List Node
  requestedRuntime : Runtime
  priorRuntime : Runtime
  proposedRuntime : Runtime
  requestedAccepted : List String
  priorAccepted : List String
  proposedAccepted : List String
  sameRevision : Bool
  deriving Repr

def keyOrder : List String := ["a","b","c","d","e","renamed","x","y"]
def canonical (keys : List String) : List String := keyOrder.filter keys.contains
def lookup (nodes : List Node) (key : String) : Option Node := nodes.find? (fun n => n.key == key)
def runtimeSatisfies (requested selected : Runtime) : Bool :=
  requested.game == selected.game && requested.loader == selected.loader &&
    requested.version.all (fun v => selected.version == some v)
def rootSatisfied (root : Root) (node : Node) : Bool :=
  root.project.all (· == node.project) && root.pin.all (· == node.version)

def aliasPairs (roots : List Root) (prior : List Node) : Except String (List (String × String)) :=
  roots.foldlM (fun aliases root => do
    if (lookup prior root.key).isSome then return aliases
    let candidate := prior.find? fun n =>
      !roots.any (fun r => r.key == n.key) && root.project == some n.project
    match candidate with
    | none => return aliases
    | some node =>
      if aliases.any (fun pair => pair.1 == node.key) then throw "alias"
      return aliases ++ [(node.key,root.key)]) []
def renamed (aliases : List (String × String)) (key : String) : String :=
  ((aliases.find? (fun pair => pair.1 == key)).map Prod.snd).getD key
def renameNode (aliases : List (String × String)) (node : Node) : Node :=
  {node with
    key := renamed aliases node.key
    edges := canonical (node.edges.map (renamed aliases))}
def rebind (roots : List Root) (prior : List Node) : Except String (List Node) := do
  let aliases ← aliasPairs roots prior
  let nodes := prior.map (renameNode aliases)
  pure (keyOrder.filterMap (lookup nodes))

def affected (input : Input) (prior : List Node) : List String :=
  canonical ((input.roots.filter fun root =>
    !runtimeSatisfies input.requestedRuntime input.priorRuntime ||
    input.requestedAccepted != input.priorAccepted ||
    (root.project.isNone && !input.sameRevision) ||
    !(lookup prior root.key).any (rootSatisfied root)).map (·.key))

def closureStep (nodes : List Node) (seen : List String) : List String :=
  canonical (seen ++ nodes.flatMap (fun n => if seen.contains n.key then n.edges else []))
def grow (nodes : List Node) : Nat → List String → List String
  | 0, seen => seen
  | n+1, seen => grow nodes n (closureStep nodes seen)
def closure (nodes : List Node) (seeds : List String) : List String := grow nodes keyOrder.length seeds

def proposalValid (input : Input) : Bool :=
  runtimeSatisfies input.requestedRuntime input.proposedRuntime &&
  input.requestedAccepted == input.proposedAccepted &&
  input.roots.all (fun r => (lookup input.proposed r.key).any (rootSatisfied r))

def checkPrior (input : Input) (prior : List Node) (active allowed : List String) : Except String (List String) :=
  prior.foldlM (fun changed old => do
    let some next := lookup input.proposed old.key | throw "discard"
    let retainedRoot := input.roots.any (fun r => r.key == old.key) && !active.contains old.key
    if !allowed.contains old.key || retainedRoot then
      if old.record != next.record || old.coverage != next.coverage ||
          old.edgesPresent != next.edgesPresent || old.edges != next.edges then throw "retained"
      return changed
    if old.record != next.record then
      let selectionChanged := old.project != next.project || old.version != next.version
      if selectionChanged && prior.any (fun dependent => !allowed.contains dependent.key && dependent.edges.contains old.key) then
        throw "dependent"
      return changed ++ [old.key]
    return changed) []

def checkScope (input : Input) (prior : List Node) (active : List String) : Except String (List String) := do
  if runtimeSatisfies input.requestedRuntime input.priorRuntime && input.proposedRuntime != input.priorRuntime then
    throw "runtime"
  let allowed := closure input.proposed active
  let changed ← checkPrior input prior active allowed
  let changed ← input.proposed.foldlM (fun changed node => do
    if (lookup prior node.key).isNone then
      if !allowed.contains node.key then throw "unjustified"
      return changed ++ [node.key]
    return changed) changed
  pure (canonical changed)

structure Outcome where
  runtimeSatisfied : Bool
  affected : List String
  normalized : Option (List Node)
  stage : String
  result : String
  changed : List String
  reason : String
  deriving Repr
def supportedKeys (input : Input) : Bool :=
  input.roots.all (fun root => keyOrder.contains root.key) &&
  (input.prior ++ input.proposed).all (fun node =>
    keyOrder.contains node.key && node.edges.all keyOrder.contains)
def evaluate (input : Input) : Outcome :=
  let sat := runtimeSatisfies input.requestedRuntime input.priorRuntime
  if !supportedKeys input then ⟨sat,[],none,"research-profile","unsupported",[],"unsupported"⟩ else
  match rebind input.roots input.prior with
  | .error reason => ⟨sat,[],none,"rebind","error",[],reason⟩
  | .ok prior =>
    let active := affected input prior
    if !proposalValid input then ⟨sat,active,some prior,"proposed","error",[],"proposed"⟩ else
    match checkScope input prior active with
    | .error reason => ⟨sat,active,some prior,"scope","error",[],reason⟩
    | .ok changed => ⟨sat,active,some prior,"scope","ok",changed,""⟩

def fixtureNodes : List Node :=
  [⟨"a",1,1,"a1",0,true,["b"]⟩,⟨"b",2,1,"b1",0,false,[]⟩,⟨"c",3,1,"c1",0,false,[]⟩]
def base : Input :=
  ⟨[⟨"a",some 1,none⟩],fixtureNodes,fixtureNodes,⟨"game","fabric",none⟩,
    ⟨"game","fabric",some "old"⟩,⟨"game","fabric",some "old"⟩,[],[],[],false⟩

theorem unpinned_request_retains_exact_runtime : runtimeSatisfies base.requestedRuntime base.priorRuntime = true := rfl
theorem metadata_does_not_require_provider_resolution : affected base fixtureNodes = [] := rfl
theorem root_demotion_is_not_deletion_authority :
    checkScope {base with roots := []} fixtureNodes [] = .ok [] := rfl
theorem missing_prior_record_is_refused :
    checkScope {base with roots := [], proposed := fixtureNodes.tail} fixtureNodes [] = .error "discard" := rfl
theorem closure_reaches_shared_dependency : closure fixtureNodes ["a"] = ["a","b"] := rfl
theorem unrelated_record_is_outside_closure : (closure fixtureNodes ["a"]).contains "c" = false := rfl
theorem empty_edge_entry_is_not_absence :
    checkScope {base with proposed := fixtureNodes.map (fun n => if n.key == "c" then {n with edgesPresent := true} else n)} fixtureNodes [] = .error "retained" := rfl
theorem scope_result_is_not_full_lock_delta :
    let changed : Input := {base with
      roots := [⟨"a",some 1,some 2⟩]
      proposed := fixtureNodes.map (fun n => if n.key == "a" then {n with version := 2, record := "a2"}
        else if n.key == "b" then {n with coverage := 1} else n)}
    (evaluate changed).result = "ok" ∧ (evaluate changed).changed = ["a"] := by constructor <;> rfl
theorem explicit_runtime_upgrade_needs_new_requirements :
    checkScope {base with proposedRuntime := ⟨"game","fabric",some "new"⟩} fixtureNodes [] = .error "runtime" := rfl
theorem search_is_bound_to_overall_revision :
    affected {base with roots := [⟨"a",none,none⟩]} fixtureNodes = ["a"] := rfl
theorem same_revision_keeps_search_selection :
    affected {base with roots := [⟨"a",none,none⟩], sameRevision := true} fixtureNodes = [] := rfl

theorem alias_does_not_replace_selection_or_record (aliases : List (String × String)) (node : Node) :
    ((renameNode aliases node).project,(renameNode aliases node).version,(renameNode aliases node).record,
      (renameNode aliases node).coverage,(renameNode aliases node).edgesPresent) =
    (node.project,node.version,node.record,node.coverage,node.edgesPresent) := rfl

theorem cycle_closure_keeps_exactly_reachable_nodes :
    closure [⟨"a",1,1,"a1",0,true,["b"]⟩,⟨"b",2,1,"b1",0,true,["a"]⟩,
      ⟨"c",3,1,"c1",0,false,[]⟩] ["a"] = ["a","b"] := rfl

theorem duplicate_alias_requests_are_not_partial_rebindings :
    rebind [⟨"x",some 1,none⟩,⟨"y",some 1,none⟩] fixtureNodes = .error "alias" := rfl

theorem unsupported_research_key_is_not_silently_dropped :
    (evaluate {base with roots := [⟨"outside-profile",some 1,none⟩]}).result = "unsupported" := rfl

end ApplicationStudy.EmpackSynchronization
