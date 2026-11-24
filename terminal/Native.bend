import Base

# Bounded projections of the named native fixtures, not universal CLI laws.
# Tool: 0 npm, 1 pnpm, 2 Yarn Berry, 3 empack.
# Case: 0 top help, 1 unknown command, 2 selected preview/lock-write mode,
# 3 controlled interruption (empack is the observed late-cancel completion).
# Exit encoding: exit code, or 256 + POSIX signal. Scopes are independent.

def npm_exit(case_id: Nat) -> Nat:
  match case_id:
    case 0n: 1n
    case 1n: 1n
    case 2n: 0n
    case _: 258n

def pnpm_exit(case_id: Nat) -> Nat:
  match case_id:
    case 0n: 0n
    case 1n: 1n
    case 2n: 0n
    case _: 258n

def yarn_exit(case_id: Nat) -> Nat:
  match case_id:
    case 0n: 0n
    case 1n: 1n
    case 2n: 0n
    case _: 129n

def empack_exit(case_id: Nat) -> Nat:
  match case_id:
    case 0n: 0n
    case 1n: 2n
    case _: 0n

def exit_for(tool: Nat, case_id: Nat) -> Nat:
  match tool:
    case 0n: npm_exit(case_id)
    case 1n: pnpm_exit(case_id)
    case 2n: yarn_exit(case_id)
    case _: empack_exit(case_id)

def project_changed(tool: Nat, case_id: Nat) -> Bool:
  match case_id:
    case 1n:
      Nat.is_eq(tool, 1n)
    case 2n:
      Nat.is_eq(tool, 2n)
    case 3n:
      True{}
    case _:
      False{}

# Result/diagnostic payload channel for the unknown-command fixtures.
# This describes current behavior; it does not endorse prose on machine stdout.
def refusal_channel(tool: Nat) -> Nat:
  match tool:
    case 0n: 0n
    case 1n: 1n
    case 2n: 0n
    case _: 1n

law refusal_can_have_effects:
  {project_changed(1n, 1n) == True{} : Bool}
def refusal_can_have_effects():
  {==}

law lock_write_is_not_preview:
  {project_changed(2n, 2n) == True{} : Bool}
def lock_write_is_not_preview():
  {==}

law empack_late_cancel_preserves_completed_status:
  {empack_exit(3n) == 0n : Nat}
def empack_late_cancel_preserves_completed_status():
  {==}

# Executable joined projection consumed by replay.py. One fixed finite table.
def bit(value: Bool) -> Nat:
  match value:
    case False{}: 0n
    case True{}: 1n

def row(+tool: Nat, +case_id: Nat) -> String:
  Nat.show(tool) ++ "," ++ Nat.show(case_id) ++ "," ++ Nat.show(exit_for(tool, case_id)) ++ "," ++ Nat.show(bit(project_changed(tool, case_id))) ++ "," ++ Nat.show(refusal_channel(tool)) ++ "\n"

def main() -> IO(Unit):
  do IO<Unit>:
    IO.print(
      row(0n, 0n) ++
      row(0n, 1n) ++
      row(0n, 2n) ++
      row(0n, 3n) ++
      row(1n, 0n) ++
      row(1n, 1n) ++
      row(1n, 2n) ++
      row(1n, 3n) ++
      row(2n, 0n) ++
      row(2n, 1n) ++
      row(2n, 2n) ++
      row(2n, 3n) ++
      row(3n, 0n) ++
      row(3n, 1n) ++
      row(3n, 2n) ++
      row(3n, 3n))
