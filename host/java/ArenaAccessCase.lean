import Lean
import host.java.ArenaAccess
open Lean Host.Java25.ArenaAccess

private structure Row where
  alive : Bool
  historicalValue : Nat
  shared : Bool
  owner : Bool
  operation : String
  deriving FromJson
private structure Input where
  schema : Nat
  cases : List Row
  deriving FromJson

private def evaluate (r : Row) : Except String String := do
  let op ← match r.operation with
    | "read" => pure Operation.read | "write" => pure Operation.write | "close" => pure Operation.close
    | _ => throw "Unsupported arena operation."
  let s : State := ⟨r.alive,r.historicalValue⟩
  let c : Context := ⟨r.shared,r.owner⟩
  let next := after s c op
  let value := (returnedValue s c op).map toString |>.getD "none"
  pure s!"{if allowed s c then 1 else 0}/{if next.alive then 1 else 0}/{value}/{refusalReasons s c}"

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one arena input path."; return 2
  let text ← IO.FS.readFile path
  match Json.parse text >>= fromJson? (α := Input) with
  | .error error => IO.eprintln error; return 2
  | .ok input =>
    if input.schema != 1 then IO.eprintln "Unsupported schema."; return 2
    match input.cases.mapM evaluate with
    | .error error => IO.eprintln error; return 2
    | .ok values => IO.println (toJson values).compress; return 0
