import Base

# Proposed boundary: 0 inspect, 1 preview, 2 apply.
# Decision: 0 inspect, 1 plan, 2 apply, 3 require approval, 4 refresh, 5 refuse.
# Host witnesses bind unchanged target, complete evidence, and exact approval.
def decide(mode: Nat, current: Bool, evidence: Bool, approved: Bool) -> Nat:
  match mode:
    case 0n:
      0n
    case 1n:
      1n
    case _:
      match current:
        case False{}: 4n
        case True{}:
          match evidence:
            case False{}: 5n
            case True{}:
              match approved:
                case False{}: 3n
                case True{}: 2n

# Cancellation is an execution input; the established terminal result survives.
def finish(cancel_requested: Bool, actual_status: Nat) -> Nat:
  actual_status

law preview_never_applies:
  for current: Bool
  for evidence: Bool
  for approved: Bool
  {decide(1n, current, evidence, approved) == 1n : Nat}
def preview_never_applies(current, evidence, approved):
  {==}

law stale_target_requires_refresh:
  for evidence: Bool
  for approved: Bool
  {decide(2n, False{}, evidence, approved) == 4n : Nat}
def stale_target_requires_refresh(evidence, approved):
  {==}

law incomplete_evidence_refuses:
  for approved: Bool
  {decide(2n, True{}, False{}, approved) == 5n : Nat}
def incomplete_evidence_refuses(approved):
  {==}

law late_cancel_keeps_status:
  for actual: Nat
  {finish(True{}, actual) == actual : Nat}
def late_cancel_keeps_status(actual):
  {==}

def bit(value: Bool) -> Nat:
  match value:
    case False{}: 0n
    case True{}: 1n

def row(+mode: Nat, +current: Bool, +evidence: Bool, +approved: Bool) -> String:
  Nat.show(mode) ++ "," ++ Nat.show(bit(current)) ++ "," ++ Nat.show(bit(evidence)) ++ "," ++ Nat.show(bit(approved)) ++ "," ++ Nat.show(decide(mode, current, evidence, approved)) ++ "\n"

def main() -> IO(Unit):
  do IO<Unit>:
    IO.print(
      row(0n, False{}, False{}, False{}) ++
      row(0n, False{}, False{}, True{}) ++
      row(0n, False{}, True{}, False{}) ++
      row(0n, False{}, True{}, True{}) ++
      row(0n, True{}, False{}, False{}) ++
      row(0n, True{}, False{}, True{}) ++
      row(0n, True{}, True{}, False{}) ++
      row(0n, True{}, True{}, True{}) ++
      row(1n, False{}, False{}, False{}) ++
      row(1n, False{}, False{}, True{}) ++
      row(1n, False{}, True{}, False{}) ++
      row(1n, False{}, True{}, True{}) ++
      row(1n, True{}, False{}, False{}) ++
      row(1n, True{}, False{}, True{}) ++
      row(1n, True{}, True{}, False{}) ++
      row(1n, True{}, True{}, True{}) ++
      row(2n, False{}, False{}, False{}) ++
      row(2n, False{}, False{}, True{}) ++
      row(2n, False{}, True{}, False{}) ++
      row(2n, False{}, True{}, True{}) ++
      row(2n, True{}, False{}, False{}) ++
      row(2n, True{}, False{}, True{}) ++
      row(2n, True{}, True{}, False{}) ++
      row(2n, True{}, True{}, True{}))
