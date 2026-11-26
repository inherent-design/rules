import Lean
import applications.«pnpm-admission».Admission
open Lean ApplicationStudy.PnpmAdmission

private structure Raw where
  kind : String
  name : String
  rawArgs : List String
  forcedBuiltin : Bool
  builtinHelp : Bool
  inMember : Bool
  localBody : Bool
  rootBody : Bool
  scriptLabel : String
  args : List String
  deriving FromJson
private structure Input where
  schema : Nat
  profile : String
  cases : List Raw
  deriving FromJson

private def evaluate (r : Raw) : Except String Json := do
  let kind ← match r.kind with
    | "tasks" => pure Kind.tasks | "placeholder" => pure .placeholder
    | "explicit-run" => pure .explicitRun | "declared-fallback" => pure .declaredFallback
    | _ => throw "Unsupported command namespace."
  unless ["tasks","edit","xmas","fixture-inventory-script","pm"].contains r.name do throw "Unsupported fixture name."
  unless r.rawArgs.length ≤ 6 && r.args.length ≤ 3 do throw "Argument profile is too large."
  unless r.args.all (fun a => ["status","tasks","--help","--literal","--fixture-option"].contains a) do
    throw "Unsupported fixture argument."
  let (forced,tokens) := splitLeadingPm r.rawArgs
  unless forced == r.forcedBuiltin do throw "Prefix evidence disagrees with the raw arguments."
  let tokens := if tokens.take 2 == ["--dir","."] then tokens.drop 2 else tokens
  let expected := (if kind == .explicitRun then ["run",r.name] else [r.name]) ++ r.args
  unless tokens == expected do throw "Parsed request disagrees with the raw arguments."
  unless r.inMember || r.localBody == r.rootBody do throw "Root and local body evidence disagree."
  unless !r.inMember || !r.localBody do throw "This member fixture has no local script."
  let expectedLabel := if r.name == "fixture-inventory-script" then "fallback" else r.name
  unless r.scriptLabel == (if r.localBody then expectedLabel else "") do throw "Script-body label evidence is inconsistent."
  unless kind == .tasks || !r.builtinHelp do throw "Only tasks parser help is in this profile."
  match kind with
  | .tasks =>
    unless r.name == "tasks" && r.args == (if r.builtinHelp then ["--help"] else ["status"]) do throw "Unsupported tasks operand."
  | .placeholder =>
    unless (r.name == "edit" && r.args == []) || (r.name == "xmas" && r.args == ["--fixture-option"]) do throw "Unsupported placeholder profile."
  | .explicitRun =>
    unless r.localBody && ["tasks","edit"].contains r.name do throw "Explicit run needs an admitted local script."
  | .declaredFallback =>
    unless r.localBody && !r.forcedBuiltin && ["fixture-inventory-script","pm"].contains r.name do throw "Only declared-script fallback is admitted."
  let out := run ⟨kind,r.forcedBuiltin,r.builtinHelp,r.inMember,r.localBody,r.rootBody,r.scriptLabel,r.args⟩
  pure (Json.arr #[toJson out.action,toJson out.status,toJson out.scriptLabel,toJson out.args,toJson out.childNpmCommand])

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one retained namespace input."; return 2
  match Json.parse (← IO.FS.readFile path) >>= fromJson? (α := Input) with
  | .error e => IO.eprintln e; return 2
  | .ok input =>
    if input.schema != 1 || input.profile != "pnpm-command-script-namespace" || input.cases.isEmpty || input.cases.length > 32 then
      IO.eprintln "Unsupported namespace study schema, profile, or count."; return 2
    match input.cases.mapM evaluate with
    | .error e => IO.eprintln e; return 2
    | .ok values => IO.println (toJson values).compress; return 0
