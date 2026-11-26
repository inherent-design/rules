import Lean
import applications.restic.Repository
open Lean ApplicationStudy.ResticRepository

private structure Raw where
  kind : String
  requestedVersion : Nat
  version : Nat
  hasKeys : Bool
  hasSnapshots : Bool
  otherPassword : Bool
  knownMigration : Bool
  unknownMigration : Bool
  strictUnknown : Bool
  deriving FromJson
private structure Input where
  schema : Nat
  profile : String
  cases : List Raw
  deriving FromJson

private def evaluate (r : Raw) : Except String Json := do
  let kind ← match r.kind with
    | "init" => pure Kind.initialize | "open" => pure .openRepo
    | "migrate-list" => pure .listMigrations | "migrate-apply" => pure .applyMigrations
    | _ => throw "Unsupported repository operation."
  unless [0,1,2].contains r.version && [1,2,99].contains r.requestedVersion do throw "Unadmitted format profile."
  unless kind == .applyMigrations || (!r.knownMigration && !r.unknownMigration && !r.strictUnknown) do
    throw "Migration names and result policy belong to apply requests."
  unless kind != .applyMigrations || r.knownMigration || r.unknownMigration do throw "Apply needs a migration name."
  unless kind == .initialize || r.requestedVersion == 2 do throw "Only initialization selects an output format."
  unless kind == .openRepo || !r.otherPassword do throw "Other-password profile is measured only for opening."
  unless kind == .initialize || r.version == 0 || r.hasKeys do throw "An admitted positive config needs its usable key context."
  unless ![Kind.listMigrations,.applyMigrations].contains kind || (r.version > 0 && !r.otherPassword) do
    throw "Migration projection needs an authenticated repository."
  let out := run ⟨kind,r.requestedVersion,r.version,r.hasKeys,r.hasSnapshots,r.otherPassword,r.knownMigration,r.unknownMigration,r.strictUnknown⟩
  pure (Json.arr #[toJson out.status,toJson out.version,toJson out.configChanged,toJson out.unknownReported,toJson out.skippedReported,toJson out.appliedReported,toJson out.upgradeListed])

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one repository study input."; return 2
  match Json.parse (← IO.FS.readFile path) >>= fromJson? (α := Input) with
  | .error e => IO.eprintln e; return 2
  | .ok input =>
    if input.schema != 1 || input.profile != "restic-local-repository-lifecycle" || input.cases.isEmpty || input.cases.length > 32 then
      IO.eprintln "Unsupported repository study schema, profile, or count."; return 2
    match input.cases.mapM evaluate with
    | .error e => IO.eprintln e; return 2
    | .ok out => IO.println (toJson out).compress; return 0
