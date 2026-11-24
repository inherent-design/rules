import Lean
import applications.mo2.Profile
open Lean ApplicationStudy.Mo2Profile

private structure Row where
  id : String
  mode : String
  policies : List String
  before : List Bool
  target : Nat
  request : Bool
  enable : List Nat
  disable : List Nat
  deriving FromJson

private structure Input where
  schema : Nat
  cases : List Row
  deriving FromJson

private structure Output where
  id : String
  state : List Bool
  signals : List (List Nat)
  loggedErrors : Nat
  threw : Bool
  deriving ToJson

private def evaluate (row : Row) : Except String Output := do
  if row.policies.length != row.before.length then
    throw "Profile and catalog lengths differ."
  let policies ← row.policies.mapM fun policy => match policy with
    | "free" => pure Policy.free
    | "on" => pure Policy.alwaysOn
    | "off" => pure Policy.alwaysOff
    | _ => throw "Unknown activation policy."
  let entries := (List.range policies.length).zip (policies.zip row.before)
    |>.map fun (id, policy, enabled) => Entry.mk id policy enabled
  let result ← match row.mode with
    | "single" => pure (single entries row.target row.request)
    | "batch" => pure (batch entries row.enable row.disable)
    | _ => throw "Unknown activation operation."
  pure ⟨row.id, result.entries.map (·.enabled), result.signals, result.loggedErrors, result.threw⟩

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one profile input JSON path."; return 2
  let text ← IO.FS.readFile path
  match Json.parse text >>= fromJson? (α := Input) with
  | .error error => IO.eprintln error; return 2
  | .ok input =>
    if input.schema != 1 then
      IO.eprintln "Unsupported profile schema."
      return 2
    match input.cases.mapM evaluate with
    | .error error => IO.eprintln error; return 2
    | .ok result => IO.println (toJson result).compress; return 0
