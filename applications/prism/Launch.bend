import Base

# Two conditional projections: finalization of the observed started prefix,
# and abort admission/delivery for the controlled current step. This is not
# the full sequence interpreter, native process ownership, or UI controller.
type AbortPolicy is Data:
  Disabled{}
  Refused{}
  Synchronous{}
  Queued{}

type AbortResult is Data:
  AbortResult{accepted: Bool, pending: Bool, base_failed: Bool}

def abort_projection(policy: AbortPolicy, +delivered: Bool) -> AbortResult:
  match policy:
    case Disabled{}: AbortResult{False{},False{},False{}}
    case Refused{}: AbortResult{False{},False{},False{}}
    case Synchronous{}: AbortResult{True{},False{},True{}}
    case Queued{}: AbortResult{True{},Bool.not(delivered),delivered}

def finalized(terminal: Bool, started: List<&2,Nat>) -> List<&2,Nat>:
  match terminal:
    case False{}: []
    case True{}: List.reverse(&2,Nat,started)

law queued_acceptance_is_not_completion:
  {abort_projection(Queued{},False{}) == AbortResult{True{},True{},False{}} : AbortResult}
def queued_acceptance_is_not_completion():
  {==}

law delivered_abort_reports_failure:
  {abort_projection(Queued{},True{}) == AbortResult{True{},False{},True{}} : AbortResult}
def delivered_abort_reports_failure():
  {==}

law refused_abort_does_not_complete:
  for delivered: Bool
  {abort_projection(Refused{},delivered) == AbortResult{False{},False{},False{}} : AbortResult}
def refused_abort_does_not_complete(delivered):
  {==}

law pending_sequence_finalizes_nothing:
  for started: List<&2,Nat>
  {finalized(False{},started) == [] : List<&2,Nat>}
def pending_sequence_finalizes_nothing(started):
  {==}

def main() -> IO(Unit):
  IO.print("Conditional launch-task projections,not process-retirement evidence.")
