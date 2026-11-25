import Lean
import applications.«js-workspace-publish».WorkspacePublication
open Lean ApplicationStudy.WorkspacePublication ApplicationStudy.JsPublication

private structure Row where
  profile : String
  failure : String
  deriving FromJson
private structure Input where
  schema : Nat
  cases : List Row
  deriving FromJson
private def evaluate (r : Row) : Except String (List Nat) := do
  let p ← match r.profile with
    | "npm" => pure Profile.npm | "pnpm" => pure Profile.pnpm | "yarn" => pure Profile.yarn
    | _ => throw "Unsupported workspace publication profile."
  let f ← match r.failure with
    | "none" => pure Failure.none | "producerLate" => pure Failure.producerLate | "privateEarly" => pure Failure.privateEarly
    | _ => throw "Unsupported workspace failure boundary."
  let o := run p f
  pure [if o.privateHook then 1 else 0, if o.producerAccepted then 1 else 0,
    if o.consumerAccepted then 1 else 0, if o.consumerBlocked then 1 else 0,
    o.order, if o.rewritten then 1 else 0, o.summaryCount, o.code]
def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one workspace publication JSON path."; return 2
  match Json.parse (← IO.FS.readFile path) >>= fromJson? (α := Input) with
  | .error e => IO.eprintln e; return 2
  | .ok input =>
    if input.schema != 1 then IO.eprintln "Unsupported workspace publication schema."; return 2
    match input.cases.mapM evaluate with
    | .error e => IO.eprintln e; return 2
    | .ok result => IO.println (toJson result).compress; return 0
