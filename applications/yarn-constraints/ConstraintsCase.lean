import Lean
import applications.«yarn-constraints».Constraints
open Lean ApplicationStudy.YarnConstraints
private structure Row where
  mode : Nat
  fix : Bool
  counter : Nat
  rootLicense : Nat
  childLicense : Nat
  object : Nat
  deriving FromJson
private structure Input where
  schema : Nat
  profile : String
  rows : List Row
  deriving FromJson
private def image (s : Image) : List Nat := [s.counter,s.rootLicense,s.childLicense,s.object]
private def evaluate (r : Row) : Except String Json := do
  if r.mode > 5 || r.counter > 12 || r.rootLicense > 2 || r.childLicense > 2 || r.object > 1 then throw "Research example bound."
  let s : Image := ⟨r.counter,r.rootLicense,r.childLicense,r.object⟩
  let result := current r.mode r.fix s
  let rendered := String.intercalate "/" ((image result.image ++ [result.exitCode,result.evaluations]).map toString)
  pure (Json.mkObj [("current",toJson rendered),("inputs",toJson ((inputs r.mode r.fix (if r.fix then 10 else 1) s).map image)),
    ("proposal",toJson (proposedStatus r.mode result)),("humanGuidance",toJson (humanGuidance r.mode r.fix s))])
def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one constraints research input."; return 2
  match Json.parse (← IO.FS.readFile path) >>= fromJson? (α := Input) with
  | .error e => IO.eprintln e; return 2
  | .ok input =>
    if input.schema != 1 || input.profile != "owned-modern-js-rules" || input.rows.length > 128 then
      IO.eprintln "Unsupported constraints research profile."; return 2
    match input.rows.mapM evaluate with
    | .error e => IO.eprintln e; return 2
    | .ok results => IO.println (toJson results).compress; return 0
