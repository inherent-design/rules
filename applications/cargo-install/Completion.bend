import Base

# tracking 0 disabled, 1 saved, 2 failed; admitted by the scoped decoder.
# A new bin is already published and one replacement was requested.
type Current is Data:
  Current{failed: Bool, new_survives: Bool, headline: Bool}
type Proposed is Data:
  Proposed{failed: Bool, replacement_report: Bool}

def current(+tracking: Nat,+replacement_failed: Bool) -> Current:
  +failed = Bool.and(Bool.not(Nat.is_eq(tracking,0n)),replacement_failed)
  Current{failed,Bool.not(failed),Bool.not(failed)}

def proposed(tracking: Nat,+replacement_failed: Bool) -> Proposed:
  Proposed{Bool.or(replacement_failed,Nat.is_eq(tracking,2n)),Bool.not(replacement_failed)}

def flag(v: Bool) -> String:
  Bool.pick(String,v,"1","0")

def render_results(c: Current,p: Proposed) -> String:
  match c:
    case Current{a,b,c}:
      match p:
        case Proposed{d,e}: flag(a) ++ "/" ++ flag(b) ++ "/" ++ flag(c) ++ "/" ++ flag(d) ++ "/" ++ flag(e)

def render(+tracking: Nat,+replacement_failed: Bool) -> String:
  render_results(current(tracking,replacement_failed),proposed(tracking,replacement_failed))

def command_failed(c: Current) -> Bool:
  match c:
    case Current{failed,_,_}: failed
def replacement_headline(c: Current) -> Bool:
  match c:
    case Current{_,_,headline}: headline
def new_survives(c: Current) -> Bool:
  match c:
    case Current{_,survives,_}: survives
def proposed_failed(p: Proposed) -> Bool:
  match p:
    case Proposed{failed,_}: failed
def proposed_headline(p: Proposed) -> Bool:
  match p:
    case Proposed{_,headline}: headline

def law_untracked_error_masked() -> Bool:
  Bool.not(command_failed(current(0n,True{})))
def law_untracked_false_headline() -> Bool:
  replacement_headline(current(0n,True{}))
def law_untracked_new_survives() -> Bool:
  new_survives(current(0n,True{}))
def law_tracked_new_removed() -> Bool:
  Bool.not(new_survives(current(1n,True{})))
def law_tracking_error_masked() -> Bool:
  Bool.not(command_failed(current(2n,False{})))
def law_both_errors_fail() -> Bool:
  command_failed(current(2n,True{}))
def law_proposed_replacement_error() -> Bool:
  Bool.and(proposed_failed(proposed(0n,True{})),Bool.not(proposed_headline(proposed(0n,True{}))))
def law_proposed_tracking_error() -> Bool:
  proposed_failed(proposed(2n,False{}))
def law_effect_and_failure_separate() -> Bool:
  Bool.and(proposed_failed(proposed(2n,False{})),proposed_headline(proposed(2n,False{})))
