import Lean
import applications.«js-dedupe».Dedupe
open Lean ApplicationStudy.Dedupe
private structure Row where
  npmStyle : Bool
  check : Bool
  left : Nat
  right : Nat
  copies : Nat
  targetLeft : Nat
  targetRight : Nat
  targetCopies : Nat
  allowedLeft : List Nat
  allowedRight : List Nat
  deriving FromJson
private structure Input where
  schema : Nat
  rows : List Row
  deriving FromJson
private def canonical (xs : List Nat) : Bool :=
  xs == xs.mergeSort (· ≤ ·) && xs.eraseDups.length == xs.length && !xs.isEmpty && xs.all (fun n => 0 < n && n < 4)
private def evaluate (r : Row) : Except String String := do
  if !canonical r.allowedLeft || !canonical r.allowedRight ||
      [r.left,r.right,r.targetLeft,r.targetRight].any (fun n => n == 0 || n > 3) ||
      [r.copies,r.targetCopies].any (fun n => n == 0 || n > 2) then
    throw "Unsupported research labels or noncanonical allowed set."
  let p : Plan := ⟨⟨r.left,r.right,r.copies⟩,⟨r.targetLeft,r.targetRight,r.targetCopies⟩,r.allowedLeft,r.allowedRight⟩
  let o := run r.npmStyle r.check p
  pure (String.intercalate "/" [toString o.selected.left,toString o.selected.right,toString o.selected.copies,
    toString o.status,toString o.selectionChanged,toString o.placementChanged,toString o.manifestChanged])
def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one research input."; return 2
  match Json.parse (← IO.FS.readFile path) >>= fromJson? (α := Input) with
  | .error e => IO.eprintln e; return 2
  | .ok input =>
    if input.schema != 1 || input.rows.length > 128 then
      IO.eprintln "Unsupported research schema/count."; return 2
    match input.rows.mapM evaluate with
    | .error e => IO.eprintln e; return 2
    | .ok rows => IO.println (toJson rows).compress; return 0
