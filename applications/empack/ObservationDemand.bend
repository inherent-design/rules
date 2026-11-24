import Base
import Ownership.bend as O

type Evidence is Data:
  Unavailable{}
  Absent{}
  Directory{}
  Regular{bytes: Maybe<&2, O.Content>}

type Step is Data:
  PreserveUserNoByteClaim{}
  PrepareAbsentPlan{}
  MissingSource{}
  NeedByteFacts{}
  CompareContent{}
  RejectKind{}
  NeedObservation{}

type Role is Data:
  InstalledDestination{}
  DistributionSource{}

def content_step(bytes: Maybe<&2, O.Content>) -> Step:
  match bytes:
    case None{}: NeedByteFacts{}
    case Some{content}: CompareContent{}

def seed_step(explicit_change: Bool, bytes: Maybe<&2, O.Content>) -> Step:
  match explicit_change:
    case False{}: PreserveUserNoByteClaim{}
    case True{}: content_step(bytes)

def regular_step(policy: O.Policy, explicit_change: Bool, bytes: Maybe<&2, O.Content>) -> Step:
  match policy:
    case O.Seed{}: seed_step(explicit_change, bytes)
    case O.Managed{}: content_step(bytes)

def destination_step(evidence: Evidence, policy: O.Policy, explicit_change: Bool) -> Step:
  match evidence:
    case Unavailable{}: NeedObservation{}
    case Absent{}: PrepareAbsentPlan{}
    case Directory{}: RejectKind{}
    case Regular{bytes}: regular_step(policy, explicit_change, bytes)

def source_step(evidence: Evidence) -> Step:
  match evidence:
    case Unavailable{}: NeedObservation{}
    case Absent{}: MissingSource{}
    case Directory{}: RejectKind{}
    case Regular{bytes}: content_step(bytes)

def next_step(role: Role, evidence: Evidence, policy: O.Policy, explicit_change: Bool) -> Step:
  match role:
    case InstalledDestination{}: destination_step(evidence, policy, explicit_change)
    case DistributionSource{}: source_step(evidence)

def current_byte_gate(size: Nat, maximum: Nat) -> Bool:
  Nat.is_le(size, maximum)

def label(step: Step) -> String:
  match step:
    case PreserveUserNoByteClaim{}: "preserve-no-byte-claim"
    case PrepareAbsentPlan{}: "prepare-absent-plan"
    case MissingSource{}: "missing-source"
    case NeedByteFacts{}: "need-byte-facts"
    case CompareContent{}: "compare-content"
    case RejectKind{}: "reject-kind"
    case NeedObservation{}: "need-observation"

law default_seed_needs_no_byte_facts:
  {next_step(InstalledDestination{}, Regular{None{}}, O.Seed{}, False{}) == PreserveUserNoByteClaim{} : Step}
def default_seed_needs_no_byte_facts():
  {==}

law byte_facts_do_not_change_default_seed:
  for content: O.Content
  {next_step(InstalledDestination{}, Regular{Some{content}}, O.Seed{}, False{}) == PreserveUserNoByteClaim{} : Step}
def byte_facts_do_not_change_default_seed(content):
  {==}

law unknown_is_not_absence:
  for policy: O.Policy
  for explicit_change: Bool
  {destination_step(Unavailable{}, policy, explicit_change) == NeedObservation{} : Step}
def unknown_is_not_absence(policy, explicit_change):
  {==}

law seed_distribution_source_still_needs_bytes:
  {next_step(DistributionSource{}, Regular{None{}}, O.Seed{}, False{}) == NeedByteFacts{} : Step}
def seed_distribution_source_still_needs_bytes():
  {==}

def main() -> IO(Unit):
  IO.print("Proposed observation demand,not native publication authority.")
