import Lean
import applications.restic.Restore
open Lean ApplicationStudy.ResticRestore

private structure Row where
  policy : String
  existing : String
  time : String
  sameSize : Bool
  selected : Bool
  dry : Bool
  verify : Bool
  valid : Bool
  extras : Bool
  delete : Bool
  filter : String
  deriving FromJson

private structure Input where
  schema : Nat
  cases : List Row
  deriving FromJson

private def evaluate (r : Row) : Except String String := do
  let p ← match r.policy with
    | "always" => pure Policy.always | "if-changed" => pure Policy.ifChanged
    | "if-newer" => pure Policy.ifNewer | "never" => pure Policy.never
    | _ => throw "Unsupported overwrite policy."
  let existing ← match r.existing with
    | "missing" => pure Existing.missing | "correct" => pure Existing.correct
    | "different" => pure Existing.different | "symlink" => pure Existing.symlink
    | _ => throw "Unsupported target node."
  let time ← match r.time with
    | "older" => pure TimeOrder.older | "equal" => pure TimeOrder.equal | "newer" => pure TimeOrder.newer
    | _ => throw "Unknown target time ordering."
  let f ← match r.filter with
    | "all" => pure Filter.all | "exclude-root" => pure Filter.excludeRootFile
    | "exclude-child" => pure Filter.excludeChild | "exclude-directory" => pure Filter.excludeDirectory
    | "include-alpha" => pure Filter.includeAlpha | _ => throw "Unsupported fixed filter."
  if existing == .missing && r.sameSize then throw "Missing node has no size observation."
  if existing == .symlink && r.sameSize then throw "Symlink size is not a regular payload witness."
  if r.dry && r.verify && r.valid then throw "Dry/verify combination must be an invalid command."
  let request : FileRequest := ⟨p, existing, time, r.sameSize, r.selected, r.dry, r.verify, r.valid⟩
  let extra := deleteCurrent r.delete r.dry r.valid f (if r.extras then fullExtras else ⟨false, false, false, false⟩)
  let result := after request
  let content := if result == .correct then "correct" else if result == .different then "different"
    else if result == .missing then "missing" else "symlink"
  pure (String.intercalate "/" [content, if extra.rootFile then "1" else "0",
    if extra.directory then "1" else "0", if extra.protectedChild then "1" else "0",
    if extra.otherChild then "1" else "0", if r.valid then "0" else "1"])

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one restore input JSON path."; return 2
  let text ← IO.FS.readFile path
  match Json.parse text >>= fromJson? (α := Input) with
  | .error error => IO.eprintln error; return 2
  | .ok input =>
    if input.schema != 1 then IO.eprintln "Unsupported restore schema."; return 2
    match input.cases.mapM evaluate with
    | .error error => IO.eprintln error; return 2
    | .ok values => IO.println (toJson values).compress; return 0
