import host.java.FloatOrder

namespace Host.Minecraft.ItemProgram
open Host.Java.FloatOrder

/-- Postorder research syntax. Tags0empty,1leaf,2composite,3condition,4select,5range,6unknown.
    Body IDs witness selected raw JSON equality; they are not model-result inputs.
    emptyRun compresses only a verified homogeneous list of empty child definitions. -/
structure Instruction where
  kind : Nat := 0
  fieldsValid : Bool := true
  hasReference : Bool := false
  reference : Nat := 0
  tints : Nat := 0
  children : List Nat := []
  keys : List (List Nat) := []
  rowFieldsValid : List Bool := []
  fallbackKind : Nat := 0 --0missing,1explicit null,2child
  fallbackChild : Nat := 0
  thresholds : List Nat := [] --0negative ten,1negative zero,2positive zero,3ten,4outside finite profile
  bodies : List Nat := []
  flipScale : Bool := false
  emptyRun : Nat := 0
  deriving Repr

structure State where
  error : Nat := 0
  used : Nat := 0
  dependencies : List Nat := []
  reverseEvents : List Nat := []
  deriving Repr

/-- Events1tint factory,2condition factory,3selector factory,5range factory,
    6condition read,7selector read,8range read,9tint call;100+key is key decoding. -/
def event (s : State) (value : Nat) : State := {s with reverseEvents := value :: s.reverseEvents}
def failure (s : State) (code : Nat) : State := {s with error := code}
def reference (s : State) (value : Nat) : State :=
  if s.dependencies.contains value then s else {s with dependencies := value :: s.dependencies}

def repeatedEvents (s : State) (value count : Nat) : State :=
  {s with reverseEvents := List.replicate count value ++ s.reverseEvents}

def emptyChildren (s : State) (depth count : Nat) : State :=
  if count == 0 then s else if depth > 32 then failure s 13
  else if s.used + count > 4096 then failure {s with used := 4097} 13
  else {s with used := s.used + count}

/-- Error1root fields,2type,3node/row fields,4missing model,5tints,6case/alternative bound,
    7empty alternatives,8duplicate key,9null fallback,10range bound,11nonfinite threshold,
    12threshold conflict,13depth/nodes,14root float scale;99invalid research projection. -/
def compile (fuel : Nat) (program : Array Instruction) (depth index : Nat) (s : State) : State :=
  match fuel with
  | 0 => failure s 99
  | fuel + 1 => Id.run do
    if s.error != 0 then return s
    if depth > 32 then return failure s 13
    let s := {s with used := s.used + 1}
    if s.used > 4096 then return failure s 13
    let some node := program[index]? | return failure s 99
    if node.kind > 5 then return failure s 2
    if !node.fieldsValid then return failure s 3
    let descend := fun child state => compile fuel program (depth + 1) child state
    let fallback := fun state =>
      if state.error != 0 then state
      else if node.fallbackKind == 0 then state
      else if node.fallbackKind == 1 then failure state 9
      else descend node.fallbackChild state
    match node.kind with
    | 0 => return s
    | 1 =>
      if !node.hasReference then return failure s 4
      let s := reference s node.reference
      if node.tints > 32 then return failure s 5
      return repeatedEvents s 1 node.tints
    | 2 =>
      if node.emptyRun != 0 then return emptyChildren s (depth + 1) node.emptyRun
      return node.children.foldl (fun state child => if state.error != 0 then state else descend child state) s
    | 3 =>
      let s := event s 2
      if node.children.length != 2 then return failure s 99
      return node.children.foldl (fun state child => if state.error != 0 then state else descend child state) s
    | 4 =>
      let s := event s 3
      if node.children.length > 512 then return failure s 6
      let (s, _, _) := node.children.zipIdx.foldl (fun (state, seen, alternatives) (child, row) => Id.run do
        if state.error != 0 then return (state, seen, alternatives)
        if !node.rowFieldsValid[row]?.getD false then return (failure state 3, seen, alternatives)
        let state := descend child state
        if state.error != 0 then return (state, seen, alternatives)
        let keys := node.keys[row]?.getD []
        if keys.isEmpty then return (failure state 7, seen, alternatives)
        return keys.foldl (fun (state, seen, alternatives) key =>
          if state.error != 0 then (state, seen, alternatives)
          else if alternatives + 1 > 512 then (failure state 6, seen, alternatives + 1)
          else let state := event state (100 + key)
               if seen.contains key then (failure state 8, seen, alternatives + 1)
               else (state, key :: seen, alternatives + 1)) (state, seen, alternatives)) (s, ([] : List Nat), 0)
      return fallback s
    | 5 =>
      if node.children.length > 512 then return failure s 10
      let (s, _) := node.children.zipIdx.foldl (fun (state, seen) (child, row) => Id.run do
        if state.error != 0 then return (state, seen)
        let threshold := node.thresholds[row]?.getD 4
        if threshold > 3 then return (failure state 11, seen)
        if !node.rowFieldsValid[row]?.getD false then return (failure state 3, seen)
        let body := node.bodies[row]?.getD 0
        match seen.find? (fun pair => pair.1 == threshold) with
        | some pair =>
          if pair.2 != body then return (failure state 12, seen)
          return (state, seen)
        | none => return (descend child state, (threshold, body) :: seen)) (s, ([] : List (Nat × Nat)))
      if s.error != 0 then return s
      return fallback (event s 5)
    | _ => return failure s 99

