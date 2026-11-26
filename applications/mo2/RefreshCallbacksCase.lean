import Lean
import applications.mo2.RefreshCallbacks
open Lean ApplicationStudy.Mo2RefreshCallbacks

private structure ChildInput where
  token : Nat
  group : Nat
  force : Bool
  deriving FromJson
private structure Row where
  token : Nat
  group : Nat
  force : Bool
  child : Option ChildInput
  deriving FromJson
private structure Scenario where
  active : Bool
  detached : Bool
  requests : List Row
  deriving FromJson
private structure Input where
  schema : Nat
  profile : String
  singleThreaded : Bool
  callbacksDoNotThrowOrCancel : Bool
  scenarios : List Scenario
  deriving FromJson

private def snapshot (state : State) : Json :=
  Json.mkObj [("trace",toJson state.trace),
    ("connected",toJson ((state.pending.map (·.token)).mergeSort (· ≤ ·))),
    ("pending",toJson state.pending.length)]

private def evaluate (scenario : Scenario) : Except String Json := do
  if scenario.requests.length > 8 then throw "Too many selected callback requests."
  let mut tokens : List Nat := []
  let mut requests : List Request := []
  for row in scenario.requests do
    if row.token == 0 || row.token > 9 || row.group > 2 then throw "Unsupported callback value."
    tokens := tokens ++ [row.token]
    let child ← match row.child with
      | none => pure none
      | some child => do
        if child.token == 0 || child.token > 9 || child.group > 2 then
          throw "Unsupported leaf callback value."
        tokens := tokens ++ [child.token]
        pure (some (Child.mk child.token child.group child.force))
    requests := requests ++ [⟨⟨row.token,row.group,child⟩,row.force⟩]
  if tokens.eraseDups.length != tokens.length then throw "Registration tokens must be unique."
  let result := run scenario.detached scenario.active requests
  pure (Json.mkObj [("before",snapshot result.before),("first",snapshot result.first),
    ("second",snapshot result.second)])

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one callback research input."; return 2
  match Json.parse (← IO.FS.readFile path) >>= fromJson? (α := Input) with
  | .error error => IO.eprintln error; return 2
  | .ok input =>
    if input.schema != 1 || input.profile != "single-thread-leaf-callback-drain" ||
        !input.singleThreaded || !input.callbacksDoNotThrowOrCancel ||
        input.scenarios.length > 16 then
      IO.eprintln "Unsupported callback research scope."; return 2
    match input.scenarios.mapM evaluate with
    | .error error => IO.eprintln error; return 2
    | .ok values => IO.println (toJson values).compress; return 0
