import Lean
import applications.«js-peers».Removal
open Lean ApplicationStudy.JsRemoval

private structure Row where
  profile : String
  action : String
  parent : Bool
  leaf : Bool
  deriving FromJson

private structure Input where
  schema : Nat
  cases : List Row
  deriving FromJson

private def bit (value : Bool) : String := if value then "1" else "0"

private def evaluate (row : Row) : Except String String := do
  let profile ← match row.profile with
    | "npm" => pure Profile.npm
    | "pnpm" => pure Profile.pnpm
    | "yarn" => pure Profile.yarn
    | _ => throw "Unknown removal profile."
  let action ← match row.action with
    | "remove-leaf" => pure Action.removeLeaf
    | "add-leaf" => pure Action.addLeaf
    | "remove-parent" => pure Action.removeParent
    | _ => throw "Unknown declaration edit."
  let roots : Roots := ⟨row.parent, row.leaf⟩
  let result := next profile action roots
  pure (String.intercalate "/" [bit (accepted profile action roots), bit result.parent,
    bit result.leaf, bit (liveLeaf result), bit (rootCanLoadLeaf profile result)])

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one removal input JSON path."; return 2
  let text ← IO.FS.readFile path
  match Json.parse text >>= fromJson? (α := Input) with
  | .error error => IO.eprintln error; return 2
  | .ok input =>
    if input.schema != 1 then
      IO.eprintln "Unsupported removal schema."
      return 2
    match input.cases.mapM evaluate with
    | .error error => IO.eprintln error; return 2
    | .ok result => IO.println (toJson result).compress; return 0
