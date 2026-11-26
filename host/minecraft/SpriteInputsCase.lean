import Lean
import host.minecraft.SpriteInputs

open Lean Host.Minecraft.SpriteInputs

private structure Row where
  id : Nat
  width : Nat
  height : Nat
  masks : Option (List Nat)
  aliasLifecycle : Bool
  deriving FromJson

private structure Packet where
  schema : Nat
  contract : String
  release : String
  nameContext : String
  metadataContext : String
  rows : List Row
  deriving FromJson

private structure Frame where
  frame : Nat
  transparent : List Bool
  deriving ToJson

private structure Alias where
  beforeMutation : Bool
  afterMutation : Bool
  inputError : Nat
  spriteError : Nat
  widthAfterClose : Nat
  heightAfterClose : Nat
  framesAfterClose : List Nat
  deriving ToJson

private structure Result where
  id : Nat
  width : Nat
  height : Nat
  uniqueFrames : List Nat
  matrices : List Frame
  aliasState : Option Alias
  deriving ToJson

private def decode (json : Json) : Except String Json := do
  let p ← fromJson? (α := Packet) json
  if p.schema != 1 || p.contract != "constructed-sprite-inputs-v1" || p.release != "1.21.1" ||
      p.nameContext != "null" || p.metadataContext != "empty" || p.rows.length > 32 then
    throw "Unselected constructed sprite profile."
  if (p.rows.map (·.id)).eraseDups.length != p.rows.length then throw "Repeated scenario identity."
  let mut results : List Result := []
  for row in p.rows do
    let masks ← match row.masks with
      | some masks => pure masks
      | none => throw "Needed backing masks are unknown."
    if row.id > 63 || ![2, 3].contains row.width || row.height != 2 ||
        ![1, 2].contains masks.length || row.width * row.height * masks.length > 8 ||
        masks.any (· ≥ 2 ^ (row.width * row.height)) then
      throw "Outside selected initialized tiny masks."
    if row.aliasLifecycle && (row.width != 2 || masks != [0]) then throw "Unselected alias lifecycle context."
    let aliasState := if row.aliasLifecycle then some (Alias.mk
      (aliasFirstTransparent aliasBacking) (aliasFirstTransparent aliasMutated)
      aliasClosedAccess aliasClosedAccess (Host.Java.CpuImage.metadata aliasClosed).1
      (Host.Java.CpuImage.metadata aliasClosed).2 (frameIds masks)) else none
    results := results ++ [⟨row.id, row.width, row.height, frameIds masks,
      (matrices row.width row.height masks).map (fun m => ⟨m.frame, m.cells⟩), aliasState⟩]
  return toJson results

def main (args : List String) : IO UInt32 := do
  let err ← IO.getStderr
  let out ← IO.getStdout
  let (batch, path) ← match args with
    | [path] => pure (false, path)
    | ["--batch", path] => pure (true, path)
    | _ => err.putStrLn "Expected packet path or --batch packet-array path."; return 2
  try
    let input ← match Json.parse (← IO.FS.readFile path) with
      | .ok value => pure value
      | .error message => err.putStrLn message; return 2
    if batch then
      let packets ← match fromJson? (α := List Json) input with
        | .ok value => pure value
        | .error message => err.putStrLn message; return 2
      if packets.length > 64 then err.putStrLn "Too many packets."; return 2
      out.putStrLn (toJson (packets.map (fun j => match decode j with | .ok _ => (0 : Nat) | .error _ => 2))).compress
    else
      match decode input with
      | .ok value => out.putStrLn value.compress
      | .error message => err.putStrLn message; return 2
    return 0
  catch error => err.putStrLn error.toString; return 2
