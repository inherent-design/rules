import Lean
import host.minecraft.ItemProgram

open Lean Host.Minecraft.ItemProgram Host.Java.FloatOrder

private structure RawInstruction where
  kind : Nat
  fieldsValid : Bool
  hasReference : Bool
  reference : Nat
  tints : Nat
  children : List Nat
  keys : List (List Nat)
  rowFieldsValid : List Bool
  fallbackKind : Nat
  fallbackChild : Nat
  thresholds : List Nat
  bodies : List Nat
  flipScale : Bool
  emptyRun : Nat
  deriving FromJson, Inhabited
private structure RawContext where
  id : Nat
  pick : Nat
  condition : Bool
  number : Nat
  color : Nat
  deriving FromJson
private structure Row where
  badFields : Option Bool
  scaleOverflow : Option Bool
  handAnimation : Option Bool
  oversized : Option Bool
  swapBits : Option Nat
  index : Option Nat
  program : Option (Array RawInstruction)
  contexts : Option (List RawContext)
  deriving FromJson
private structure Request where
  schema : Nat
  contract : String
  artifact : String
  contextContract : String
  rows : List Row
  deriving FromJson
private structure ObservedLayer where
  model : Nat
  tints : List Nat
  deriving ToJson
private structure ObservedContext where
  id : Nat
  layers : List ObservedLayer
  deriving ToJson
private structure Observed where
  error : Nat
  dependencies : List Nat
  events : List Nat
  handAnimation : Option Bool := none
  oversized : Option Bool := none
  swapBits : Option Nat := none
  contexts : List ObservedContext := []
  deriving ToJson

private def need {α : Type} (value : Option α) : Except String α :=
  match value with
  | some x => .ok x
  | none => .error "Required selected input evidence is unknown."

private def atom (value : Nat) : Except String Atom :=
  match value with
  | 0 => .ok .negativeTen | 1 => .ok .negativeZero | 2 => .ok .positiveZero
  | 3 => .ok .positiveTen | 4 => .ok .nan
  | _ => .error "Outside the selected float atoms."

private def instruction (raw : RawInstruction) : Instruction :=
  ⟨raw.kind,raw.fieldsValid,raw.hasReference,raw.reference,raw.tints,raw.children,
   raw.keys,raw.rowFieldsValid,raw.fallbackKind,raw.fallbackChild,raw.thresholds,
   raw.bodies,raw.flipScale,raw.emptyRun⟩

private def validate (raw : Array RawInstruction) (root : Nat) : Except String (Array Instruction) := do
  if raw.isEmpty || raw.size > 2048 || root + 1 != raw.size then
    throw "Outside the selected postorder program/root bounds."
  let mut references : List Nat := []
  let mut alternatives := 0
  for index in [:raw.size] do
    let node := raw[index]!
    if node.kind > 6 || node.reference > 255 || node.tints > 64 || node.emptyRun > 4096 then
      throw "Outside the selected instruction domain."
    if node.fallbackKind > 2 || (node.fallbackKind != 0 && node.kind != 4 && node.kind != 5) then
      throw "Unselected fallback owner or form."
    let children := node.children ++ (if node.fallbackKind == 2 then [node.fallbackChild] else [])
    if children.any (· >= index) then throw "Child is outside the earlier postorder frame."
    references := references ++ children
    if node.kind == 3 && node.fieldsValid && node.children.length != 2 then throw "Condition needs two children."
    if node.kind == 4 then
      if node.keys.length != node.children.length || node.rowFieldsValid.length != node.children.length then
        throw "Select evidence lengths differ."
    else if !node.keys.isEmpty then throw "Keys belong to select."
    if node.kind == 5 then
      if node.thresholds.length != node.children.length || node.bodies.length != node.children.length || node.rowFieldsValid.length != node.children.length then
        throw "Range evidence lengths differ."
      if node.thresholds.any (· > 4) || node.bodies.any (· > 4096) then throw "Unknown threshold/body evidence."
    else if !node.thresholds.isEmpty || !node.bodies.isEmpty then throw "Thresholds belong to range."
    if node.kind != 4 && node.kind != 5 && !node.rowFieldsValid.isEmpty then throw "Rows belong to select/range."
    if node.kind != 2 && node.kind != 3 && node.kind != 4 && node.kind != 5 && !node.children.isEmpty then
      throw "Children belong to recursive nodes."
    if node.emptyRun != 0 && (node.kind != 2 || !node.children.isEmpty) then
      throw "Empty-run compression requires an otherwise empty composite frame."
    if node.keys.any (fun keys => keys.any (· > 4096)) then throw "Key outside the selected identity frame."
    alternatives := alternatives + node.keys.foldl (fun n keys => n + keys.length) 0
  if alternatives > 2048 then throw "Outside the research alternative budget."
  -- A tree, not an arbitrary DAG: each earlier frame belongs to exactly one parent.
  for index in [:root] do
    if (references.filter (· == index)).length != 1 then throw "Postorder frame has missing or shared ownership."
  if 4 * raw.size + 2 * alternatives + 2 * references.length + 16 > 20000 then
    throw "Outside the research machine-step budget."
  return raw.map instruction

