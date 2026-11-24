import Lean
import applications.«js-config».Configuration
open Lean ApplicationStudy.JsConfiguration
private structure Row where
  app : String
  global : Option Nat
  home : Option Nat
  project : Option Nat
  environment : Option Nat
  command : Option Nat
  globalMode : Bool
  customRc : Bool
  fallback : Nat
  action : String
  location : Option String
  value : Nat
  deriving FromJson
private structure Input where
  schema : Nat
  cases : List Row
  deriving FromJson
private def scope (s : String) : Except String Scope := match s with
  | "global" => pure .global | "home" => pure .home | "project" => pure .project
  | _ => throw "Unknown config fixture scope."
private def source : Source → String
  | .fallback => "default" | .global => "global" | .home => "home" | .project => "project"
  | .environment => "environment" | .command => "command"
private def scopeName : Scope → String
  | .global => "global" | .home => "home" | .project => "project"
private def item (n : Option Nat) : String := toString (n.getD 0)
private def evaluate (v : Row) : Except String String := do
  let app ← match v.app with
    | "npm" => pure App.npm | "pnpm" => pure App.pnpm | "yarn" => pure App.yarn
    | _ => throw "Unknown config fixture app."
  let action ← match v.action with
    | "get" => pure Action.read | "explain" => pure Action.explain
    | "set" => pure Action.set | "unset" => pure Action.unset
    | _ => throw "Unknown config fixture action."
  let location ← v.location.mapM scope
  if v.value == 0 || v.value > 10 || v.fallback == 0 || v.fallback > 10 then throw "Unsupported config fixture identity."
  if [v.global,v.home,v.project,v.environment,v.command].any (fun n => n.any (fun n => n == 0 || n > 10)) then
    throw "Unsupported config witness identity."
  if app == .yarn && (v.global.isSome || v.globalMode || v.command.isSome || location == some .global) then
    throw "Unsupported Yarn scalar fixture profile."
  if app == .pnpm && (v.home.isSome || location == some .home) then throw "Unsupported pnpm scalar fixture profile."
  let r : Request := ⟨app,⟨v.global,v.home,v.project⟩,⟨v.environment,v.command,v.globalMode,v.customRc,v.fallback⟩,action,location,v.value⟩
  let s := after r
  let e := currentEffective r
  let wrote := if action == .set || action == .unset then scopeName (target r) else "none"
  pure (String.intercalate "/" [item s.global,item s.home,item s.project,toString e.value,source e.source,wrote,item (reportedSetValue r)])
def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one config-model file."; return 2
  let text ← IO.FS.readFile path
  match Json.parse text >>= fromJson? (α := Input) with
  | .error error => IO.eprintln error; return 2
  | .ok input =>
    if input.schema != 1 then IO.eprintln "Unsupported config research schema."; return 2
    match input.cases.mapM evaluate with
    | .error error => IO.eprintln error; return 2
    | .ok values => IO.println (toJson values).compress; return 0
