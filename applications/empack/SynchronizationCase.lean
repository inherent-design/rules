import Lean
import applications.empack.Synchronization
open Lean ApplicationStudy.EmpackSynchronization

private structure RootRow where
  key : String
  project : Option Nat
  pin : Option Nat
  deriving FromJson
private structure NodeRow where
  key : String
  project : Nat
  version : Nat
  record : String
  coverage : Nat
  edgesPresent : Bool
  edges : List String
  deriving FromJson
private structure RuntimeRow where
  game : String
  loader : String
  version : Option String
  deriving FromJson
private structure Row where
  roots : List RootRow
  prior : List NodeRow
  proposed : List NodeRow
  requestedRuntime : RuntimeRow
  priorRuntime : RuntimeRow
  proposedRuntime : RuntimeRow
  requestedAccepted : List String
  priorAccepted : List String
  proposedAccepted : List String
  sameRevision : Bool
  deriving FromJson
private structure Request where
  schema : Nat
  cases : List Row
  deriving FromJson
private def node (n : NodeRow) : Node := ⟨n.key,n.project,n.version,n.record,n.coverage,n.edgesPresent,n.edges⟩
private def runtime (r : RuntimeRow) : Runtime := ⟨r.game,r.loader,r.version⟩
private def encodeNode (n : Node) : Json := Json.mkObj [
  ("key",toJson n.key),("project",toJson n.project),("version",toJson n.version),
  ("record",toJson n.record),("coverage",toJson n.coverage),
  ("edgesPresent",toJson n.edgesPresent),("edges",toJson n.edges)]
private def checked (r : Row) : Except String Input := do
  let keys := r.roots.map (·.key)
  if canonical keys != keys then throw "Unsupported or repeated root key/order."
  for root in r.roots do
    if root.project.any (fun p => p < 1 || p > 5) || root.pin.any (fun p => p < 1 || p > 2) ||
        (root.project.isNone && root.pin.isSome) then throw "Root outside the captured provider/search profile."
  for nodes in [r.prior,r.proposed] do
    let keys := nodes.map (·.key)
    let projects := nodes.map (·.project)
    if canonical keys != keys || projects.eraseDups.length != projects.length then
      throw "Unsupported, repeated, or unordered node identity."
    for n in nodes do
      if n.project < 1 || n.project > 5 || n.version < 1 || n.version > 2 || n.coverage > 1 ||
          n.record.isEmpty || n.record.length > 8192 || canonical n.edges != n.edges ||
          n.edges.any (fun k => !keys.contains k) || (!n.edgesPresent && !n.edges.isEmpty) then
        throw "Node outside the captured graph/evidence profile."
  for rt in [r.requestedRuntime,r.priorRuntime,r.proposedRuntime] do
    if rt.game != "1.21.1" || rt.loader != "Fabric" ||
        rt.version.any (fun v => v != "0.16.0" && v != "0.17.0") then
      throw "Runtime outside the captured Fabric profile."
  if r.priorRuntime.version.isNone || r.proposedRuntime.version.isNone then throw "Selected runtime needs an exact loader."
  for accepted in [r.requestedAccepted,r.priorAccepted,r.proposedAccepted] do
    if accepted != [] && accepted != ["1.21"] then throw "Accepted game list outside the captured profile."
  let input : Input := ⟨r.roots.map (fun v => ⟨v.key,v.project,v.pin⟩),r.prior.map node,r.proposed.map node,
    runtime r.requestedRuntime,runtime r.priorRuntime,runtime r.proposedRuntime,
    r.requestedAccepted,r.priorAccepted,r.proposedAccepted,r.sameRevision⟩
  if let .ok prior := rebind input.roots input.prior then
    for old in prior do
      if let some next := lookup input.proposed old.key then
        if old.project == next.project && old.version == next.version && old.record != next.record then
          throw "Same-selection record edits require a separate evidence model."
  pure input
private def output (r : Outcome) : Json := Json.mkObj [
  ("runtimeSatisfied",toJson r.runtimeSatisfied),("affected",toJson r.affected),
  ("normalized",(r.normalized.map (fun nodes => toJson (nodes.map encodeNode))).getD Json.null),
  ("stage",toJson r.stage),("result",toJson r.result),("changed",toJson r.changed),("reason",toJson r.reason)]
def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one synchronization research input."; return 2
  match Json.parse (← IO.FS.readFile path) >>= fromJson? (α := Request) with
  | .error error => IO.eprintln error; return 2
  | .ok request =>
    if request.schema != 1 then IO.eprintln "Unsupported synchronization research schema."; return 2
    match request.cases.mapM (fun row => checked row >>= fun input => pure (output (evaluate input))) with
    | .error error => IO.eprintln error; return 2
    | .ok result => IO.println (toJson result).compress; return 0
