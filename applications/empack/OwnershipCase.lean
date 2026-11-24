import Lean
import applications.empack.Ownership
open Lean ApplicationStudy.EmpackOwnership

private structure Row where
  previous : Nat
  incoming : Nat
  kind : Nat
  id : Nat
  readonly : Bool
  executable : Bool
  executableBits : Bool
  deriving FromJson

private structure Input where
  schema : Nat
  cases : List Row
  deriving FromJson

private def value (id : Nat) (readonly executable : Bool := false) : Content :=
  ⟨id, 1, readonly, executable⟩

private def decodeEntry (id code : Nat) : Except String (Option FileEntry) :=
  match code with
  | 0 => pure none
  | 1 => pure (some ⟨value id, .managed⟩)
  | 2 => pure (some ⟨value id, .seed⟩)
  | _ => throw "Unknown ownership policy code."

private def simulate (r : Row) : Except String String := do
  let previous ← decodeEntry 1 r.previous
  let incoming ← decodeEntry 2 r.incoming
  let current ← match r.kind with
    | 0 => pure Observation.absent
    | 1 => pure Observation.directory
    | 2 => pure (Observation.file (value r.id r.readonly r.executable))
    | _ => throw "Unknown observation kind."
  pure (label (plan previous current incoming r.executableBits))

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one file-ownership matrix JSON path."; return 2
  let text ← IO.FS.readFile path
  match Json.parse text >>= fromJson? (α := Input) with
  | .error error => IO.eprintln error; return 2
  | .ok input =>
    if input.schema != 1 then
      IO.eprintln "Unsupported ownership observation schema."
      return 2
    match input.cases.mapM simulate with
    | .error error => IO.eprintln error; return 2
    | .ok labels => IO.println (toJson labels).compress; return 0
