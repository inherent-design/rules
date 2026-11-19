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
