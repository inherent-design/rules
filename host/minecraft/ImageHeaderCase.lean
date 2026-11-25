import Lean
import host.minecraft.ImageHeader

open Lean Host.Minecraft.ImageHeader

private structure Row where
  id : Nat
  release : String
  limit : Nat
  position : Nat
  littleEndian : Bool
  readOnly : Bool
  magic : Option Bool
  length13 : Option Bool
  ihdr : Option Bool
  widthBits : Option Nat
  heightBits : Option Nat
  depth : Option Nat
  color : Option Nat
  deriving FromJson

private structure MathRow where
  id : Nat
  java : Nat
  widthBits : Nat
  heightBits : Nat
  deriving FromJson

private structure Request where
  schema : Nat
  contract : String
  rows : List Row
  arithmetic : List MathRow
  deriving FromJson

private structure Result where
  id : Nat
  error : Nat
  littleEndian : Bool
  position : Nat
  limit : Nat
  remaining : Nat
  readOnly : Bool
  bytesUnchanged : Bool
  deriving ToJson

private structure MathResult where
  id : Nat
  word : String
  narrowWord : String
  roundtrip : Bool
  checked : Bool
  deriving ToJson

private def known (label : String) (value : Option α) : Except String α :=
  match value with
  | some value => .ok value
  | none => .error ("Needed header fact unknown: " ++ label)

private def row (r : Row) : Except String Result := do
  if r.id > 255 || r.limit > 33 || r.position > r.limit then throw "Outside tiny-buffer profile."
  let generation ← match r.release with
    | "1.21.1" | "1.21.4" | "1.21.5" => pure 0
    | "1.21.11" => pure 1
    | "26.3" => pure 2
    | _ => throw "Unselected original client."
  let mut i : Input := ⟨generation, r.limit, false, false, false, 0, 0, 0, 0, r.position, r.littleEndian, r.readOnly⟩
  -- Parse only facts demanded by this bounded predicate; placeholders in dead
  -- slots are not observations of missing/invalid bytes.
  if !(generation == 1 && r.limit < 16) && !(generation == 2 && r.limit < 33) && r.limit >= 8 then
    i := { i with magic := ← known "magic" r.magic }
    if i.magic && r.limit >= 12 then
      i := { i with length13 := ← known "IHDR length" r.length13 }
      if i.length13 && r.limit >= 16 then
        i := { i with ihdr := ← known "IHDR type" r.ihdr }
        if i.ihdr && generation == 2 then
          let depth ← known "depth" r.depth
          if depth > 255 then throw "Unselected unsigned byte."
          i := { i with depth := depth }
          if [1, 2, 4, 8, 16].contains depth then
            let color ← known "color" r.color
            if color > 255 then throw "Unselected unsigned byte."
            i := { i with color := color }
            if [0, 2, 3, 4, 6].contains color && depth == 16 then
              let width ← known "width bits" r.widthBits
              let height ← known "height bits" r.heightBits
              if width >= 4294967296 || height >= 4294967296 then throw "Unselected int bits."
              i := { i with widthBits := width, heightBits := height }
  let output := run i
  return ⟨r.id, output.error, output.littleEndian, output.position, output.limit, output.remaining, output.readOnly, output.bytesUnchanged⟩

private def mathRow (r : MathRow) : Except String MathResult := do
  if r.id > 31 || ![17, 21, 25].contains r.java || r.widthBits == 0 || r.heightBits == 0 ||
      r.widthBits >= 2147483648 || r.heightBits >= 2147483648 then
    throw "Outside positive int/JDK17-21-25 arithmetic calibration."
  let word := Host.Java.Word64.estimate r.widthBits r.heightBits
  return ⟨r.id, toString word.toNat, toString (Host.Java.Word64.narrowed word).toNat,
    Host.Java.Word64.intRoundtrip word, Host.Java.Word64.checkedLong r.widthBits r.heightBits⟩

private def decode (json : Json) : Except String Json := do
  let r ← fromJson? (α := Request) json
  if r.schema != 1 || r.contract != "original-png-header-v1" || r.rows.length > 256 || r.arithmetic.length > 16 then
    throw "Unsupported research envelope."
  if (r.rows.map (·.id)).eraseDups.length != r.rows.length || (r.arithmetic.map (·.id)).eraseDups.length != r.arithmetic.length then
    throw "Repeated case identity."
  let headers ← r.rows.mapM row
  let arithmetic ← r.arithmetic.mapM mathRow
  return Json.mkObj [("rows", toJson headers), ("arithmetic", toJson arithmetic)]

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
      | .ok output => out.putStrLn output.compress
      | .error message => err.putStrLn message; return 2
    return 0
  catch error => err.putStrLn error.toString; return 2
