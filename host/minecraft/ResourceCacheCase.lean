import Lean
import host.minecraft.ResourceCache

open Lean Host.Minecraft.ResourceCache

private structure RawAction where
  op : Nat
  identity : Nat
  kind : Nat
  event : Nat
  projection : Nat
  value : Nat
  failures : Nat
  deriving FromJson

private structure Row where
  id : Nat
  capacity : Int
  actions : Option (List RawAction)
  deriving FromJson

private structure Request where
  schema : Nat
  contract : String
  artifact : String
  identityProfile : String
  callbackProfile : String
  rows : List Row
  deriving FromJson

private structure ObservedStep where
  error : Nat
  value : Option Nat
  size : Nat
  events : List Nat
  deriving ToJson

private structure Observed where
  id : Nat
  constructorError : Nat
  steps : List ObservedStep
  deriving ToJson

private def action (state : State) (raw : RawAction) : Except String Step := do
  if raw.identity > 3 || raw.kind > 4 || raw.event > 128 || raw.projection > 2 || raw.value > 64 || raw.failures > 1 then
    throw "Outside the selected identities/kinds/callback markers."
  match raw.op with
  | 0 =>
    if raw.failures != 0 || raw.event == 0 then throw "Project needs a declared event and no clear-failure state."
    let outcome ← match raw.projection with
      | 0 => if raw.value == 0 then pure (.returned .absent) else throw "Absent projection cannot carry a text identity."
      | 1 => if raw.value > 0 then pure (.returned (.text raw.value)) else throw "Text needs a nonzero role identity."
      | _ => if raw.value == 0 then pure .failed else throw "Failed projection cannot carry a result."
    return project state raw.identity raw.kind raw.event outcome
  | 1 =>
    if raw.identity != 0 || raw.kind != 0 || raw.projection != 0 || raw.value != 0 || raw.event == 0 then
      throw "Clear registration has only its marker and authored failure state."
    return onClear state ⟨raw.event, raw.failures⟩
  | 2 =>
    if raw.identity != 0 || raw.kind != 0 || raw.projection != 0 || raw.value != 0 || raw.event != 0 || raw.failures != 0 then
      throw "Clear has no synthetic projection or registration evidence."
    return clear state
  | _ => throw "Unselected operation."

private def row (raw : Row) : Except String Observed := do
  if raw.id > 64 || raw.capacity < -8 || raw.capacity > 1024 then throw "Outside selected case/capacity bounds."
  match create raw.capacity with
  | none => return ⟨raw.id, 1, []⟩
  | some initial =>
    let actions ← match raw.actions with
      | some actions => pure actions
      | none => throw "Actions are unknown for an admitted cache."
    if actions.length > 64 then throw "Outside selected trace length."
    let mut state := initial
    let mut steps := []
    for rawAction in actions do
      let result ← action state rawAction
      state := result.state
      if state.entries.length > state.capacity then throw "Research state violated its capacity premise."
      let value := result.value.map fun v => match v with
        | .absent => 0
        | .text identity => identity
      steps := steps ++ [⟨result.error, value, state.entries.length, state.events⟩]
    return ⟨raw.id, 0, steps⟩

private def decode (input : Json) : Except String Json := do
  let request ← fromJson? (α := Request) input
  if request.schema != 1 || request.contract != "isolated-resource-cache-v1" ||
      request.artifact != "4ae402eaa858eef4141858554a3f9f0867f6e2ddc72e68313668187a3058e5d5" ||
      request.identityProfile != "case-local-equal-distinct-strings-v1" ||
      request.callbackProfile != "authored-nonreentrant-v1" || request.rows.length > 32 then
    throw "Unselected source/schema/identity/callback profile."
  if (request.rows.map (·.id)).eraseDups.length != request.rows.length then throw "Repeated case identity."
  return toJson (← request.rows.mapM row)

def main (args : List String) : IO UInt32 := do
  let out ← IO.getStdout
  let err ← IO.getStderr
  let (batch, path) ← match args with
    | [path] => pure (false, path)
    | ["--batch", path] => pure (true, path)
    | _ => err.putStrLn "Expected a request path or --batch packet-array path."; return 2
  try
    match Json.parse (← IO.FS.readFile path) with
    | .error message => err.putStrLn message; return 2
    | .ok input =>
      if batch then
        match fromJson? (α := List Json) input with
        | .error message => err.putStrLn message; return 2
        | .ok packets =>
          if packets.length > 64 then err.putStrLn "Outside the research packet-array bound."; return 2
          let statuses := packets.map (fun packet => match decode packet with | .ok _ => (0 : Nat) | .error _ => 2)
          out.putStrLn (toJson statuses).compress; return 0
      else
        match decode input with
        | .ok value => out.putStrLn value.compress; return 0
        | .error message => err.putStrLn message; return 2
  catch failure => err.putStrLn failure.toString; return 2
