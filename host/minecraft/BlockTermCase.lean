import Lean
import host.minecraft.BlockTerm

open Lean Host.Minecraft.BlockTerm

private structure Row where
  id : Nat
  release : String
  operation : Nat
  value : List Nat
  negated : Option Bool
  deriving FromJson

private structure Request where
  schema : Nat
  contract : String
  rows : List Row
  deriving FromJson

private structure Result where
  id : Nat
  error : Nat
  value : List Nat
  negated : Bool
  encoded : List Nat
  reparseAttempted : Bool
  reparseError : Nat
  reparsedValue : List Nat
  reparsedNegated : Bool
  equalAfterReparse : Bool
  deriving ToJson

private def scalar (n : Nat) : Bool := n ≤ 1114111 && !(55296 ≤ n && n ≤ 57343)
private def utf16Units (ns : List Nat) : Nat :=
  ns.foldl (fun count n => count + if n < 65536 then 1 else 2) 0

private def row (r : Row) : Except String Result := do
  if r.id > 127 || !["1.21.5", "1.21.11", "26.3"].contains r.release || r.operation > 1 then
    throw "Unselected literal record profile or operation."
  if !r.value.all scalar || utf16Units r.value > 32 then throw "Outside short well-formed Unicode scalar profile."
  let value := r.value.map UInt32.ofNat
  let first ← if r.operation == 0 then pure (parse value) else
    match r.negated with
    | some flag => pure (construct value flag)
    | none => throw "Needed constructor flag is unknown."
  match first with
  | none => return ⟨r.id, 1, [], false, [], false, 0, [], false, false⟩
  | some term =>
    let encoded := encode term
    match parse encoded with
    | none => return ⟨r.id, 0, term.value.map UInt32.toNat, term.negated, encoded.map UInt32.toNat, true, 1, [], false, false⟩
    | some next => return ⟨r.id, 0, term.value.map UInt32.toNat, term.negated, encoded.map UInt32.toNat, true, 0,
        next.value.map UInt32.toNat, next.negated, term == next⟩

private def decode (json : Json) : Except String Json := do
  let r ← fromJson? (α := Request) json
  if r.schema != 1 || r.contract != "original-blockstate-term-v1" || r.rows.length > 128 then throw "Unsupported research envelope."
  if (r.rows.map (·.id)).eraseDups.length != r.rows.length then throw "Repeated case identity."
  return toJson (← r.rows.mapM row)

def main (args : List String) : IO UInt32 := do
  let err ← IO.getStderr
  let out ← IO.getStdout
  let (batch, path) ← match args with
    | [path] => pure (false, path)
    | ["--batch", path] => pure (true, path)
    | _ => err.putStrLn "Expected packet path or --batch packet-array path."; return 2
  try
    let input ← match Json.parse (← IO.FS.readFile path) with
      | .ok json => pure json
      | .error message => err.putStrLn message; return 2
    if batch then
      let packets ← match fromJson? (α := List Json) input with
        | .ok packets => pure packets
        | .error message => err.putStrLn message; return 2
      if packets.length > 64 then err.putStrLn "Too many packets."; return 2
      out.putStrLn (toJson (packets.map (fun p => match decode p with | .ok _ => (0 : Nat) | .error _ => 2))).compress
    else
      match decode input with
      | .ok result => out.putStrLn result.compress
      | .error message => err.putStrLn message; return 2
    return 0
  catch error => err.putStrLn error.toString; return 2