structure Root where
  badFields : Bool := false
  scaleOverflow : Bool := false
  handAnimation : Bool := true
  oversized : Bool := false
  swapBits : Nat := 1065353216
  index : Nat
  program : Array Instruction
  deriving Repr

def compileRoot (root : Root) : State :=
  if root.badFields then failure {} 1
  else let result := compile 35 root.program 0 root.index {}
       if result.error != 0 then result
       else if root.scaleOverflow then failure result 14 else result

structure Context where
  pick : Nat
  condition : Bool
  number : Atom
  color : Nat
  deriving Repr

structure Layer where
  model : Nat
  tints : Nat := 0
  deriving Repr, BEq, DecidableEq

structure Evaluation where
  layers : List Layer := []
  events : List Nat := []
  valid : Bool := true
  deriving Repr

def missing : Evaluation := {layers := [⟨0,0⟩]}
def combine (left right : Evaluation) : Evaluation :=
  ⟨left.layers ++ right.layers, left.events ++ right.events, left.valid && right.valid⟩

def evaluate (fuel : Nat) (program : Array Instruction) (index : Nat) (context : Context) : Evaluation :=
  match fuel with
  | 0 => {valid := false}
  | fuel + 1 => Id.run do
    let some node := program[index]? | return {valid := false}
    let descend := fun child => evaluate fuel program child context
    let fallback := if node.fallbackKind == 0 then missing else descend node.fallbackChild
    match node.kind with
    | 0 => return {}
    | 1 => return {layers := [⟨node.reference,node.tints⟩]}
    | 2 =>
      if node.emptyRun != 0 then return {}
      return node.children.foldl (fun result child => combine result (descend child)) {}
    | 3 =>
      let position := if context.condition then 0 else 1
      let some child := node.children[position]? | return {valid := false}
      let result := descend child
      return {result with events := 6 :: result.events}
    | 4 =>
      let selected := (node.children.zip node.keys).find? (fun row => row.2.contains context.pick)
      let result := match selected with | some row => descend row.1 | none => fallback
      return {result with events := 7 :: result.events}
    | 5 =>
      let value := Host.Java.FloatOrder.scale node.flipScale context.number
      let selected := if isNaN value then none else
        (node.children.zip node.thresholds).foldl (fun selected row =>
          if row.2 <= rank value then
            match selected with
            | none => some row
            | some previous => if row.2 > previous.2 then some row else selected
          else selected) (none : Option (Nat × Nat))
      let result := match selected with | some row => descend row.1 | none => fallback
      return {result with events := 8 :: result.events}
    | _ => return {valid := false}

/-- The authored observer executes tint callbacks after collecting the complete layer list. -/
def observedEvents (evaluation : Evaluation) : List Nat :=
  evaluation.events ++ List.replicate (evaluation.layers.foldl (fun count layer => count + layer.tints) 0) 9

def leaf (model : Nat) (tints : Nat := 0) : Instruction :=
  {kind := 1, hasReference := true, reference := model, tints := tints}
