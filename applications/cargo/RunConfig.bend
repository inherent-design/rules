import Base

# Current pinned runner retrieval and generated scalar-jobs profile.
# build=None means not attempted;Some false/true are compiler phase witnesses.
type RunRequest is Data:
  RR{package_cwd: Bool,explicit_file: Bool,environment_runner: Bool,cli_runner: Bool,invalid_jobs: Bool,cli_jobs: Bool,build: Maybe<&2,Bool>,old_artifact: Bool,runner_status: Nat,application_status: Nat}
type RunOutcome is Data:
  RO{runner_started: Bool,application_started: Bool,executed_runner: Nat,stage: Nat,status: Nat,application_cwd: Nat}

def select_runner(package: Bool,file: Bool,environment: Bool,cli: Bool) -> Nat:
  Bool.pick(Nat,environment,2n,Bool.pick(Nat,cli,3n,Bool.pick(Nat,Bool.or(package,file),1n,0n)))
def proposed_runner(package: Bool,file: Bool,environment: Bool,cli: Bool) -> Nat:
  Bool.pick(Nat,cli,3n,Bool.pick(Nat,environment,2n,Bool.pick(Nat,Bool.or(package,file),1n,0n)))
def build_passed(build: Maybe<&2,Bool>) -> Bool:
  match build:
    case None{}: False{}
    case Some{value}: value
def run(r: RunRequest) -> RunOutcome:
  match r:
    case RR{+package,file,environment,cli,invalid,cli_jobs,build,_,+runner_status,+application_status}:
      +valid=Bool.or(Bool.not(invalid),cli_jobs)
      +built=build_passed(build)
      +eligible=Bool.and(valid,built)
      +selected=select_runner(package,file,environment,cli)
      +wrapped=Bool.not(Nat.is_eq(selected,0n))
      +application=Bool.and(eligible,Bool.or(Bool.not(wrapped),Nat.is_eq(runner_status,0n)))
      +runner_failed=Bool.and(wrapped,Bool.not(Nat.is_eq(runner_status,0n)))
      stage=Bool.pick(Nat,Bool.not(valid),1n,Bool.pick(Nat,Bool.not(built),2n,Bool.pick(Nat,runner_failed,3n,Bool.pick(Nat,Bool.not(Nat.is_eq(application_status,0n)),4n,0n))))
      RO{Bool.and(eligible,wrapped),application,Bool.pick(Nat,Bool.and(eligible,wrapped),selected,0n),stage,Bool.pick(Nat,Bool.not(eligible),101n,Bool.pick(Nat,runner_failed,runner_status,application_status)),Bool.pick(Nat,application,Bool.pick(Nat,package,0n,1n),2n)}

law retained_binary_does_not_bypass_failed_compile:
  {run(RR{True{},False{},False{},False{},False{},False{},Some{False{}},True{},0n,0n}) == RO{False{},False{},0n,2n,101n,2n} : RunOutcome}
def retained_binary_does_not_bypass_failed_compile(): {==}
law configuration_failure_is_not_a_build_result:
  {run(RR{True{},False{},False{},False{},True{},False{},None{},True{},0n,0n}) == RO{False{},False{},0n,1n,101n,2n} : RunOutcome}
def configuration_failure_is_not_a_build_result(): {==}
law cli_scalar_override_admits_run:
  {run(RR{True{},False{},False{},False{},True{},True{},Some{True{}},True{},0n,0n}) == RO{True{},True{},1n,0n,0n,0n} : RunOutcome}
def cli_scalar_override_admits_run(): {==}
law runner_failure_keeps_compiler_success_separate:
  {run(RR{True{},False{},False{},False{},False{},False{},Some{True{}},True{},9n,0n}) == RO{True{},False{},1n,3n,9n,2n} : RunOutcome}
def runner_failure_keeps_compiler_success_separate(): {==}
law application_failure_is_after_execution:
  {run(RR{True{},False{},False{},False{},False{},False{},Some{True{}},True{},0n,7n}) == RO{True{},True{},1n,4n,7n,0n} : RunOutcome}
def application_failure_is_after_execution(): {==}
law parent_manifest_does_not_load_child_runner:
  {run(RR{False{},False{},False{},False{},False{},False{},Some{True{}},True{},0n,0n}) == RO{False{},True{},0n,0n,0n,1n} : RunOutcome}
def parent_manifest_does_not_load_child_runner(): {==}
law explicit_file_restores_runner_but_keeps_cwd:
  {run(RR{False{},True{},False{},False{},False{},False{},Some{True{}},True{},0n,0n}) == RO{True{},True{},1n,0n,0n,1n} : RunOutcome}
def explicit_file_restores_runner_but_keeps_cwd(): {==}
law current_runner_environment_replaces_cli:
  {select_runner(True{},False{},True{},True{}) == 2n : Nat}
def current_runner_environment_replaces_cli(): {==}
law proposed_cli_priority_is_separate:
  {proposed_runner(True{},False{},True{},True{}) == 3n : Nat}
def proposed_cli_priority_is_separate(): {==}
law cli_alone_is_not_ignored:
  {select_runner(True{},False{},False{},True{}) == 3n : Nat}
def cli_alone_is_not_ignored(): {==}

def number(b: Bool) -> Nat: Bool.pick(Nat,b,1n,0n)
def render(r: RunOutcome) -> String:
  match r:
    case RO{a,b,c,d,e,f}: Nat.show(number(a)) ++ "/" ++ Nat.show(number(b)) ++ "/" ++ Nat.show(c) ++ "/" ++ Nat.show(d) ++ "/" ++ Nat.show(e) ++ "/" ++ Nat.show(f)
def main() -> IO(Unit): IO.print("Configuration, successful compilation, runner start, and application outcome remain separate.")
