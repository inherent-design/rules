import Lean
import applications.cargo.LockSources
open Lean ApplicationStudy.CargoLockSources

private structure Raw where
  source : String
  operation : String
  locked : Bool
  offline : Bool
  pathV2 : Bool
  remoteB : Bool
  beforeLock : Nat
  cacheHead : Nat
  hasA : Bool
  hasB : Bool
  deriving FromJson
private structure Input where
  schema : Nat
  profile : String
  cases : List Raw
  deriving FromJson

private def selection (n : Nat) : Except String Selection :=
  match n with
  | 0 => pure .missing | 1 => pure .pathV1 | 2 => pure .pathV2
  | 3 => pure .gitA | 4 => pure .gitB | 5 => pure .patched
  | _ => throw "Unknown lock selection."

private def evaluate (r : Raw) : Except String (List Nat) := do
  let source ← match r.source with
    | "path" => pure Source.path | "git" => pure .git | "patch" => pure .patch
    | _ => throw "Outside the path/local-Git/compatible-patch profile."
  let operation ← match r.operation with
    | "metadata" => pure Operation.metadata | "generate" => pure .generate | "update" => pure .update
    | _ => throw "Unsupported metadata/lock operation."
  let old ← selection r.beforeLock
  unless (r.cacheHead == 0 && !r.hasA && !r.hasB) ||
      (r.cacheHead == 1 && r.hasA && !r.hasB) ||
      (r.cacheHead == 2 && r.hasA && r.hasB) do
    throw "Unadmitted cache usability/coverage premise."
  unless (source == .path && [0,1,2].contains r.beforeLock && !r.remoteB) ||
      (source == .git && [0,3,4].contains r.beforeLock && !r.pathV2) ||
      (source == .patch && [3,4,5].contains r.beforeLock && !r.pathV2) do
    throw "Lock/source context does not belong to this fixture."
  unless operation != .generate || source == .path do throw "Git regeneration is not this native profile."
  unless operation != .update || source == .git do throw "Only the selected Git update is admitted."
  unless source != .git || r.beforeLock == 0 || r.cacheHead > 0 do
    throw "Cold acquisition of a previously locked revision is not observed here."
  unless source != .path || r.cacheHead == 0 do throw "Path cases use the initial private cache."
  unless source != .patch || (r.remoteB && r.cacheHead == 2) do
    throw "The patch case uses the already admitted Git catalog."
  pure (observed (run ⟨source,operation,r.locked,r.offline,r.pathV2,r.remoteB,old,⟨r.cacheHead,r.hasA,r.hasB⟩⟩))

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one retained Cargo lock/source input."; return 2
  match Json.parse (← IO.FS.readFile path) >>= fromJson? (α := Input) with
  | .error e => IO.eprintln e; return 2
  | .ok input =>
    if input.schema != 1 || input.profile != "cargo-1.92-owned-lock-sources" || input.cases.isEmpty || input.cases.length > 24 then
      IO.eprintln "Unsupported lock/source schema,profile,or case count."; return 2
    match input.cases.mapM evaluate with
    | .error e => IO.eprintln e; return 2
    | .ok values => IO.println (toJson values).compress; return 0
