import Base

# Adapter supplies globally admitted inputs for one destination, ordered from
# side to shared override to common. Global validation/recipe decoding and
# preserved-layer inventories are compared separately by Lean.
type Requirement is Data:
  Unsupported{}
  Required{}
  Optional{default_enabled: Bool}
type Policy is Data:
  Preserve{}
  Unresolved{}
  Enable{}
  Disable{}
  Defaults{}
  Unknown{}
type Candidate is Data:
  Candidate{owner: Nat, requirement: Requirement}
type Pick is Data:
  Empty{}
  Chosen{owner: Nat, requirement_code: Nat}
  Blocked{reason: String}

def has_supported(candidates: List<&2,Candidate>) -> Bool:
  match candidates:
    case Nil{}: False{}
    case Con{head,tail}:
      match head:
        case Candidate{owner,requirement}:
          match requirement:
            case Unsupported{}: has_supported(tail)
            case Required{}: True{}
            case Optional{default_enabled}: True{}

def optional_code(default_enabled: Bool) -> Nat:
  match default_enabled:
    case True{}: 3n
    case False{}: 2n

def preserved_optional(fallback: Bool, full: Bool, owner: Nat, default_enabled: Bool) -> Pick:
  match fallback:
    case True{}: Blocked{"overlay-needs-choice"}
    case False{}:
      match full:
        case True{}: Blocked{"choice-required"}
        case False{}: Chosen{owner,optional_code(default_enabled)}

def choose(candidates: List<&2,Candidate>, policy: Policy, full: Bool) -> Pick:
  match candidates:
    case Nil{}: Empty{}
    case Con{head,tail}:
      match head:
        case Candidate{owner,requirement}:
          match requirement:
            case Unsupported{}: choose(tail,policy,full)
            case Required{}: Chosen{owner,1n}
            case Optional{default_enabled}:
              match policy:
                case Preserve{}: preserved_optional(has_supported(tail),full,owner,default_enabled)
                case Unresolved{}: Blocked{"choice-required"}
                case Enable{}: Chosen{owner,1n}
                case Disable{}: choose(tail,Disable{},full)
                case Defaults{}: Bool.pick(Pick,default_enabled,Chosen{owner,1n},choose(tail,Defaults{},full))
                case Unknown{}: Blocked{"unknown-choice"}

def label(pick: Pick) -> String:
  match pick:
    case Empty{}: "none"
    case Chosen{owner,requirement_code}: "s" ++ Nat.show(owner) ++ ":" ++ Nat.show(requirement_code)
    case Blocked{reason}: "error/" ++ reason

type Representation is Data:
  Embedded{}
  Unacquired{}
  Download{observed: Bool, origin: Bool}

def valid_download(observed: Bool, full: Bool) -> String:
  match observed:
    case False{}: "invalid-reference"
    case True{}: Bool.pick(String,full,"materialization","ok")

def complete(representation: Representation, full: Bool) -> String:
  match representation:
    case Embedded{}: "ok"
    case Unacquired{}: "materialization"
    case Download{observed,origin}:
      match origin:
        case False{}: "invalid-reference"
        case True{}: valid_download(observed,full)

law required_masks_lower_choices:
  for +owner: Nat
  for lower: List<&2,Candidate>
  for policy: Policy
  for full: Bool
  {choose(Con{Candidate{owner,Required{}},lower},policy,full) == Chosen{owner,1n} : Pick}
def required_masks_lower_choices(owner,lower,policy,full):
  {==}

law preserved_optional_cannot_erase_fallback:
  for full: Bool
  for owner: Nat
  for default_enabled: Bool
  {preserved_optional(True{},full,owner,default_enabled) == Blocked{"overlay-needs-choice"} : Pick}
def preserved_optional_cannot_erase_fallback(full,owner,default_enabled):
  {==}

law missing_representation_is_incomplete:
  for full: Bool
  {complete(Unacquired{},full) == "materialization" : String}
def missing_representation_is_incomplete(full):
  {==}

law invalid_origin_is_not_complete:
  for observed: Bool
  for full: Bool
  {complete(Download{observed,False{}},full) == "invalid-reference" : String}
def invalid_origin_is_not_complete(observed,full):
  {==}

def main() -> IO(Unit):
  IO.print("Layer choice and representation completion after independent input admission.")