def empty : Instruction := {}

theorem root_fields_refuse_before_callbacks (r : Root) :
    compileRoot {r with badFields := true} = failure {} 1 := rfl
theorem empty_compiler_emits_no_callbacks :
    (compileRoot ⟨false,false,true,false,1065353216,0,#[empty]⟩).reverseEvents = [] := rfl
theorem empty_composite_emits_no_layers (c : Context) :
    (evaluate 2 #[{kind := 2}] 0 c).layers = [] := rfl
theorem fallback_is_a_layer : missing.layers = [⟨0,0⟩] := rfl
theorem leaf_reference_discovered :
    (compileRoot ⟨false,false,true,false,1065353216,0,#[leaf 7]⟩).dependencies = [7] := by decide
theorem late_root_failure_keeps_factory_event :
    let result := compileRoot ⟨false,true,true,false,1065353216,0,#[leaf 7 1]⟩
    result.error = 14 ∧ result.reverseEvents = [1] := by decide
theorem tint_limit_precedes_factory_calls :
    let result := compileRoot ⟨false,false,true,false,1065353216,0,#[leaf 7 33]⟩
    result.error = 5 ∧ result.reverseEvents = [] := by decide
theorem selected_empty_list_within_node_budget : (emptyChildren {used := 1} 1 4095).error = 0 := by decide
theorem one_more_empty_child_refuses : (emptyChildren {used := 1} 1 4096).error = 13 := by decide
theorem absent_fallback_is_not_a_discovered_reference :
    (compileRoot ⟨false,false,true,false,1065353216,0,#[{kind := 4}]⟩).dependencies = [] := by decide
theorem empty_select_still_constructs_selector :
    (compileRoot ⟨false,false,true,false,1065353216,0,#[{kind := 4}]⟩).reverseEvents = [3] := by decide
theorem duplicate_decoded_key_refuses :
    (compileRoot ⟨false,false,true,false,1065353216,1,
      #[empty,{kind := 4,children := [0],keys := [[2,2]],rowFieldsValid := [true]}]⟩).error = 8 := by decide
theorem null_fallback_refuses_after_selector :
    let result := compileRoot ⟨false,false,true,false,1065353216,0,#[{kind := 4,fallbackKind := 1}]⟩
    result.error = 9 ∧ result.reverseEvents = [3] := by decide
theorem nan_range_uses_fallback :
    (evaluate 2 #[leaf 7,{kind := 5,children := [0],thresholds := [2]}] 1 ⟨0,false,.nan,0⟩).layers = missing.layers := by decide
theorem signed_zero_selects_different_layers :
    let p := #[leaf 7,leaf 8,{kind := 5,children := [0,1],thresholds := [1,2]}]
    (evaluate 3 p 2 ⟨0,false,.negativeZero,0⟩).layers = [⟨7,0⟩] ∧
    (evaluate 3 p 2 ⟨0,false,.positiveZero,0⟩).layers = [⟨8,0⟩] := by decide

theorem stopped_work_preserved (fuel : Nat) (p : Array Instruction) (depth index : Nat)
    (state : State) (stopped : state.error ≠ 0) :
    compile (fuel + 1) p depth index state = state := by simp [compile,stopped]
theorem compile_error_precedes_root_scale (r : Root)
    (failed : (compile 35 r.program 0 r.index {}).error ≠ 0) :
    compileRoot {r with badFields := false} = compile 35 r.program 0 r.index {} := by
  simp [compileRoot,failed]
theorem combination_keeps_layer_order (a b : Evaluation) :
    (combine a b).layers = a.layers ++ b.layers := rfl
theorem layer_combination_associative (a b c : Evaluation) :
    (combine (combine a b) c).layers = (combine a (combine b c)).layers := by
  simp [combine,List.append_assoc]
theorem observer_event_count (result : Evaluation) :
    (observedEvents result).length = result.events.length +
      result.layers.foldl (fun count layer => count + layer.tints) 0 := by
  simp [observedEvents]
theorem no_tints_add_no_tint_events (result : Evaluation)
    (none : result.layers.foldl (fun count layer => count + layer.tints) 0 = 0) :
    observedEvents result = result.events := by simp [observedEvents,none]

end Host.Minecraft.ItemProgram
