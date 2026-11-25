import Base
import ../java/ArraySearch.bend as A

def ri_admitted(+values: List<&2,Nat>,+query: Nat,+result: Maybe<&2,Nat>) -> Bool:
  Bool.pick(Bool,Nat.is_lt(List.length(&2,Nat,values),16n),A.as_upper_floor(values,query,result),A.as_binary_floor(values,query,result))

law ri_empty_fallback:
  {ri_admitted(Nil{},2n,None{}) == True{} : Bool}
def ri_empty_fallback():
  {==}
law ri_small_duplicate_last:
  {ri_admitted(Con{2n,Con{2n,Nil{}}},2n,Some{1n}) == True{} : Bool}
def ri_small_duplicate_last():
  {==}
law ri_small_duplicate_earlier:
  {ri_admitted(Con{2n,Con{2n,Nil{}}},2n,Some{0n}) == False{} : Bool}
def ri_small_duplicate_earlier():
  {==}
law ri_small_above:
  {ri_admitted(Con{2n,Con{3n,Nil{}}},4n,Some{1n}) == True{} : Bool}
def ri_small_above():
  {==}
law ri_small_bad_floor:
  {ri_admitted(Con{2n,Con{3n,Nil{}}},4n,Some{0n}) == False{} : Bool}
def ri_small_bad_floor():
  {==}
