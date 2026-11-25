import Lean
import host.java.Word32
open Lean Host.Java.Word32
private structure Row where
  a : Nat
  b : Nat
  deriving FromJson
private structure Request where
  schema : Nat
  rows : List Row
  deriving FromJson
def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one32bit arithmetic request.";return 2
  let raw ← IO.FS.readFile path
  match Json.parse raw >>= fromJson? (α := Request) with
  | .error e => IO.eprintln e;return 2
  | .ok r =>
    if r.schema != 1 || r.rows.length > 64 || r.rows.any (fun x => x.a > 4294967295 || x.b > 4294967295) then
      IO.eprintln "Unselected schema,size or word.";return 2
    let result := r.rows.map (fun x =>
      let sum := UInt32.ofNat x.a+UInt32.ofNat x.b
      let difference := UInt32.ofNat x.a-UInt32.ofNat x.b
      [sum.toNat,difference.toNat,(negative sum).toNat,(positive sum).toNat])
    IO.println (toJson result).compress;return 0
