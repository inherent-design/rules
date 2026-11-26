import Lean
import host.java.TimerPolicy

open Lean Host.Java.TimerPolicy

private structure Row where
  id : Nat
  operation : Nat
  timer : Option Nat
  task : Option Nat
  validArguments : Option Bool
  deriving FromJson

private structure Packet where
  schema : Nat
  contract : String
  java : Nat
  rows : List Row
  deriving FromJson

private structure Result where
  id : Nat
  error : Nat
  value : Option Bool
  deriving ToJson

private def known (name : String) (value : Option α) : Except String α :=
  match value with
  | some value => .ok value
  | none => .error ("Needed timer input unknown: " ++ name)

private def decode (json : Json) : Except String Json := do
  let p ← fromJson? (α := Packet) json
  if p.schema != 1 || p.contract != "jdk-timer-admission-v1" || ![17, 21, 25].contains p.java || p.rows.length > 64 then
    throw "Unselected authored timer profile."
  if (p.rows.map (·.id)).eraseDups.length != p.rows.length then throw "Repeated step identity."
  let mut state := initial
  let mut results : List Result := []
  for row in p.rows do
    if row.id > 127 || row.operation > 2 then throw "Unknown timer operation."
    let mut timer := 0
    let mut task := 0
    let mut valid := true
    if row.operation != 1 then
      timer := ← known "timer" row.timer
      if timer > 1 then throw "Outside owned two-timer pool."
    if row.operation != 2 then
      task := ← known "task" row.task
      if task > 5 then throw "Outside owned six-task pool."
    if row.operation == 0 then valid := ← known "valid arguments" row.validArguments
    let (next, reply) := step state row.operation timer task valid
    state := next
    results := results ++ [⟨row.id, reply.error, reply.value⟩]
  return toJson results

def main (args : List String) : IO UInt32 := do
  let err ← IO.getStderr
  let out ← IO.getStdout
  let (batch, path) ← match args with
    | [path] => pure (false, path)
    | ["--batch", path] => pure (true, path)
    | _ => err.putStrLn "Expected packet path or --batch packet-array path."; return 2
  try
    let input ← match Json.parse (← IO.FS.readFile path) with
      | .ok value => pure value
      | .error message => err.putStrLn message; return 2
    if batch then
      let packets ← match fromJson? (α := List Json) input with
        | .ok value => pure value
        | .error message => err.putStrLn message; return 2
      if packets.length > 64 then err.putStrLn "Too many packets."; return 2
      out.putStrLn (toJson (packets.map (fun j => match decode j with | .ok _ => (0 : Nat) | .error _ => 2))).compress
    else
      match decode input with
      | .ok value => out.putStrLn value.compress
      | .error message => err.putStrLn message; return 2
    return 0
  catch error => err.putStrLn error.toString; return 2
