import Lean
import applications.«js-scripts».Policy
open Lean ApplicationStudy.JsScripts

private structure Row where
  app : String
  approval : Option Bool
  disabled : Bool
  broad : Bool
  fail : Bool
  scope : String
  deriving FromJson

private structure Input where
  schema : Nat
  cases : List Row
  deriving FromJson

private structure Output where
  decision : String
  effects : List String
  succeeds : Bool
  deriving ToJson

private def evaluate (row : Row) : Except String Output := do
  let profile ← match row.app with
    | "npm" => pure (Profile.npm row.disabled row.broad)
    | "pnpm" => pure (Profile.pnpm row.disabled row.broad)
    | "yarn" => pure (Profile.yarn (!row.disabled))
    | _ => throw "Unknown script-policy profile."
  let review := match row.approval with
    | none => Review.unreviewed
    | some true => Review.allow
    | some false => Review.deny
  let scope ← match row.scope with
    | "dependency" => pure Scope.dependencyInstall
    | "root" | "explicit-root" => pure Scope.workspaceInstall
    | _ => throw "Unknown script-policy scope."
  let selected := decision profile scope review
  let effects := installEffects scope selected
  if row.scope == "explicit-root" then
    pure ⟨label (decision profile .explicitRootRun review), effects ++ explicitRootEffects profile, true⟩
  else pure ⟨label selected, effects, installSucceeds scope selected row.fail⟩

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one script-policy JSON path."; return 2
  let text ← IO.FS.readFile path
  match Json.parse text >>= fromJson? (α := Input) with
  | .error error => IO.eprintln error; return 2
  | .ok input =>
    if input.schema != 1 then
      IO.eprintln "Unsupported script-policy schema."
      return 2
    match input.cases.mapM evaluate with
    | .error error => IO.eprintln error; return 2
    | .ok results => IO.println (toJson results).compress; return 0
