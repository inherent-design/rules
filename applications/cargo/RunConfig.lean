namespace ApplicationStudy.CargoRunConfig

inductive Runner | direct | project | environment | cli
  deriving BEq, ReflBEq, LawfulBEq, DecidableEq, Repr
structure Request where
  packageCwd : Bool := true
  explicitFile : Bool := false
  environmentRunner : Bool := false
  cliRunner : Bool := false
  invalidEnvironmentJobs : Bool := false
  cliJobs : Bool := false
  build : Option Bool := some true
  oldArtifact : Bool := false
  runnerStatus : Nat := 0
  applicationStatus : Nat := 0
  deriving Repr

/-- Current pinned PathAndArgs/StringList behavior, not general scalar config
precedence. The native CLI+environment control executes the environment runner. -/
def runner (r : Request) : Runner :=
  if r.environmentRunner then .environment
  else if r.cliRunner then .cli
  else if r.packageCwd || r.explicitFile then .project else .direct

/-- Proposed priority correction. No patched Cargo was executed. -/
def proposedRunner (r : Request) : Runner :=
  if r.cliRunner then .cli
  else if r.environmentRunner then .environment
  else if r.packageCwd || r.explicitFile then .project else .direct

def configurationAccepted (r : Request) : Bool :=
  !r.invalidEnvironmentJobs || r.cliJobs
def runnerId : Runner → Nat
  | .direct => 0 | .project => 1 | .environment => 2 | .cli => 3
structure Outcome where
  runnerStarted : Bool
  applicationStarted : Bool
  executedRunner : Nat
  stage : Nat
  code : Nat
  applicationCwd : Nat
  deriving BEq, DecidableEq, Repr

/-- Build result is an admitted phase witness, compared against independent
runner/application journals and process status. This is not a Rust compiler,
freshness algorithm, arbitrary launcher, or process-retirement model. -/
def run (r : Request) : Outcome :=
  let configured := configurationAccepted r
  let built := r.build == some true
  let eligible := configured && built
  let wrapped := runner r != .direct
  let application := eligible && (!wrapped || r.runnerStatus == 0)
  let stage := if !configured then 1 else if !built then 2
    else if wrapped && r.runnerStatus != 0 then 3
    else if r.applicationStatus != 0 then 4 else 0
  { runnerStarted := eligible && wrapped
    applicationStarted := application
    executedRunner := if eligible && wrapped then runnerId (runner r) else 0
    stage := stage
    code := if !eligible then 101 else if wrapped && r.runnerStatus != 0 then r.runnerStatus else r.applicationStatus
    applicationCwd := if application then (if r.packageCwd then 0 else 1) else 2 }

theorem retained_artifact_is_not_fallback_authority (r : Request) :
    run { r with oldArtifact := true } = run { r with oldArtifact := false } := rfl
theorem failed_build_does_not_launch_retained_binary :
    (run { build := some false, oldArtifact := true }).runnerStarted = false ∧
    (run { build := some false, oldArtifact := true }).applicationStarted = false := ⟨rfl,rfl⟩
theorem configuration_refusal_precedes_build_execution :
    (run { invalidEnvironmentJobs := true, build := none }).stage = 1 ∧
    (run { invalidEnvironmentJobs := true, build := none }).code = 101 := ⟨rfl,rfl⟩
theorem scalar_cli_jobs_override_invalid_environment :
    configurationAccepted { invalidEnvironmentJobs := true, cliJobs := true } = true := rfl
theorem runner_error_is_after_a_successful_build :
    (run { runnerStatus := 9 }).stage = 3 ∧
    (run { runnerStatus := 9 }).applicationStarted = false ∧
    (run { runnerStatus := 9 }).code = 9 := ⟨rfl,rfl,rfl⟩
theorem application_status_is_not_a_compile_failure :
    (run { applicationStatus := 7 }).stage = 4 ∧
    (run { applicationStatus := 7 }).applicationStarted = true ∧
    (run { applicationStatus := 7 }).code = 7 := ⟨rfl,rfl,rfl⟩
theorem parent_invocation_does_not_discover_child_config :
    runner { packageCwd := false } = .direct := rfl
theorem manifest_selection_does_not_change_invocation_cwd :
    (run { packageCwd := false }).applicationCwd = 1 := rfl
theorem explicit_file_can_restore_runner_without_changing_cwd :
    (run { packageCwd := false, explicitFile := true }).executedRunner = 1 ∧
    (run { packageCwd := false, explicitFile := true }).applicationCwd = 1 := ⟨rfl,rfl⟩
theorem cli_runner_alone_is_selected : runner { cliRunner := true } = .cli := rfl
theorem current_and_proposed_conflicting_priority_differ :
    runner { cliRunner := true, environmentRunner := true } = .environment ∧
    proposedRunner { cliRunner := true, environmentRunner := true } = .cli := ⟨rfl,rfl⟩
theorem proposed_priority_keeps_nonconflicting_choices (r : Request)
    (h : !(r.environmentRunner && r.cliRunner) = true) : runner r = proposedRunner r := by
  cases env : r.environmentRunner <;> cases cli : r.cliRunner <;>
    simp_all [runner,proposedRunner]

end ApplicationStudy.CargoRunConfig
