import Lean
import applications.vscode.Trust
open Lean ApplicationStudy.VscodeTrust

private structure Row where
  trustEnabled : Bool
  hasEntry : Bool
  configured : Nat
  version : Nat
  override : Nat
  declared : Nat
  fallback : Nat
  deriving FromJson

private structure Input where
  schema : Nat
  cases : List Row
  deriving FromJson

private def decode : Nat → Except String (Option Support)
  | 0 => pure none | 1 => pure (some .deny)
  | 2 => pure (some .allow) | 3 => pure (some .limited)
  | _ => throw "Unknown support code."

private def code : Support → Nat
  | .deny => 1 | .allow => 2 | .limited => 3

private def simulate (row : Row) : Except String Json := do
  if row.version > 2 then throw "Unknown version-admission code."
  let value := support row.trustEnabled row.hasEntry (row.version != 2)
    (← decode row.configured) (← decode row.override)
    (← decode row.declared) (← decode row.fallback)
  return Json.mkObj [("selected", toJson (code value)),
    ("blocked", toJson ([blocked false false value, blocked false true value,
      blocked true false value, blocked true true value]))]

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one trust-predicate JSON input."; return 2
  match Json.parse (← IO.FS.readFile path) >>= fromJson? (α := Input) with
  | .error error => IO.eprintln error; return 2
  | .ok input =>
    if input.schema != 1 then IO.eprintln "Unsupported trust schema."; return 2
    match input.cases.mapM simulate with
    | .error error => IO.eprintln error; return 2
    | .ok output => IO.println (toJson output).compress; return 0
