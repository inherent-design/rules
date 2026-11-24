import Base

type Origin is Data:
  Orig{id: Nat, loose: Bool, order: Maybe<&2, Nat>}

type Rank is Data:
  Ranked{layer: Nat, value: Nat}

def rank_order(loose: Bool, order: Maybe<&2, Nat>) -> Rank:
  match order:
    case None{}: Ranked{Nat.add(Bool.pick(Nat, loose, 2n, 0n), 1n), 0n}
    case Some{value}: Ranked{Bool.pick(Nat, loose, 2n, 0n), value}

def rank(origin: Origin) -> Rank:
  match origin:
    case Orig{id, loose, order}: rank_order(loose, order)

def compare_rank(a: Rank, b: Rank) -> Bool:
  match a:
    case Ranked{+layer_a, value_a}:
      match b:
        case Ranked{+layer_b, value_b}:
          Bool.or(Nat.is_gt(layer_a, layer_b), Bool.and(Nat.is_eq(layer_a, layer_b), Nat.is_gt(value_a, value_b)))

def outranks(a: Origin, b: Origin) -> Bool:
  compare_rank(rank(a), rank(b))

def choose(preferred: Bool, a: Origin, b: Origin) -> Origin:
  match preferred:
    case True{}: a
    case False{}: b

def pick(+candidate: Origin, best: Maybe<&2, Origin>) -> Origin:
  match best:
    case None{}: candidate
    case Some{+value}: choose(outranks(candidate, value), candidate, value)

def winner(origins: List<&2, Origin>) -> Maybe<&2, Origin>:
  match origins:
    case Nil{}: None{}
    case Con{head, tail}: Some{pick(head, winner(tail))}

def identity(origin: Origin) -> Nat:
  match origin:
    case Orig{id, loose, order}: id

def winner_id(origin: Maybe<&2, Origin>) -> String:
  match origin:
    case None{}: "none"
    case Some{value}: Nat.show(identity(value))

law empty_has_no_winner:
  {winner([]) == None{} : Maybe<&2, Origin>}
def empty_has_no_winner():
  {==}

law sole_candidate_wins:
  for +id: Nat
  for +loose: Bool
  for +order: Maybe<&2, Nat>
  {winner([Orig{id, loose, order}]) == Some{Orig{id, loose, order}} : Maybe<&2, Origin>}
def sole_candidate_wins(id, loose, order):
  {==}

def main() -> IO(Unit):
  IO.print(winner_id(winner([Orig{1n, False{}, Some{2n}}, Orig{2n, True{}, Some{0n}}])))
