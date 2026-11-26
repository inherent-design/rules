import Lean
import applications.vscode.Activation
open Lean ApplicationStudy.VscodeActivation

private structure Row where
  phase : String
  workspace : String
  action : String
  mainExited : Bool
  trackedAbsent : Bool
  deriving FromJson
private structure Input where
  schema : Nat
  profile : String
  initialGlobalDisabled : Bool
  events : List Row
  deriving FromJson

private def boolJson (v : Option Bool) : Json := toJson v
private def decodeAction : String → Except String Action
  | "startup" => pure .start | "activate" => pure .activate
  | "disable-workspace" => pure .disable | "enable-workspace" => pure .enable
  | "held-ping" => pure .ping | "quit-requested" => pure .quit
  | "retired" => pure .retire | _ => throw "Unknown activation study action."
private def decodeWorkspace : String → Except String Workspace
  | "a" => pure .a | "b" => pure .b | _ => throw "Unknown owned workspace."

private def run (input : Input) : Except String (List Json) := do
  if input.schema != 1 || input.profile != "vscode-1.148-owned-workspace-runtime" then
    throw "Unsupported activation study profile."
  if input.initialGlobalDisabled then throw "This native profile has no target global-disable intervention."
  if input.events.isEmpty || input.events.length > 24 then throw "Supply the bounded nonempty lifecycle."
  let mut state : State := {}
  let mut phase := ""
  let mut phases : List String := []
  let mut output := []
  for row in input.events do
    let w ← decodeWorkspace row.workspace
    let action ← decodeAction row.action
    if !["a-disable","b-other","a-enable","a-confirm"].contains row.phase then throw "Unknown phase identity."
    if action == .start then
      if state.alive || phases.contains row.phase then throw "Do not reopen a live or previously observed phase."
      if (row.phase == "b-other") != (w == .b) then throw "Workspace identity disagrees with phase."
      phase := row.phase
      phases := phases ++ [phase]
    else
      if !state.alive || phase != row.phase || state.workspace != w then throw "Action lacks its live phase/workspace."
    if action == .retire then
      if !state.quitting || !row.mainExited || !row.trackedAbsent then throw "Retirement needs quit, exit, and observed PID absence."
    else
      if row.mainExited || row.trackedAbsent then throw "Unexpected retirement witness for a live action."
      if state.quitting then throw "No extension action after quit request."
    if action == .activate && (!state.visible || state.activated) then throw "This profile activates an admitted dormant target."
    if action == .ping && !state.activated then throw "Captured API requires prior activation."
    if action == .disable && !state.activated then throw "Only active-target disablement is qualified by this trace."
    if action == .enable && state.visible then throw "Only absent inactive-target enablement is qualified by this trace."
    let result := observe state w action
    output := output ++ [Json.mkObj [
      ("phase",toJson row.phase),("action",toJson row.action),
      ("visible",boolJson result.visible),("apiActive",boolJson result.apiActive),
      ("ping",toJson result.ping),("storedOverride",toJson result.storedOverride),
      ("hooks",boolJson result.hooks),("retired",toJson result.retired)]]
    state := step state w action
  if state.alive || phases != ["a-disable","b-other","a-enable","a-confirm"] then
    throw "The normal four-phase trace is incomplete or reordered."
  return output

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one activation lifecycle JSON input."; return 2
  match Json.parse (← IO.FS.readFile path) >>= fromJson? (α := Input) >>= run with
  | .error error => IO.eprintln error; return 2
  | .ok value => IO.println (toJson value).compress; return 0
