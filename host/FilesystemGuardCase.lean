import Lean
import common.FilesystemGuard
open Lean Host.FilesystemGuard
private structure Row where
  policyAllows : Bool
  relation : Nat
  complete : Bool
  identityCurrent : Bool
  scopeMatches : Bool
  authority : Bool
  boundaryBound : Bool
  deriving FromJson
private structure Request where
  schema : Nat
  contract : String
  rows : List Row
  deriving FromJson
def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one filesystem-guard request.";return 2
  let raw ← IO.FS.readFile path
  match Json.parse raw >>= fromJson? (α := Request) with
  | .error e => IO.eprintln e;return 2
  | .ok r =>
    if r.schema != 1 || r.contract != "protected-tree-preflight-v1" || r.rows.length > 256 || r.rows.any (·.relation > 2) then
      IO.eprintln "Unselected filesystem guard schema,relation or batch.";return 2
    let result := r.rows.map fun x =>
      let e : Evidence := ⟨x.policyAllows,x.relation,x.complete,x.identityCurrent,x.scopeMatches,x.authority,x.boundaryBound⟩
      (preflight e,(mayMutate e).toNat)
    IO.println (toJson result).compress;return 0
