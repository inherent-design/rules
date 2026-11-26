import Lean
import applications.«js-overrides».Overrides
open Lean ApplicationStudy.JsOverrides
private structure RawRule where
  scope : String
  version : String
  deriving FromJson
private structure RawStep where
  action : String
  rules : List RawRule
  target : String
  deriving FromJson
private structure Row where
  tool : String
  profile : String
  steps : List RawStep
  deriving FromJson
private structure Input where
  schema : Nat
  profile : String
  rows : List Row
  deriving FromJson
private def version : String → Except String Version
  | "1.0.0" => pure .one | "1.1.0" => pure .minor | "2.0.0" => pure .two
  | _ => throw "Outside the three-version generated catalog."
private def rule (r : RawRule) : Except String Rule := do
  let scope ← match r.scope with
    | "global" => pure Scope.global | "parent" => pure .parent | "converge" => pure .converge
    | "broad" => pure .broad | "narrow" => pure .narrow | _ => throw "Unknown selector scope."
  pure ⟨scope,← version r.version⟩
private def evaluate (r : Row) : Except String (List String) := do
  let tool ← match r.tool with
    | "npm" => pure Tool.npm | "pnpm" => pure .pnpm | "yarn" => pure .yarn
    | _ => throw "Unknown application."
  unless ["graph","direct","manual","range"].contains r.profile do throw "Unknown fixture profile."
  unless (r.profile != "manual" || tool == .yarn) && (r.profile != "range" || tool == .pnpm) do
    throw "Unadmitted tool/profile pair."
  unless !r.steps.isEmpty && r.steps.length ≤ 32 do throw "Trace bound."
  let steps ← r.steps.mapM fun s => do
    let action ← match s.action with
      | "install" => pure Action.install | "set" => pure .setResolution | "check" => pure .check
      | "remove-lock" => pure .removeLock | "query" => pure .query | _ => throw "Unknown operation."
    unless s.rules.length ≤ 2 do throw "Policy bound."
    let rules ← s.rules.mapM rule
    unless rules.eraseDups.length == rules.length do throw "Duplicate rule."
    if action != .install && !rules.isEmpty then throw "Policy is admitted only on an install request."
    if [Action.check,.setResolution,.removeLock].contains action && r.profile != "manual" then
      throw "Manual lock operation outside the selected Yarn workflow."
    if rules.any (fun x => x.scope == .converge) && (tool != .pnpm || rules.length != 1) then
      throw "Unqualified convergence interaction."
    if rules.any (fun x => x.scope == .broad || x.scope == .narrow) && r.profile != "range" then
      throw "Range precedence is only a bounded admission, not a predicted winner."
    if rules.any (fun x => x.scope == .parent) && r.profile != "graph" then throw "Parent selector without the graph."
    pure (Request.mk action rules (← version s.target))
  pure ((trace tool (r.profile == "direct" || r.profile == "manual") {} steps).map text)
def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one override trace input."; return 2
  match Json.parse (← IO.FS.readFile path) >>= fromJson? (α := Input) with
  | .error e => IO.eprintln e; return 2
  | .ok input =>
    if input.schema != 1 || input.profile != "generated-caret-override-traces" || input.rows.isEmpty || input.rows.length > 16 then
      IO.eprintln "Unsupported research schema/profile/count."; return 2
    match input.rows.mapM evaluate with
    | .error e => IO.eprintln e; return 2
    | .ok results => IO.println (toJson results).compress; return 0
