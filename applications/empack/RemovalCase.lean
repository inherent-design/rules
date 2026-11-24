import Lean
import applications.empack.Removal
open Lean ApplicationStudy.EmpackRemoval
private structure NodeRow where
  key : Nat
  record : String
  coverage : Nat
  edgesPresent : Bool
  edges : List Nat
  deriving FromJson
private structure StateRow where
  roots : List Nat
  nodes : List NodeRow
  deriving FromJson
private structure CaseRow where
  operation : String
  before : StateRow
  mode : String := "content"
  acknowledge : Bool := false
  selection : List Nat := []
  request : Option StateRow := none
  deriving FromJson
private structure Input where
  schema : Nat
  cases : List CaseRow
  deriving FromJson
private def checkedState (s : StateRow) : Except String State := do
  let keys := s.nodes.map (·.key)
  if keys != canonical keys || keys.any (· > 3) || s.roots != canonical s.roots ||
      s.roots.any (fun k => !keys.contains k) then throw "Unsupported state keys/order."
  for n in s.nodes do
    if n.record.isEmpty || n.record.length > 8192 || n.coverage > 2 ||
        n.edges != canonical n.edges || n.edges.any (fun k => !keys.contains k) ||
        (!n.edgesPresent && !n.edges.isEmpty) then throw "Unsupported exact record/coverage/graph."
  pure ⟨s.roots,s.nodes.map (fun n => ⟨n.key,n.record,n.coverage,n.edgesPresent,n.edges⟩)⟩
private def encodeState (s : State) : Json := Json.mkObj [
  ("roots",toJson s.roots),("nodes",toJson (s.nodes.map fun n => Json.mkObj [
    ("key",toJson n.key),("record",toJson n.record),("coverage",toJson n.coverage),
    ("edgesPresent",toJson n.edgesPresent),("edges",toJson n.edges)]))]
private def evaluate (c : CaseRow) : Except String Json := do
  let s ← checkedState c.before
  if c.operation == "remove" then
    if c.selection.isEmpty || c.selection.any (fun k => k < 1 || k > 4) || c.request.isSome ||
        (c.mode != "content" && c.mode != "forget") then throw "Unsupported removal request."
    let mode := if c.mode == "forget" then Mode.forget else .content
    pure <| match remove s c.selection mode c.acknowledge with
    | .error e => Json.mkObj [("error",Json.mkObj [("kind",toJson e.kind),("keys",toJson e.keys)]),("after",Json.null)]
    | .ok r => Json.mkObj [("error",Json.null),("selected",toJson r.selected),
        ("removed",toJson r.removed),("incomplete",toJson r.incomplete),("after",encodeState r.after)]
  else
    if !["add","adopt","update"].contains c.operation || !c.selection.isEmpty || c.acknowledge then
      throw "Unsupported request-merge operation."
    let some request := c.request | throw "Request evidence required."
    let request ← checkedState request
    if !s.roots.isEmpty || (s.nodes.map (·.key) != [1,2,3] && s.nodes.map (·.key) != [2,3]) ||
        request.roots != [1] || request.nodes.map (·.key) != [1,2] then throw "Outside the captured re-addition profile."
    for n in s.nodes ++ request.nodes do
      if n.coverage != 0 || n.edges != (if n.key == 1 then [2] else []) ||
          n.edgesPresent != (n.key == 1) then throw "Unsupported request graph/evidence."
    for n in request.nodes do
      if let some old := lookup s n.key then
        if old != n then throw "Changed selections/records need a separate addition model."
    pure <| match readd s request c.operation with
    | .error e => Json.mkObj [("error",toJson e),("after",Json.null)]
    | .ok r => Json.mkObj [("error",Json.null),("existingRequests",toJson r.existing),
      ("changedRecords",toJson r.changed),("rejectExistingWouldAllow",toJson r.rejectExistingWouldAllow),
      ("after",encodeState r.after)]
def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one removal research input."; return 2
  match Json.parse (← IO.FS.readFile path) >>= fromJson? (α := Input) with
  | .error error => IO.eprintln error; return 2
  | .ok input =>
    if input.schema != 1 then IO.eprintln "Unsupported removal research schema."; return 2
    match input.cases.mapM evaluate with
    | .error error => IO.eprintln error; return 2
    | .ok results => IO.println (toJson results).compress; return 0
