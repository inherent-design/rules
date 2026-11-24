import Base

# Boolean projection of the observed compatibility/stale-removal decisions.
def compatible(request_exclusive: Bool, held_exclusive: Bool, readable: Bool, empty: Bool) -> Bool:
  Bool.or(empty,Bool.and(readable,Bool.not(Bool.or(request_exclusive,held_exclusive))))

def stale(old: Bool, same_host: Bool, reachable: Bool) -> Bool:
  Bool.or(old,Bool.and(same_host,Bool.not(reachable)))

def remove_stale(readable: Bool, empty: Bool, old: Bool, same_host: Bool, reachable: Bool) -> Bool:
  Bool.and(Bool.and(readable,Bool.not(empty)),stale(old,same_host,reachable))

# Proposed refinement; unknown is distinct from a confirmed absent process.
type Probe is Data:
  Reachable{}
  Absent{}
  Unknown{}

def absent(probe: Probe) -> Bool:
  match probe:
    case Reachable{}: False{}
    case Absent{}: True{}
    case Unknown{}: False{}

def candidate_stale(old: Bool, same_host: Bool, probe: Probe) -> Bool:
  Bool.or(old,Bool.and(same_host,absent(probe)))

law shared_compatible:
  {compatible(False{},False{},True{},False{}) == True{} : Bool}
def shared_compatible():
  {==}

law exclusive_conflicts_with_shared:
  {compatible(True{},False{},True{},False{}) == False{} : Bool}
def exclusive_conflicts_with_shared():
  {==}

law unreadable_is_not_absent:
  for request_exclusive: Bool
  {compatible(request_exclusive,False{},False{},False{}) == False{} : Bool}
def unreadable_is_not_absent(request_exclusive):
  {==}

law unknown_does_not_mean_absent:
  {candidate_stale(False{},True{},Unknown{}) == False{} : Bool}
def unknown_does_not_mean_absent():
  {==}

def main() -> IO(Unit):
  IO.print("Lock compatibility,source stale policy,and separately proposed process-probe classification.")
