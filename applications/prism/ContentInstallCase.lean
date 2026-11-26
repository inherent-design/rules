import Lean
import applications.prism.ContentInstall
open Lean ApplicationStudy.PrismContentInstall

private structure Raw where
  policy : String
  source : String
  destination : Nat
  sourcePayload : Nat
  disabledSibling : Bool
  drop : Bool
  extraMissing : Bool
  watching : Bool
  refreshResult : Bool
  cancelBeforeCommit : Bool
  deriving FromJson
private structure Input where
  schema : Nat
  profile : String
  cases : List Raw
  deriving FromJson

private def evaluate (r : Raw) : Except String Json := do
  let policy ← match r.policy with
    | "current" => pure Policy.current | "guarded" => pure .guarded | "staged" => pure .staged
    | _ => throw "Unknown implementation policy."
  let source ← match r.source with
    | "regular" => pure Source.regular | "same-path" => pure .samePath
    | "destination-alias" => pure .destinationAlias | "missing" => pure .missing
    | _ => throw "Unadmitted source relation."
  unless [0,1,2,4].contains r.destination && [0,1,2,4].contains r.sourcePayload do throw "Unknown payload class."
  unless (source == .missing && r.sourcePayload == 0) ||
      (source == .regular && r.sourcePayload > 0) ||
      ([Source.samePath, .destinationAlias].contains source && r.destination > 0 && r.sourcePayload == r.destination) do
    throw "Source/payload existence is inconsistent."
  unless !r.extraMissing || r.drop do throw "Only the drop case has a second missing input."
  unless !r.cancelBeforeCommit || policy == .staged do throw "Only staged proposal has the precommit hook."
  unless policy == .current || (r.watching && r.refreshResult && !r.disabledSibling && !r.extraMissing) do
    throw "Candidate profile does not qualify these additional caller states."
  unless r.sourcePayload != 4 || (policy == .staged && source == .regular && r.destination == 0 && !r.drop && !r.cancelBeforeCommit) do
    throw "Multichunk continuation has one selected staged-copy context."
  let out := run ⟨policy,source,r.destination,r.sourcePayload,r.disabledSibling,r.drop,r.extraMissing,
    r.watching,r.refreshResult,r.cancelBeforeCommit⟩
  pure (Json.arr #[toJson out.surface,toJson out.items,toJson out.destination,toJson out.sourceAlive,toJson out.disabledSibling,toJson out.refreshCalls])

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one retained resource-install input."; return 2
  match Json.parse (← IO.FS.readFile path) >>= fromJson? (α := Input) with
  | .error e => IO.eprintln e; return 2
  | .ok input =>
    if input.schema != 1 || input.profile != "prism-regular-content-install" || input.cases.isEmpty || input.cases.length > 32 then
      IO.eprintln "Unsupported install research schema,profile,or count."; return 2
    match input.cases.mapM evaluate with
    | .error e => IO.eprintln e; return 2
    | .ok values => IO.println (toJson values).compress; return 0
