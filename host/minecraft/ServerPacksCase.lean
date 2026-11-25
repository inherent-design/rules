import Lean
import host.minecraft.ServerPacks
open Lean Host.Minecraft.ServerPacks
private structure Request where
  schema : Nat
  contract : String
  rows : List (List Nat)
  deriving FromJson
private def selected (row : List Nat) : Bool :=
  match row with
  | [op,presentPrompt,present,accepted,download,activation,reason,load] =>
    op ≤ 12 && presentPrompt ≤ 2 && present ≤ 1 && accepted ≤ 1 && download ≤ 2 && activation ≤ 2 && reason ≤ 5 && load ≤ 1
  | _ => false
private def evaluate (row : List Nat) : List Nat :=
  match row with
  | [op,prompt,present,accepted,download,activation,reason,load] => decideBranch op prompt present accepted download activation reason load
  | _ => []
def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one selected manager-branch request."; return 2
  let raw ← IO.FS.readFile path
  match Json.parse raw >>= fromJson? (α := Request) with
  | .error e => IO.eprintln e; return 2
  | .ok r =>
    if r.schema != 1 || r.contract != "java-server-pack-single-record-branches" || r.rows.length > 512 || !(r.rows.all selected) then
      IO.eprintln "Unselected schema,contract,branch or value."; return 2
    IO.println (toJson (r.rows.map evaluate)).compress; return 0
