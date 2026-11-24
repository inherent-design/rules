import Lean
import applications.mo2.Overlay
import applications.prism.Update
open Lean ApplicationStudy

private structure OriginInput where
  id : Nat
  loose : Bool
  priority : Int
  archiveOrder : Int
  deriving FromJson

private structure Mo2Input where
  id : String
  candidates : List OriginInput
  deriving FromJson

private structure FileInput where
  path : String
  hash : String
  deriving FromJson, ToJson

private structure PrismInput where
  id : String
  old : List FileInput
  new : List FileInput
  deriving FromJson

private structure Input where
  schema : Nat
  mo2 : List Mo2Input
  prism : List PrismInput
  deriving FromJson

private structure Mo2Output where
  id : String
  winner : Option Nat
  deriving ToJson

private structure PrismOutput where
  id : String
  remainingNew : List FileInput
  remainingOld : List FileInput
  reparsed : Bool
  downloads : List FileInput
  simulatedFinal : List FileInput
  proposedFinal : List FileInput
  deriving ToJson

private structure Output where
  mo2 : List Mo2Output
  prism : List PrismOutput
  deriving ToJson

private def file (f : FileInput) : Prism.PackFile := ⟨f.path, f.hash⟩
private def dto (f : Prism.PackFile) : FileInput := ⟨f.path, f.hash⟩

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one launcher projection JSON path."; return 2
  let text ← IO.FS.readFile path
  match Json.parse text >>= fromJson? (α := Input) with
  | .error error => IO.eprintln error; return 2
  | .ok input =>
    if input.schema != 1 then
      IO.eprintln "Unsupported launcher projection schema."
      return 2
    let mo2 := input.mo2.map fun c =>
      let origins := c.candidates.map fun o =>
        let n := if o.loose then o.priority else o.archiveOrder
        Mo2.Origin.mk o.id o.loose (if n < 0 then none else some n.toNat)
      Mo2Output.mk c.id ((Mo2.winner origins).map Mo2.Origin.id)
    let prism := input.prism.map fun c =>
      let old := c.old.map file
      let new := c.new.map file
      let plan := Prism.filterPlan false new old
      let proposed := Prism.filterPlan true new old
      PrismOutput.mk c.id (plan.pendingNew.map dto) (plan.unmatchedOld.map dto)
        plan.pendingNew.isEmpty ((Prism.creationDownloads new plan).map dto)
        ((Prism.applyPlan old new plan).map dto) ((Prism.applyPlan old new proposed).map dto)
    IO.println (toJson (Output.mk mo2 prism)).compress
    return 0
