import Base

def second_suffix(first_file: Bool, second_file: Bool, same_entry: Bool, fresh: Bool) -> Bool:
  Bool.and(Bool.and(Bool.not(fresh), Bool.not(Bool.xor(first_file, second_file))), Bool.not(same_entry))

def first_without_suffix(first_file: Bool, second_file: Bool, +same_entry: Bool, fresh: Bool) -> Bool:
  Bool.pick(Bool, fresh, same_entry, Bool.pick(Bool, first_file, True{}, Bool.pick(Bool, second_file, same_entry, True{})))

def second_without_suffix(first_file: Bool, second_file: Bool, +same_entry: Bool, fresh: Bool) -> Bool:
  Bool.pick(Bool, fresh, True{}, Bool.pick(Bool, first_file, same_entry, Bool.pick(Bool, second_file, True{}, same_entry)))

def memory_first(+first_file: Bool, +second_file: Bool, +same_entry: Bool, +fresh: Bool) -> Bool:
  Bool.pick(Bool, second_suffix(first_file, second_file, same_entry, fresh), True{}, first_without_suffix(first_file, second_file, same_entry, fresh))

def memory_second(+first_file: Bool, +second_file: Bool, +same_entry: Bool, +fresh: Bool) -> Bool:
  Bool.pick(Bool, second_suffix(first_file, second_file, same_entry, fresh), same_entry, second_without_suffix(first_file, second_file, same_entry, fresh))

def stored_first(first_file: Bool, second_file: Bool, +same_entry: Bool, fresh: Bool) -> Bool:
  Bool.pick(Bool, second_suffix(first_file, second_file, same_entry, fresh), True{}, same_entry)

def stored_second(first_file: Bool, second_file: Bool, +same_entry: Bool, fresh: Bool) -> Bool:
  Bool.pick(Bool, second_suffix(first_file, second_file, same_entry, fresh), same_entry, True{})

type HandleBinding is Data:
  HandleRef{file: Bool, entry: Nat}

# Proposed immutable slot, not the current application registry.
def bind_slot(old: Maybe<&2, HandleBinding>, next: HandleBinding) -> Maybe<&2, HandleBinding>:
  match old:
    case None{}: Some{next}
    case Some{value}: Some{value}

law distinct_same_kind_suffix:
  for +kind: Bool
  {second_suffix(kind, kind, False{}, False{}) == True{} : Bool}
def distinct_same_kind_suffix(kind):
  match kind:
    case False{}: {==}
    case True{}: {==}

law occupied_slot_not_rebound:
  for +old: HandleBinding
  for next: HandleBinding
  {bind_slot(Some{old}, next) == Some{old} : Maybe<&2, HandleBinding>}
def occupied_slot_not_rebound(old, next):
  {==}

law empty_slot_is_bound:
  for +next: HandleBinding
  {bind_slot(None{}, next) == Some{next} : Maybe<&2, HandleBinding>}
def empty_slot_is_bound(next):
  {==}

def main() -> IO(Unit):
  IO.print("Two-registration source projection and proposed immutable slot; use retained replay.")
