import Lean
import applications.prism.Launch
open Lean ApplicationStudy.PrismLaunch

private structure Row where
  id : String
  modes : List String
  action : String
  deriving FromJson
private structure Input where
  schema : Nat
  cases : List Row
  deriving FromJson
private structure Snapshot where
  phase : Nat
  baseState : Nat
  running : Bool
  finished : Bool
  successful : Bool
  canAbort : Bool
  stepIndex : Int
  instanceRunning : Bool
  instanceCrashed : Bool
  reason : String
  deriving ToJson
private structure Output where
  id : String
  initial : Snapshot
  afterStart : Snapshot
  abortAccepted : Option Bool
  afterAction : Snapshot
  actionEvents : List String
  afterDrain : Snapshot
  events : List String
  deriving ToJson

private def snapshot (work : Work) : Snapshot :=
  ⟨phaseCode work.phase, outcomeCode work.outcome, work.outcome == .running,
    work.outcome != .running && work.outcome != .inactive, work.outcome == .succeeded,
    canAbort work, work.current.map Int.ofNat |>.getD (-1), work.instanceRunning,
    work.instanceCrashed, work.reason⟩

private def decode : String → Except String Kind
  | "success" => pure .success
  | "failure" => pure .failure
  | "ready" => pure .ready
  | "progress" => pure .progress
  | "hold-no-abort" => pure .disabled
  | "hold-refuse" => pure .refuse
  | "hold-sync" => pure .synchronous
  | "hold-queued" => pure .queued
  | _ => throw "Unknown controlled launch step."

private def evaluate (row : Row) : Except String Output := do
  let steps ← row.modes.mapM decode
  let initial : Work := {}
  let started := start steps
  let (accepted, acted) ← match row.action with
    | "none" => pure (none, started)
    | "proceed" =>
      if started.phase != .waiting then throw "Fixture proceed requires a waiting step."
      pure (none, proceed started)
    | "abort" =>
      if started.outcome != .running then throw "Fixture abort requires an active hold step."
      match started.kind with
      | some .disabled | some .refuse | some .synchronous | some .queued =>
        let result := abort started
        pure (some result.1, result.2)
      | _ => throw "Fixture abort requires an active hold step."
    | _ => throw "Unknown launch action."
  let drained := drain acted
  pure ⟨row.id, snapshot initial, snapshot started, accepted, snapshot acted,
    acted.events, snapshot drained, drained.events⟩

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one controlled-launch JSON path."; return 2
  let text ← IO.FS.readFile path
  match Json.parse text >>= fromJson? (α := Input) with
  | .error error => IO.eprintln error; return 2
  | .ok input =>
    if input.schema != 1 then
      IO.eprintln "Unsupported controlled-launch schema."
      return 2
    match input.cases.mapM evaluate with
    | .error error => IO.eprintln error; return 2
    | .ok result => IO.println (toJson result).compress; return 0
