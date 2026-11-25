import Lean
import applications.prism.Commands
open Lean ApplicationStudy.PrismCommands

private structure Row where
  id : String
  mode : Nat
  rawNonempty : Bool
  trimmedEmpty : Bool
  tokens : List Nat
  programExists : Bool
  processResult : Nat
  abortRequested : Bool
  gameArgs : List Nat
  deriving FromJson
private structure Input where
  schema : Nat
  cases : List Row
  deriving FromJson
private structure View where
  id : String
  disposition : Nat
  terminal : Bool
  successful : Bool
  child : Bool
  abortAccepted : Bool
  childArgs : List Nat
  deriving ToJson
private def run (r : Row) : Except String View := do
  if r.mode > 2 || r.processResult > 3 || r.tokens.length > 12 || r.gameArgs.length > 8 ||
      r.tokens.any (· > 31) || r.gameArgs.any (· > 31) then
    throw "Unsupported Prism command research profile."
  let req : Request := ⟨r.mode,r.rawNonempty,r.trimmedEmpty,r.tokens,r.programExists,
                        r.processResult,r.abortRequested,r.gameArgs⟩
  return ⟨r.id,disposition req,terminal req,successful req,child req,abortAccepted req,childArgs req⟩

def main (args : List String) : IO UInt32 := do
  let path ← match args with
    | [p] => pure p
    | _ => throw (IO.userError "Supply one command research packet.")
  let text ← IO.FS.readFile path
  let result := do
    let j ← Json.parse text
    let input ← fromJson? (α := Input) j
    if input.schema != 1 then throw "Unsupported Prism command research schema."
    input.cases.mapM run
  match result with
  | .error message => (← IO.getStderr).putStrLn message; return 2
  | .ok rows => (← IO.getStdout).putStrLn ((toJson rows).compress); return 0
