import Lean
import host.minecraft.LinkedFilesystem
open Lean Host.Minecraft.LinkedFilesystem
private structure Row where
  kind : Nat
  sameFilesystem : Option Bool
  sameNode : Option Bool
  absolute : Option Bool
  registered : Option Bool
  mapped : Option Bool
  backing : Option Nat
  deriving FromJson
private structure Request where
  schema : Nat
  contract : String
  rows : List Row
  deriving FromJson
private def needed {α : Type} (value : Option α) : Except String α :=
  match value with
  | some x => .ok x
  | none => .error "Needed linked-filesystem evidence is unknown."
private def admit (r : Row) : Except String Nat := do
  if r.kind > 5 then throw "Unselected linked-filesystem operation."
  if r.kind == 1 then
    let sameFilesystem ← needed r.sameFilesystem
    if !sameFilesystem then return evaluate r.kind false false false false false 0
    pure (evaluate r.kind sameFilesystem (← needed r.sameNode) false false false 0)
  else if r.kind == 2 then
    let absolute ← needed r.absolute
    if !absolute then return evaluate r.kind false false false false false 0
    pure (evaluate r.kind false false absolute (← needed r.registered) false 0)
  else if r.kind == 3 then
    let mapped ← needed r.mapped
    if !mapped then return evaluate r.kind false false false false false 0
    let backing ← needed r.backing
    if backing > 2 then throw "Outside selected backing-byte states."
    pure (evaluate r.kind false false false false mapped backing)
  else if r.kind == 4 then
    pure (evaluate r.kind false false false (← needed r.registered) false 0)
  else pure (evaluate r.kind false false false false false 0)
def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one linked-filesystem request.";return 2
  let raw ← IO.FS.readFile path
  match Json.parse raw >>= fromJson? (α := Request) with
  | .error e => IO.eprintln e;return 2
  | .ok r =>
    if r.schema != 1 || r.contract != "canonical-linkfs-owned-bytes-v1" || r.rows.length > 128 then
      IO.eprintln "Unselected linked-filesystem schema,contract or batch.";return 2
    match r.rows.mapM admit with
    | .error e => IO.eprintln e;return 2
    | .ok values => IO.println (toJson values).compress;return 0
