import Lean
import applications.mo2.Overwrite
open Lean ApplicationStudy.Mo2Overwrite
private structure Row where
  metadata : Bool
  known : Bool
  primary : Int
  alternatives : List Int
  choice : Option Int
  source : Option Nat
  destination : Option Nat
  removeOk : Bool
  moveOk : Bool
  deriving FromJson
private structure Input where
  schema : Nat
  cases : List Row
  deriving FromJson
private def maybe (v : Option Nat) : String := toString (v.getD 0)
private def failure : Failure → String
  | .none => "none" | .remove => "remove" | .move => "move"
private def label (x : Option Int) : String := x.map toString |>.getD "absent"
private def evaluate (r : Row) : Except String String := do
  if r.primary < 0 || r.primary > 2 || r.alternatives.any (fun x => x < 0 || x > 2) then
    throw "Unknown origin witness."
  if [r.source,r.destination].any (fun n => n.any (fun n => n == 0 || n > 5)) then
    throw "Unknown backing witness."
  let values := options r.metadata r.known r.primary r.alternatives
  if let some choice := r.choice then
    if !(values.any (·.contains choice)) then throw "Choice is not offered by this widget."
  let chosen := selected values r.choice
  if r.removeOk && (chosen.isNone || chosen == some (-1) || r.destination.isNone) then
    throw "Successful remove needs an admitted existing destination."
  if r.moveOk && (!r.removeOk || r.source.isNone) then throw "Move witness lacks removed target or source."
  let before : Files := ⟨r.source,r.destination⟩
  let out := applyCurrent before chosen r.removeOk r.moveOk
  pure (String.intercalate "/" [label (defaultChoice values),label chosen,maybe out.files.source,
    maybe out.files.destination,failure out.failure,maybe (withRetainedPrior before chosen r.removeOk r.moveOk).retainedPrior])
def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one overwrite model input."; return 2
  let text ← IO.FS.readFile path
  match Json.parse text >>= fromJson? (α := Input) with
  | .error error => IO.eprintln error; return 2
  | .ok input =>
    if input.schema != 1 then IO.eprintln "Unsupported overwrite research schema."; return 2
    match input.cases.mapM evaluate with
    | .error error => IO.eprintln error; return 2
    | .ok values => IO.println (toJson values).compress; return 0
