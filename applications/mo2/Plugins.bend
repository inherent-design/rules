import Base

# Per-step kernels. The Lean model separately carries the complete timeline.
def normalized(wanted: Bool, loaded: Bool, forced: Bool, disabled: Bool) -> Bool:
  Bool.or(Bool.or(Bool.and(wanted,Bool.not(disabled)),loaded),forced)
def bulk_value(old: Bool, wanted: Bool, loaded: Bool, forced: Bool, disabled: Bool) -> Bool:
  Bool.pick(Bool,Bool.or(Bool.or(loaded,forced),disabled),old,wanted)
def member(values: List<&2, Nat>, +needle: Nat) -> Bool:
  match values:
    case Nil{}: False{}
    case Con{head,tail}: Bool.or(Nat.is_eq(head,needle),member(tail,needle))
def length(values: List<&2, Nat>) -> Nat:
  match values:
    case Nil{}: 0n
    case Con{head,tail}: (length(tail) + 1n : Nat)
def last_rank(values: List<&2, Nat>, +needle: Nat, +position: Nat, +previous: Maybe<&2, Nat>) -> Maybe<&2, Nat>:
  match values:
    case Nil{}: previous
    case Con{head,tail}: last_rank(tail,needle,(position + 1n : Nat),Bool.pick(Maybe<&2, Nat>,Nat.is_eq(head,needle),Some{position},previous))
def unlisted_before(catalog: List<&2, Nat>, +requested: List<&2, Nat>, +needle: Nat) -> Nat:
  match catalog:
    case Nil{}: 0n
    case Con{+head,tail}: Bool.pick(Nat,Nat.is_eq(head,needle),0n,
      (Bool.pick(Nat,member(requested,head),0n,1n) + unlisted_before(tail,requested,needle) : Nat))
def priority_value(rank: Maybe<&2, Nat>, fallback: Nat) -> Nat:
  match rank:
    case None{}: fallback
    case Some{n}: n
def priority(catalog: List<&2, Nat>, +requested: List<&2, Nat>, +needle: Nat) -> Nat:
  priority_value(last_rank(requested,needle,0n,None{}),(length(requested) + unlisted_before(catalog,requested,needle) : Nat))
def add_rank(rank: Maybe<&2, Nat>, offset: Nat) -> Maybe<&2, Nat>:
  match rank:
    case None{}: None{}
    case Some{n}: Some{(n + offset : Nat)}
def rank_active(ordered: List<&2, Nat>, +enabled: List<&2, Nat>, +needle: Nat) -> Maybe<&2, Nat>:
  match ordered:
    case Nil{}: None{}
    case Con{+head,tail}: Bool.pick(Maybe<&2, Nat>,Nat.is_eq(head,needle),Some{0n},
      add_rank(rank_active(tail,enabled,needle),Bool.pick(Nat,member(enabled,head),1n,0n)))
def load_order(ordered: List<&2, Nat>, +enabled: List<&2, Nat>, +needle: Nat) -> Maybe<&2, Nat>:
  Bool.pick(Maybe<&2, Nat>,member(enabled,needle),rank_active(ordered,enabled,needle),None{})
def missing_enabled(masters: List<&2, Nat>, +enabled: List<&2, Nat>) -> List<&2, Nat>:
  match masters:
    case Nil{}: []
    case Con{+head,+tail}: Bool.pick(List<&2, Nat>,member(enabled,head),missing_enabled(tail,enabled),head<>missing_enabled(tail,enabled))
def missing(masters: List<&2, Nat>, enabled: List<&2, Nat>, active: Bool) -> List<&2, Nat>:
  Bool.pick(List<&2, Nat>,active,missing_enabled(masters,enabled),[])
def enabled_after(+mode: Nat, +old: Bool, +wanted: Bool, matches: Bool, +loaded: Bool, +forced: Bool, +disabled: Bool) -> Bool:
  Bool.pick(Bool,Nat.is_eq(mode,2n),bulk_value(old,wanted,loaded,forced,disabled),
    Bool.pick(Bool,Bool.and(Nat.is_lt(mode,2n),matches),normalized(wanted,loaded,forced,disabled),old))
def notified(+mode: Nat, matches: Bool, +old: Bool, +wanted: Bool, +loaded: Bool, +forced: Bool, +disabled: Bool) -> Bool:
  Bool.pick(Bool,Nat.is_eq(mode,1n),Bool.and(matches,Bool.xor(old,normalized(wanted,loaded,forced,disabled))),
    Bool.and(Bool.and(Nat.is_eq(mode,2n),Bool.not(Bool.or(Bool.or(loaded,forced),disabled))),Bool.xor(old,wanted)))
def write_requests(+mode: Nat, found: Bool, dirty: Bool) -> Nat:
  Bool.pick(Nat,Nat.is_eq(mode,1n),Bool.pick(Nat,found,1n,0n),
    Bool.pick(Nat,Bool.and(Nat.is_eq(mode,2n),dirty),1n,0n))
def show_optional(value: Maybe<&2, Nat>) -> String:
  match value:
    case None{}: "-1"
    case Some{n}: Nat.show(n)
def show_list(values: List<&2, Nat>) -> String:
  match values:
    case Nil{}: ""
    case Con{head,tail}: Nat.show(head) ++ "," ++ show_list(tail)

law loaded_wins:
  for wanted: Bool
  for forced: Bool
  {normalized(wanted,True{},forced,True{}) == True{} : Bool}
def loaded_wins(wanted,forced):
  match wanted:
    case False{}: {==}
    case True{}: {==}
law free_follows_request:
  for +wanted: Bool
  {normalized(wanted,False{},False{},False{}) == wanted : Bool}
def free_follows_request(wanted):
  match wanted:
    case False{}: {==}
    case True{}: {==}
law bulk_preserves_inconsistent_forced:
  {bulk_value(False{},False{},True{},False{},False{}) == False{} : Bool}
def bulk_preserves_inconsistent_forced():
  {==}
law api_has_no_write_request:
  for found: Bool
  for dirty: Bool
  {write_requests(0n,found,dirty) == 0n : Nat}
def api_has_no_write_request(found,dirty):
  {==}
law unchanged_helper_still_requests_write:
  {write_requests(1n,True{},False{}) == 1n : Nat}
def unchanged_helper_still_requests_write():
  {==}
law empty_order_restores_catalog_rank:
  {priority([0n,1n,2n],[],2n) == 2n : Nat}
def empty_order_restores_catalog_rank():
  {==}
law duplicate_consumes_rank:
  {priority([0n,1n,2n],[0n,0n],2n) == 3n : Nat}
def duplicate_consumes_rank():
  {==}
law disabled_has_no_load_index:
  {load_order([1n,0n],[],0n) == None{} : Maybe<&2, Nat>}
def disabled_has_no_load_index():
  {==}
law inactive_clears_missing_masters:
  {missing([4n],[],False{}) == [] : List<&2, Nat>}
def inactive_clears_missing_masters():
  {==}
