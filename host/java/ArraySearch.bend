import Base

def as_sorted_tail(values: List<&2,Nat>,+previous: Nat) -> Bool:
  match values:
    case Nil{}: True{}
    case Con{+n,rest}: Bool.and(Bool.not(Nat.is_gt(previous,n)),as_sorted_tail(rest,n))
def as_sorted(values: List<&2,Nat>) -> Bool:
  match values:
    case Nil{}: True{}
    case Con{n,rest}: as_sorted_tail(rest,n)
def as_partition_walk(values: List<&2,Nat>,+query: Nat,+cut: Nat,+position: Nat,+strict: Bool) -> Bool:
  match values:
    case Nil{}: True{}
    case Con{+n,rest}:
      left=Bool.pick(Bool,strict,Nat.is_lt(n,query),Bool.not(Nat.is_gt(n,query)))
      current=Bool.pick(Bool,Nat.is_lt(position,cut),left,Nat.is_lt(query,n))
      Bool.and(current,as_partition_walk(rest,query,cut,Nat.add(position,1n),strict))
def as_partition(+values: List<&2,Nat>,query: Nat,+cut: Nat,strict: Bool) -> Bool:
  Bool.and(Bool.not(Nat.is_gt(cut,List.length(&2,Nat,values))),as_partition_walk(values,query,cut,0n,strict))
def as_at(values: List<&2,Nat>,+index: Nat) -> Maybe<&2,Nat>:
  match values:
    case Nil{}: None{}
    case Con{n,rest}: Bool.pick(Maybe<&2,Nat>,Nat.is_eq(index,0n),Some{n},as_at(rest,Nat.sub(index,1n)))
def as_match(value: Maybe<&2,Nat>,query: Nat) -> Bool:
  match value:
    case None{}: False{}
    case Some{n}: Nat.is_eq(n,query)
def as_binary_result(+values: List<&2,Nat>,+query: Nat,found: Bool,+index: Nat) -> Bool:
  Bool.and(as_sorted(values),Bool.pick(Bool,found,as_match(as_at(values,index),query),as_partition(values,query,index,True{})))
def as_binary_floor(+values: List<&2,Nat>,+query: Nat,result: Maybe<&2,Nat>) -> Bool:
  match result:
    case None{}: as_binary_result(values,query,False{},0n)
    case Some{+i}: Bool.or(as_binary_result(values,query,True{},i),as_binary_result(values,query,False{},Nat.add(i,1n)))
def as_upper_result(+values: List<&2,Nat>,query: Nat,result: Maybe<&2,Nat>) -> Bool:
  match result:
    case None{}: as_partition(values,query,0n,False{})
    case Some{+i}: Bool.and(Nat.is_lt(i,List.length(&2,Nat,values)),as_partition(values,query,Nat.add(i,1n),False{}))
def as_upper_floor(+values: List<&2,Nat>,query: Nat,result: Maybe<&2,Nat>) -> Bool:
  Bool.and(as_sorted(values),as_upper_result(values,query,result))

law as_empty_insertion:
  {as_binary_result(Nil{},2n,False{},0n) == True{} : Bool}
def as_empty_insertion():
  {==}
law as_not_found_not_match:
  {as_binary_result(Con{1n,Con{3n,Nil{}}},2n,True{},1n) == False{} : Bool}
def as_not_found_not_match():
  {==}
law as_duplicate_first:
  {as_binary_result(Con{2n,Con{2n,Con{2n,Nil{}}}},2n,True{},0n) == True{} : Bool}
def as_duplicate_first():
  {==}
law as_duplicate_last:
  {as_binary_result(Con{2n,Con{2n,Con{2n,Nil{}}}},2n,True{},2n) == True{} : Bool}
def as_duplicate_last():
  {==}
law as_out_of_range:
  {as_binary_result(Con{2n,Nil{}},2n,True{},1n) == False{} : Bool}
def as_out_of_range():
  {==}
law as_unsorted:
  {as_binary_result(Con{3n,Con{1n,Nil{}}},1n,True{},1n) == False{} : Bool}
def as_unsorted():
  {==}
law as_upper_earlier_tie:
  {as_upper_floor(Con{2n,Con{2n,Con{2n,Nil{}}}},2n,Some{0n}) == False{} : Bool}
def as_upper_earlier_tie():
  {==}
law as_upper_last_tie:
  {as_upper_floor(Con{2n,Con{2n,Con{2n,Nil{}}}},2n,Some{2n}) == True{} : Bool}
def as_upper_last_tie():
  {==}
