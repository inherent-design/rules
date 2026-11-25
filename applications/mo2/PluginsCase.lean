import Lean
import applications.mo2.Plugins
open Lean ApplicationStudy.Mo2Plugins

private structure PluginRow where
  id : Nat
  enabled : Bool
  loaded : Bool
  forced : Bool
  disabled : Bool
  priority : Int
  loadOrder : Int
  masters : List Nat
  missing : List Nat
  deriving FromJson
private structure ActionRow where
  kind : Nat
  target : Nat
  active : Bool
  names : List Nat
  deriving FromJson
private structure CaseRow where
  id : String
  plugins : List PluginRow
  actions : List ActionRow
  deriving FromJson
private structure Input where
  schema : Nat
  cases : List CaseRow
  deriving FromJson
private structure PluginView where
  id : Nat
  enabled : Bool
  priority : Int
  loadOrder : Int
  missing : List Nat
  indexed : Bool
  deriving ToJson
private structure EventView where
  kind : Nat
  ids : List Nat
  active : Bool
  deriving ToJson
private structure View where
  plugins : List PluginView
  byPriority : List Nat
  writeRequests : Nat
  indexCalls : Nat
  events : List EventView
  errors : Nat
  warnings : Nat
  deriving ToJson
private def view (s : State) : View :=
  ⟨s.plugins.map (fun p => ⟨p.id,p.enabled,p.priority,p.loadOrder,p.missing,p.indexed⟩),
    s.byPriority,s.writeRequests,s.indexCalls,s.events.map (fun e => ⟨e.kind,e.ids,e.active⟩),s.errors,s.warnings⟩
private structure OutputRow where
  id : String
  before : View
  steps : List View
  deriving ToJson
private def run (row : CaseRow) : Except String OutputRow := do
  let n := row.plugins.length
  if n == 0 || n > 3 || row.plugins.map (·.id) != List.range n then
    throw "Plugin catalog IDs must be contiguous in the admitted fixture."
  if (row.plugins.map (·.priority)).mergeSort != (List.range n).map Int.ofNat then
    throw "Initial plugin priority must be a permutation."
  if row.plugins.any (fun p => p.loadOrder < -1 || p.loadOrder ≥ Int.ofNat n ||
      (p.masters ++ p.missing).any (· ≥ 6)) then
    throw "Plugin metadata outside the admitted field profile."
  if row.plugins.any (fun p => p.masters.eraseDups.length != p.masters.length ||
      p.missing.eraseDups.length != p.missing.length) then
    throw "Master metadata must be a set-shaped admitted sequence."
  if row.actions.any (fun a => a.kind > 5 || a.target ≥ 6 || a.names.any (· ≥ 6)) then
    throw "Unsupported plugin operation or fixture name."
  let plugins := row.plugins.map fun p => Plugin.mk p.id p.enabled p.loaded p.forced p.disabled
    p.priority p.loadOrder p.masters p.missing true
  let initial : State := { plugins, byPriority := (List.range n).map fun rank =>
    ((plugins.find? fun p => p.priority == Int.ofNat rank).map (·.id)).getD 0 }
  let final := row.actions.foldl (fun (acc : State × List View) a =>
    let next := apply ⟨a.kind,a.target,a.active,a.names⟩ acc.1
    (next,acc.2 ++ [view next])) (initial,[])
  return ⟨row.id,view initial,final.2⟩

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one plugin study JSON path."; return 2
  let text ← IO.FS.readFile path
  match Json.parse text >>= fromJson? (α := Input) with
  | .error error => IO.eprintln error; return 2
  | .ok input =>
    if input.schema != 1 then IO.eprintln "Unsupported plugin study schema."; return 2
    match input.cases.mapM run with
    | .error error => IO.eprintln error; return 2
    | .ok output => IO.println (toJson output).compress; return 0
