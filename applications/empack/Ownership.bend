import Base

type Content is Data:
  FileValue{id: Nat, bytes: Nat, readonly: Bool, executable: Bool}
type Policy is Data:
  Managed{}
  Seed{}
type Prior is Data:
  Unowned{}
  Owned{content: Content, policy: Policy}
type Observation is Data:
  Absent{}
  Directory{}
  Regular{content: Content}
type Desired is Data:
  Retire{}
  Incoming{content: Content, policy: Policy}
type Decision is Data:
  Unchanged{}
  Preserve{}
  Create{content: Content}
  Replace{content: Content}
  Remove{}
  UnownedConflict{}
  ModifiedConflict{}
  WrongKind{}
  SeedOwnership{}

def equivalent(left: Content, right: Content, caps: Bool) -> Bool:
  match left right:
    case FileValue{aid, abytes, aro, ax} FileValue{bid, bbytes, bro, bx}:
      Bool.and(Bool.and(Bool.and(Nat.is_eq(aid, bid), Nat.is_eq(abytes, bbytes)), Bool.not(Bool.xor(aro, bro))), Bool.or(Bool.not(caps), Bool.not(Bool.xor(ax, bx))))

def remove_regular(same: Bool) -> Decision:
  Bool.pick(Decision, same, Remove{}, ModifiedConflict{})

def remove_owned(now: Observation, baseline: Content, caps: Bool) -> Decision:
  match now:
    case Absent{}: Unchanged{}
    case Directory{}: WrongKind{}
    case Regular{content}: remove_regular(equivalent(content, baseline, caps))

def retire_policy(policy: Policy, now: Observation, baseline: Content, caps: Bool) -> Decision:
  match policy:
    case Seed{}: Preserve{}
    case Managed{}: remove_owned(now, baseline, caps)

def retire(prior: Prior, now: Observation, caps: Bool) -> Decision:
  match prior:
    case Unowned{}: Preserve{}
    case Owned{content, policy}: retire_policy(policy, now, content, caps)

def seed(now: Observation, next: Content) -> Decision:
  match now:
    case Absent{}: Create{next}
    case Directory{}: WrongKind{}
    case Regular{content}: Preserve{}

def managed_unowned(now: Observation, next: Content) -> Decision:
  match now:
    case Absent{}: Create{next}
    case Directory{}: WrongKind{}
    case Regular{content}: UnownedConflict{}

def managed_previous_seed(now: Observation) -> Decision:
  match now:
    case Directory{}: WrongKind{}
    case Absent{}: SeedOwnership{}
    case Regular{content}: SeedOwnership{}

def managed_regular(same_next: Bool, same_baseline: Bool, next: Content) -> Decision:
  Bool.pick(Decision, same_next, Unchanged{}, Bool.pick(Decision, same_baseline, Replace{next}, ModifiedConflict{}))

def managed_owned(now: Observation, +next: Content, baseline: Content, +caps: Bool) -> Decision:
  match now:
    case Absent{}: Create{next}
    case Directory{}: WrongKind{}
    case Regular{+content}: managed_regular(equivalent(content, next, caps), equivalent(content, baseline, caps), next)

def managed_policy(policy: Policy, now: Observation, next: Content, baseline: Content, caps: Bool) -> Decision:
  match policy:
    case Seed{}: managed_previous_seed(now)
    case Managed{}: managed_owned(now, next, baseline, caps)

def managed(prior: Prior, now: Observation, next: Content, caps: Bool) -> Decision:
  match prior:
    case Unowned{}: managed_unowned(now, next)
    case Owned{content, policy}: managed_policy(policy, now, next, content, caps)

def incoming_policy(policy: Policy, prior: Prior, now: Observation, next: Content, caps: Bool) -> Decision:
  match policy:
    case Seed{}: seed(now, next)
    case Managed{}: managed(prior, now, next, caps)

def plan(desired: Desired, prior: Prior, now: Observation, caps: Bool) -> Decision:
  match desired:
    case Retire{}: retire(prior, now, caps)
    case Incoming{content, policy}: incoming_policy(policy, prior, now, content, caps)

def label(decision: Decision) -> String:
  match decision:
    case Unchanged{}: "unchanged"
    case Preserve{}: "preserve"
    case Create{content}: "create"
    case Replace{content}: "replace"
    case Remove{}: "remove"
    case UnownedConflict{}: "unowned"
    case ModifiedConflict{}: "modified"
    case WrongKind{}: "wrong-kind"
    case SeedOwnership{}: "seed-ownership"

law incoming_seed_preserves_existing:
  for prior: Prior
  for actual: Content
  for next: Content
  for caps: Bool
  {plan(Incoming{next, Seed{}}, prior, Regular{actual}, caps) == Preserve{} : Decision}
def incoming_seed_preserves_existing(prior, actual, next, caps):
  {==}

law absent_seed_is_created:
  for prior: Prior
  for +next: Content
  for caps: Bool
  {plan(Incoming{next, Seed{}}, prior, Absent{}, caps) == Create{next} : Decision}
def absent_seed_is_created(prior, next, caps):
  {==}

law removing_seed_preserves_user_state:
  for old: Content
  for now: Observation
  for caps: Bool
  {plan(Retire{}, Owned{old, Seed{}}, now, caps) == Preserve{} : Decision}
def removing_seed_preserves_user_state(old, now, caps):
  {==}

law unowned_removal_grants_no_deletion:
  for now: Observation
  for caps: Bool
  {plan(Retire{}, Unowned{}, now, caps) == Preserve{} : Decision}
def unowned_removal_grants_no_deletion(now, caps):
  {==}

def main() -> IO(Unit):
  IO.print("Pure current instance-file planner projection;native authority stays with callers.")
