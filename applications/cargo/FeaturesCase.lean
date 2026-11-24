import Lean
import applications.cargo.Features
open Lean ApplicationStudy.CargoFeatures

private structure Row where
  resolver : Nat
  context : String
  projection : String
  noDefault : Bool
  allFeatures : Bool
  featureArg : Nat
  workspace : Bool
  tests : Bool
  deriving FromJson
private structure Input where
  schema : Nat
  cases : List Row
  deriving FromJson

private def simulate (row : Row) : Except String Json := do
  if row.context != "app-member-native-mac" then throw "Unsupported Cargo feature context."
  if row.projection != "compiled-roles" then throw "Metadata is not a compiled-role projection."
  let resolver ← match row.resolver with
    | 1 => pure Resolver.one | 2 => pure Resolver.two | 3 => pure Resolver.three
    | _ => throw "Unknown Cargo resolver."
  let arg ← match row.featureArg with
    | 0 => pure FeatureArg.none | 1 => pure FeatureArg.bare | 2 => pure FeatureArg.qualified
    | _ => throw "Unknown Cargo feature argument."
  if arg == .qualified && (row.workspace || row.tests || row.allFeatures || !row.noDefault) then
    throw "Qualified syntax is outside the retained single-app request profile."
  if row.workspace && (!row.noDefault || row.allFeatures || arg != .none || row.tests) then
    throw "Workspace root feature selection is outside the retained no-default build profile."
  let q : Request := ⟨resolver,row.noDefault,row.allFeatures,arg,row.workspace,row.tests⟩
  if refused q then return Json.mkObj [("code",toJson (101 : Nat)),("normal",Json.null),("build",Json.null)]
  return Json.mkObj [("code",toJson (0 : Nat)),("normal",toJson (mask (selected q .normal))),
    ("build",toJson (mask (selected q .build)))]

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one Cargo feature JSON input."; return 2
  match Json.parse (← IO.FS.readFile path) >>= fromJson? (α := Input) with
  | .error error => IO.eprintln error; return 2
  | .ok input =>
    if input.schema != 1 then IO.eprintln "Unsupported Cargo feature schema."; return 2
    match input.cases.mapM simulate with
    | .error error => IO.eprintln error; return 2
    | .ok output => IO.println (toJson output).compress; return 0
