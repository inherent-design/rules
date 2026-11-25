import Lean
import applications.«pnpm-deploy».Deploy
open Lean ApplicationStudy.PnpmDeploy

private structure RootRow where
  target : Nat
  group : Nat
  deriving FromJson
private structure ArcRow where
  owner : Nat
  target : Nat
  deriving FromJson
private structure Row where
  id : String
  selected : Nat
  unsafeTarget : Bool
  force : Bool
  inside : Bool
  unsafeLink : Bool
  occupied : Bool
  aliasesSource : Bool
  installAvailable : Option Bool
  production : Bool
  optional : Bool
  deriving FromJson
private structure Input where
  schema : Nat
  nodes : Nat
  roots : List RootRow
  edges : List ArcRow
  rows : List Row
  deriving FromJson
private structure OutputRow where
  id : String
  code : Nat
  payloadCopied : Bool
  priorRemoved : Bool
  commandSucceeded : Bool
  sourcePreserved : Bool
  direct : List Nat
  closure : List Nat
  deriving ToJson

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one deploy study JSON path."; return 2
  let text ← IO.FS.readFile path
  match Json.parse text >>= fromJson? (α := Input) with
  | .error error => IO.eprintln error; return 2
  | .ok input =>
    if input.schema != 1 then IO.eprintln "Unsupported deploy study schema."; return 2
    if input.nodes == 0 || input.nodes > 64 then IO.eprintln "Unsupported deploy node universe."; return 2
    if input.roots.any (fun edge => edge.target ≥ input.nodes || edge.group > 2) ||
        input.edges.any (fun edge => edge.owner ≥ input.nodes || edge.target ≥ input.nodes) then
      IO.eprintln "Deploy graph refers outside the admitted universe or groups."; return 2
    if (input.roots.map (·.target)).length != (input.roots.map (·.target)).eraseDups.length then
      IO.eprintln "Duplicate root target is outside this deploy profile."; return 2
    let dependencies := input.roots.map fun edge => RootDependency.mk edge.target edge.group
    let edges := input.edges.map fun edge => Arc.mk edge.owner edge.target
    let results : Except String (List OutputRow) := input.rows.mapM fun row => do
      let admission := admit row.selected row.unsafeTarget row.force row.inside row.unsafeLink row.occupied
      let some outcome := finish admission row.force row.occupied row.aliasesSource row.installAvailable
        | throw "Needed deployment installation evidence is unknown."
      let usable := outcome.commandSucceeded && outcome.payloadCopied
      let roots := if usable then direct input.nodes dependencies row.production row.optional else []
      let reached := if usable then closure input.nodes dependencies edges row.production row.optional else []
      return OutputRow.mk row.id outcome.code outcome.payloadCopied outcome.priorRemoved outcome.commandSucceeded outcome.sourcePreserved roots reached
    match results with
    | .error error => IO.eprintln error; return 2
    | .ok rows => IO.println (toJson rows).compress; return 0