private def insert (value : Nat) : List Nat → List Nat
  | [] => [value]
  | x::xs => if value <= x then value::x::xs else x::insert value xs
private def sorted (values : List Nat) : List Nat := values.foldl (fun xs x => insert x xs) []
private def refused (state : State) : Observed :=
  ⟨state.error,[],state.reverseEvents.reverse,none,none,none,[]⟩

private def admit (row : Row) : Except String Observed := do
  let badFields ← need row.badFields
  if badFields then return refused (failure {} 1)
  let index ← need row.index
  let program ← validate (← need row.program) index
  let compiled := compileRoot ⟨false,false,true,false,1065353216,index,program⟩
  if compiled.error != 0 then return refused compiled
  let overflow ← need row.scaleOverflow
  if overflow then return refused (failure compiled 14)
  let hand ← need row.handAnimation
  let oversized ← need row.oversized
  let swapBits ← need row.swapBits
  if swapBits >= 4294967296 || (swapBits / 8388608) % 256 == 255 then
    throw "Returned swap scale needs a selected finite float representation."
  let contexts ← need row.contexts
  if contexts.length > 16 || (contexts.map (·.id)).eraseDups.length != contexts.length then
    throw "Unselected context batch/identity."
  let mut results : List ObservedContext := []
  let mut events := compiled.reverseEvents.reverse
  for context in contexts do
    if context.id > 4096 || context.pick > 4096 || context.color > 255 then
      throw "Context outside selected roles/marker values."
    let number ← atom context.number
    let result := evaluate 35 program index ⟨context.pick,context.condition,number,context.color⟩
    if !result.valid then throw "Research evaluator did not establish a selected result."
    results := results ++ [⟨context.id,result.layers.map (fun layer => ⟨layer.model,List.replicate layer.tints context.color⟩)⟩]
    events := events ++ observedEvents result
  return ⟨0,sorted compiled.dependencies,events,some hand,some oversized,some swapBits,results⟩

private def decode (input : Json) : Except String Json := do
  let request ← fromJson? (α := Request) input
  if request.schema != 1 || request.contract != "generic-resource-program-v1" ||
      request.contextContract != "authored-values-json-v1" ||
      request.artifact != "4ae402eaa858eef4141858554a3f9f0867f6e2ddc72e68313668187a3058e5d5" || request.rows.length > 64 then
    throw "Unselected source, schema, context contract or batch."
  return toJson (← request.rows.mapM admit)

def main (args : List String) : IO UInt32 := do
  let (batch,path) ← match args with
    | [path] => pure (false,path)
    | ["--batch",path] => pure (true,path)
    | _ => IO.eprintln "Supply a request path, or --batch and a research packet-array path."; return 2
  match Json.parse (← IO.FS.readFile path) with
  | .error error => IO.eprintln error; return 2
  | .ok input =>
    if batch then
      match fromJson? (α := List Json) input with
      | .error error => IO.eprintln error; return 2
      | .ok packets =>
        if packets.length > 64 then IO.eprintln "Outside research packet-array bound."; return 2
        -- Each packet uses the identical decoder; this amortizes Lean startup in CI.
        let statuses := packets.map (fun packet => match decode packet with | .ok _ => (0 : Nat) | .error _ => 2)
        IO.println (toJson statuses).compress; return 0
    else
      match decode input with
      | .error error => IO.eprintln error; return 2
      | .ok value => IO.println value.compress; return 0
