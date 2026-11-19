import Base

# Project a candidate only when its dependency gate passed.
def publish(ok: Bool, old: Nat, candidate: Nat) -> Nat:
  match ok:
    case False{}:
      old
    case True{}:
      candidate

law refusal_preserves:
  for old: Nat
  for next: Nat
  {publish(False{}, old, next) == old : Nat}

def refusal_preserves(old, next):
  {==}

law coherent_replaces:
  for old: Nat
  for next: Nat
  {publish(True{}, old, next) == next : Nat}

def coherent_replaces(old, next):
  {==}

# The host supplies independent scope/revision, coverage and time observations.
# Nested guards form an intersection; any false witness preserves the old root.
def all(left: Bool, right: Bool) -> Bool:
  match left:
    case True{}:
      right
    case False{}:
      False{}

law grouped_guards:
  for a: Bool
  for b: Bool
  for c: Bool
  {all(all(a, b), c) == all(a, all(b, c)) : Bool}

def grouped_guards(a, b, c):
  match a:
    case False{}:
      {==}
    case True{}:
      {==}

law nested_publish:
  for a: Bool
  for b: Bool
  for +old: Nat
  for candidate: Nat
  {publish(a, old, publish(b, old, candidate)) == publish(all(a, b), old, candidate) : Nat}

def nested_publish(a, b, old, candidate):
  match a:
    case False{}:
      {==}
    case True{}:
      {==}
