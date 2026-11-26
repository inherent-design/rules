namespace ApplicationStudy.ResticRepository

inductive Kind | initialize | openRepo | listMigrations | applyMigrations
  deriving BEq, DecidableEq, Repr

/-- A local fixture policy projection. Version zero means absent config.
    Positive versions require independently authenticated, valid config evidence.
    Key/snapshot flags denote recognized object IDs, not arbitrary filenames.
    Successful IO, usable keys for opening, and controlled credential profiles
    are admitted premises, not a cryptographic or backend model. -/
structure Request where
  kind : Kind
  requestedVersion : Nat
  version : Nat
  hasKeys : Bool
  hasSnapshots : Bool
  otherPassword : Bool
  knownMigration : Bool
  unknownMigration : Bool
  strictUnknown : Bool
  deriving Repr

structure Outcome where
  status : Nat
  version : Nat
  configChanged : Bool
  unknownReported : Bool
  skippedReported : Bool
  appliedReported : Bool
  upgradeListed : Bool
  deriving BEq, DecidableEq, Repr

def run (r : Request) : Outcome :=
  match r.kind with
  | .initialize =>
    if !([1,2].contains r.requestedVersion) || r.version != 0 || r.hasKeys || r.hasSnapshots then
      ⟨1,r.version,false,false,false,false,false⟩
    else ⟨0,r.requestedVersion,true,false,false,false,false⟩
  | .openRepo =>
    ⟨if r.version == 0 then 10 else if r.otherPassword then 12 else 0,
     r.version,false,false,false,false,false⟩
  | .listMigrations => ⟨0,r.version,false,false,false,false,r.version == 1⟩
  | .applyMigrations =>
    let applies := r.knownMigration && r.version == 1
    ⟨if r.strictUnknown && r.unknownMigration then 1 else 0,
     if applies then 2 else r.version,applies,r.unknownMigration,
     r.knownMigration && r.version != 1,applies,false⟩

def fresh : Request := ⟨.initialize,1,0,false,false,false,false,false,false⟩
def migrating : Request := ⟨.applyMigrations,2,1,true,true,false,true,false,false⟩

theorem init_selects_requested_format : run fresh = ⟨0,1,true,false,false,false,false⟩ := by decide
theorem unsupported_init_does_not_create_config :
    run { fresh with requestedVersion := 99 } = ⟨1,0,false,false,false,false,false⟩ := by decide
theorem existing_keys_refuse_reinitialization :
    run { fresh with hasKeys := true } = ⟨1,0,false,false,false,false,false⟩ := by decide
theorem retained_snapshots_refuse_reinitialization :
    run { fresh with hasSnapshots := true } = ⟨1,0,false,false,false,false,false⟩ := by decide
theorem missing_config_precedes_authentication :
    (run { fresh with kind := .openRepo, otherPassword := true }).status = 10 := by decide
theorem unknown_name_can_return_zero :
    run { migrating with knownMigration := false, unknownMigration := true } =
      ⟨0,1,false,true,false,false,false⟩ := by decide
theorem mixed_unknown_request_can_still_upgrade :
    run { migrating with unknownMigration := true } = ⟨0,2,true,true,false,true,false⟩ := by decide
theorem repeated_upgrade_is_a_skipped_zero :
    run { migrating with version := 2 } = ⟨0,2,false,false,true,false,false⟩ := by decide
theorem proposed_strict_status_does_not_imply_rollback :
    run { migrating with unknownMigration := true, strictUnknown := true } =
      ⟨1,2,true,true,false,true,false⟩ := by decide
theorem proposed_status_policy_preserves_version (r : Request) :
    (run { r with strictUnknown := true }).version = (run { r with strictUnknown := false }).version := by
  cases r.kind <;> rfl

end ApplicationStudy.ResticRepository
