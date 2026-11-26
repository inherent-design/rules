import Lean
import host.java.CpuImage

open Lean Host.Java.CpuImage

private structure Row where
  id : Nat
  operation : Nat
  x : Option Nat
  y : Option Nat
  word : Option Nat
  deriving FromJson, Inhabited

private structure Request where
  schema : Nat
  contract : String
  profile : String
  rows : List Row
  deriving FromJson

private structure Result where
  id : Nat
  error : Nat
  word : Option Nat
  pixels : Option (List Nat)
  width : Nat
  height : Nat
  deriving ToJson

private def known (name : String) (value : Option α) : Except String α :=
  match value with
  | some value => .ok value
  | none => .error ("Needed image input is unknown: " ++ name)

private def decode (json : Json) : Except String Json := do
  let r ← fromJson? (α := Request) json
  if r.schema != 1 || r.contract != "original-cpu-image-v1" ||
      r.profile != "mc1.21.1-java21-macos-arm64-lwjgl333-system" || r.rows.isEmpty || r.rows.length > 64 then
    throw "Outside selected original CPU image profile."
  if (r.rows.map (·.id)).eraseDups.length != r.rows.length then throw "Repeated step identity."
  let mut state := initial
  let mut results : List Result := []
  for i in [:r.rows.length] do
    let row := r.rows[i]!
    if row.id > 127 || row.operation > 4 || ((i == 0) != (row.operation == 0)) then
      throw "Expected one initial construction and selected operations."
    let mut x := 0
    let mut y := 0
    let mut word := 0
    if row.operation == 1 || row.operation == 2 then
      x := ← known "x" row.x
      y := ← known "y" row.y
      if x > 3 || y > 3 then throw "Outside encoded coordinates -1..2."
      if row.operation == 2 then
        word := ← known "word" row.word
        if word >= 4294967296 then throw "Outside opaque32bit word."
    let (next, reply) := step state row.operation x y (UInt32.ofNat word)
    state := next
    results := results ++ [⟨row.id, reply.error, reply.word.map UInt32.toNat,
      (visibleWords state).map (List.map UInt32.toNat), (metadata state).1, (metadata state).2⟩]
  return toJson results

def main (args : List String) : IO UInt32 := do
  let out ← IO.getStdout
  let err ← IO.getStderr
  let (batch, path) ← match args with
    | [path] => pure (false, path)
    | ["--batch", path] => pure (true, path)
    | _ => err.putStrLn "Expected packet path or --batch packet-array path."; return 2
  try
    let json ← match Json.parse (← IO.FS.readFile path) with
      | .ok value => pure value
      | .error message => err.putStrLn message; return 2
    if batch then
      let packets ← match fromJson? (α := List Json) json with
        | .ok value => pure value
        | .error message => err.putStrLn message; return 2
      if packets.length > 64 then err.putStrLn "Too many packets."; return 2
      out.putStrLn (toJson (packets.map (fun p => match decode p with | .ok _ => (0 : Nat) | .error _ => 2))).compress
    else
      match decode json with
      | .ok value => out.putStrLn value.compress
      | .error message => err.putStrLn message; return 2
    return 0
  catch error => err.putStrLn error.toString; return 2
