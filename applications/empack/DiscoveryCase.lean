import Lean
import applications.empack.Discovery
open Lean ApplicationStudy.EmpackDiscovery

private structure Row where
  id : String
  entries : Nat
  limit : Nat
  matching : List Nat
  explicit : Option Nat
  explicitMatches : Bool
  deriving FromJson
private structure Input where
  schema : Nat
  cases : List Row
  deriving FromJson
private structure View where
  id : String
  kind : Nat
  selected : Option Nat
  published : Bool
  exitCode : Nat
  deriving ToJson
private def run (r : Row) : Except String View := do
  if r.limit != 10000 || r.entries > 10001 || r.matching.length > 2 ||
      r.matching.any (· > 1) || r.explicit.isSome && r.explicit.getD 0 > 1 then
    throw "Unsupported discovery research profile."
  let d := choose ⟨r.entries, r.limit, r.matching, r.explicit, r.explicitMatches⟩
  let (kind, selected) : Nat × Option Nat := match d with
    | .missing => (0, none)
    | .ambiguous => (1, none)
    | .limit => (2, none)
    | .selected n => (3, some n)
    | .explicitMismatch => (4, none)
  return ⟨r.id, kind, selected, published d, exitCode d⟩

def main (args : List String) : IO UInt32 := do
  let path ← match args with
    | [p] => pure p
    | _ => throw (IO.userError "Supply one discovery research packet.")
  let text ← IO.FS.readFile path
  let result := do
    let j ← Json.parse text
    let input ← fromJson? (α := Input) j
    if input.schema != 1 then throw "Unsupported discovery research schema."
    input.cases.mapM run
  match result with
  | .error message => (← IO.getStderr).putStrLn message; return 2
  | .ok rows => (← IO.getStdout).putStrLn ((toJson rows).compress); return 0
