import Base
def provider_feature(enabled: Bool,client: Bool,+modefite: Nat) -> Nat:
  Bool.pick(Nat,enabled,Bool.pick(Nat,client,
    Bool.pick(Nat,Nat.is_eq(modefite,0n),2n,Bool.pick(Nat,Nat.is_eq(modefite,1n),3n,4n)),1n),0n)
def provider_evaluate(selected: Bool,rotation: Bool,items: Bool,+client: Bool,+modefite: Nat,_polytone: Bool) -> List<&2, Nat>:
  +a = provider_feature(rotation,client,modefite)
  +b = provider_feature(items,client,modefite)
  Bool.pick(List<&2, Nat>,selected,
    Bool.pick(List<&2, Nat>,Bool.or(Nat.is_eq(a,4n),Nat.is_eq(b,4n)),
      [1n,5n,5n,0n,Bool.pick(Nat,Nat.is_eq(a,4n),0n,1n)],
      [0n,a,b,Nat.add(Bool.pick(Nat,Nat.is_eq(a,3n),1n,0n),Bool.pick(Nat,Nat.is_eq(b,3n),6n,0n)),2n]),
    [2n,5n,5n,0n,2n])
law provider_disabled:
  for client: Bool
  for version: Nat
  {provider_feature(False{},client,version) == 0n : Nat}
def provider_disabled(client,version):
  {==}
law provider_wrong_side:
  for version: Nat
  {provider_feature(True{},False{},version) == 1n : Nat}
def provider_wrong_side(version):
  {==}
law provider_missing:
  {provider_feature(True{},True{},0n) == 2n : Nat}
def provider_missing():
  {==}
law provider_exact:
  {provider_feature(True{},True{},1n) == 3n : Nat}
def provider_exact():
  {==}
law provider_peer_not_substitute:
  {provider_evaluate(True{},True{},True{},True{},0n,True{}) == [0n,2n,2n,0n,2n] : List<&2, Nat>}
def provider_peer_not_substitute():
  {==}
law provider_bad_version:
  {provider_evaluate(True{},True{},True{},True{},2n,False{}) == [1n,5n,5n,0n,0n] : List<&2, Nat>}
def provider_bad_version():
  {==}
law provider_bad_but_disabled:
  {provider_evaluate(True{},False{},False{},True{},2n,False{}) == [0n,0n,0n,0n,2n] : List<&2, Nat>}
def provider_bad_but_disabled():
  {==}
law provider_seven_candidates:
  {provider_evaluate(True{},True{},True{},True{},1n,False{}) == [0n,3n,3n,7n,2n] : List<&2, Nat>}
def provider_seven_candidates():
  {==}
