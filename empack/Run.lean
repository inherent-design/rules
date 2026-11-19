import empack.Model
import Lean
open Lean Empack
deriving instance FromJson for Probe
def main (args : List String) : IO Unit := do
  let line ← (← IO.getStdin).getLine
  let p : Probe ← IO.ofExcept (Json.parse line >>= fromJson?)
  let i ← match args with
    | ["always"] => pure Intent.always
    | ["never"] => pure Intent.never
    | ["auto"] => pure Intent.auto
    | _ => throw (IO.userError "Expected never, auto, or always")
  let t := detect i (observe p)
  IO.println (Json.mkObj [("tty",toJson t.tty),("unicode",toJson t.unicode),
    ("columns",toJson t.columns),("color",toJson (reprStr t.color))]).compress
