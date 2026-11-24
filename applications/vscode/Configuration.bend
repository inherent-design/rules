import Base

# Scalar projection only: null is the present tag0, strings have positive tags.
# Object merge is compared by Lean; opaque tags are not user-facing values.
def prefer(upper: Maybe<&2,Nat>, lower: Maybe<&2,Nat>) -> Maybe<&2,Nat>:
  match upper:
    case None{}: lower
    case Some{value}: Some{value}

def resolve(slots: List<&2,Maybe<&2,Nat>>) -> Maybe<&2,Nat>:
  match slots:
    case Nil{}: None{}
    case Con{head,tail}: prefer(resolve(tail),head)

def label(value: Maybe<&2,Nat>) -> String:
  match value:
    case None{}: "absent"
    case Some{value}: Nat.show(value)

# Current nullish fallback and a distinct proposed presence-preserving wrapper.
def current_global(local_value: Maybe<&2,Nat>, fallback: Maybe<&2,Nat>) -> Maybe<&2,Nat>:
  match local_value:
    case None{}: fallback
    case Some{value}:
      match value:
        case Zero{}: fallback
        case Succ{pred}: Some{Succ{pred}}

law absent_upper_preserves:
  for +lower: Maybe<&2,Nat>
  {prefer(None{},lower) == lower : Maybe<&2,Nat>}
def absent_upper_preserves(lower):
  {==}

law explicit_null_replaces:
  for lower: Maybe<&2,Nat>
  {prefer(Some{0n},lower) == Some{0n} : Maybe<&2,Nat>}
def explicit_null_replaces(lower):
  {==}

law current_wrapper_loses_present_null:
  {current_global(Some{0n},None{}) == None{} : Maybe<&2,Nat>}
def current_wrapper_loses_present_null():
  {==}

law proposed_presence_preserves_null:
  for fallback: Maybe<&2,Nat>
  {prefer(Some{0n},fallback) == Some{0n} : Maybe<&2,Nat>}
def proposed_presence_preserves_null(fallback):
  {==}

def main() -> IO(Unit):
  IO.print("Eight ordered scalar scopes; null is not absence. Object merging is a separate Lean comparison.")
