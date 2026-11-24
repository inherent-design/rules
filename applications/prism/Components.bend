import Base

# Scalar source projection. Exact identity, admitted suggestion rank and
# actual mutation outcomes are supplied separately by the retained adapter.
type Decision is Data:
  Met{}
  Missing{}
  Adjust{}
  Locked{}

type HintSource is Data:
  NoHint{}
  Incoming{}
  Existing{}

def exact_ok(incoming: Bool, existing: Bool, same: Bool) -> Bool:
  Bool.or(Bool.not(incoming),Bool.or(Bool.not(existing),same))

def can_adjust(custom: Bool, dependency_only: Bool) -> Bool:
  Bool.and(Bool.not(custom),dependency_only)

def mismatch(adjustable: Bool) -> Decision:
  match adjustable:
    case True{}: Adjust{}
    case False{}: Locked{}

def exact_change(has_exact: Bool, same: Bool, adjustable: Bool) -> Decision:
  match has_exact:
    case False{}: Met{}
    case True{}:
      match same:
        case True{}: Met{}
        case False{}: mismatch(adjustable)

def change(present: Bool, has_exact: Bool, same: Bool, adjustable: Bool) -> Decision:
  match present:
    case False{}: Missing{}
    case True{}: exact_change(has_exact,same,adjustable)

def lower_hint(incoming_lower: Bool) -> HintSource:
  match incoming_lower:
    case True{}: Existing{}
    case False{}: Incoming{}

def existing_hint(present: Bool) -> HintSource:
  match present:
    case True{}: Existing{}
    case False{}: NoHint{}

def two_hints(existing: Bool, incoming_lower: Bool) -> HintSource:
  match existing:
    case True{}: lower_hint(incoming_lower)
    case False{}: Incoming{}

def hint_source(incoming: Bool, existing: Bool, incoming_lower: Bool) -> HintSource:
  match incoming:
    case False{}: existing_hint(existing)
    case True{}: two_hints(existing,incoming_lower)

def can_disable(important: Bool, dependency_only: Bool) -> Bool:
  Bool.and(Bool.not(important),Bool.not(dependency_only))

def enabled(important: Bool, dependency_only: Bool, disabled: Bool) -> Bool:
  Bool.or(Bool.or(important,dependency_only),Bool.not(disabled))

def obsolete(dependency_only: Bool, volatile: Bool, required: Bool) -> Bool:
  Bool.and(Bool.and(dependency_only,volatile),Bool.not(required))

def current_cached_volatile(written_cached_bit: Bool, has_legacy_bit: Bool, legacy_bit: Bool) -> Bool:
  Bool.and(has_legacy_bit,legacy_bit)

def after_removal(pending: Bool, succeeded: Bool) -> Bool:
  Bool.and(pending,Bool.not(succeeded))

def patch_removed(important: Bool, patch_writable: Bool) -> Bool:
  Bool.and(Bool.not(important),patch_writable)

def record_removed(important: Bool, patch_writable: Bool, local_jar: Bool, jar_writable: Bool) -> Bool:
  Bool.and(patch_removed(important,patch_writable),Bool.or(Bool.not(local_jar),jar_writable))

law mismatching_exacts_are_not_version_rank_comparison:
  {exact_ok(True{},True{},False{}) == False{} : Bool}
def mismatching_exacts_are_not_version_rank_comparison():
  {==}

law suggestion_tie_chooses_incoming:
  {hint_source(True{},True{},False{}) == Incoming{} : HintSource}
def suggestion_tie_chooses_incoming():
  {==}

law custom_dependency_cannot_adjust:
  {can_adjust(True{},True{}) == False{} : Bool}
def custom_dependency_cannot_adjust():
  {==}

law explicit_component_cannot_adjust:
  {can_adjust(False{},False{}) == False{} : Bool}
def explicit_component_cannot_adjust():
  {==}

law required_component_is_not_obsolete:
  for dependency_only: Bool
  for volatile: Bool
  {obsolete(dependency_only,volatile,True{}) == False{} : Bool}
def required_component_is_not_obsolete(dependency_only,volatile):
  match dependency_only:
    case False{}: {==}
    case True{}:
      match volatile:
        case False{}: {==}
        case True{}: {==}

law dependency_cannot_disable:
  {enabled(False{},True{},True{}) == True{} : Bool}
def dependency_cannot_disable():
  {==}

law cached_bit_is_not_current_decoder_key:
  {current_cached_volatile(True{},False{},False{}) == False{} : Bool}
def cached_bit_is_not_current_decoder_key():
  {==}

law failed_removal_is_still_pending:
  {after_removal(True{},False{}) == True{} : Bool}
def failed_removal_is_still_pending():
  {==}

law partial_jar_refusal_keeps_record:
  {record_removed(False{},True{},True{},False{}) == False{} : Bool}
def partial_jar_refusal_keeps_record():
  {==}

law partial_jar_refusal_does_not_undo_patch:
  {patch_removed(False{},True{}) == True{} : Bool}
def partial_jar_refusal_does_not_undo_patch():
  {==}

def main() -> IO(Unit):
  IO.print("Ordered requirements, protected selections, cached fields and removal outcomes are separate.")
