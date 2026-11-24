import Lean
import applications.«js-peers».LockModes
open Lean ApplicationStudy.JsLockModes

private structure Row where
  profile : String
  mode : String
  wanted : Nat
  locked : Nat
  payload : Nat
  hidden : Nat
  deriving FromJson

private structure Input where
  schema : Nat
  cases : List Row
  deriving FromJson

private def revision : Nat → Except String Revision
  | 0 => pure .absent
  | 1 => pure .one
  | 2 => pure .two
  | _ => throw "Unsupported fixture revision."

private def label : Revision → String
  | .absent => "0" | .one => "1" | .two => "2"

private def evaluate (r : Row) : Except String String := do
  let profile ← match r.profile with
    | "npm" => pure Profile.npm | "pnpm" => pure Profile.pnpm | "yarn" => pure Profile.yarn
    | _ => throw "Unsupported lock-mode profile."
  let mode ← match r.mode with
    | "refresh" => pure Mode.refresh | "frozen" => pure Mode.frozen | "resolve-only" => pure Mode.resolveOnly
    | _ => throw "Unsupported install mode."
  if r.wanted == 0 then throw "Fixture requires one declared dependency."
  if r.profile != "npm" && r.hidden != 0 then throw "Hidden index belongs to npm profile only."
  let s : State := ⟨← revision r.wanted, ← revision r.locked, ← revision r.payload, ← revision r.hidden⟩
  let result := step profile mode s
  pure (String.intercalate "/" [if accepted mode s then "1" else "0",
    label result.locked, label result.payload, label result.hidden])

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one lock-mode input JSON path."; return 2
  let text ← IO.FS.readFile path
  match Json.parse text >>= fromJson? (α := Input) with
  | .error error => IO.eprintln error; return 2
  | .ok input =>
    if input.schema != 1 then IO.eprintln "Unsupported lock-mode schema."; return 2
    match input.cases.mapM evaluate with
    | .error error => IO.eprintln error; return 2
    | .ok values => IO.println (toJson values).compress; return 0
