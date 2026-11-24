import Base

type CSnap is Data:
  CSnap{id: Nat, original: Maybe<&2,Nat>, parent: Maybe<&2,Nat>, fixed: Nat, paths: List<&2,Nat>, tags: List<&2,Nat>, excludes: List<&2,Nat>, ignored: Nat}
def contains(+value: Nat,values: List<&2,Nat>) -> Bool:
  match values:
    case Nil{}: False{}
    case Con{head, tail}: Bool.or(Nat.is_eq(value,head),contains(value,tail))
def contains_all(+available: List<&2,Nat>,requested: List<&2,Nat>) -> Bool:
  match requested:
    case Nil{}: True{}
    case Con{head, tail}: Bool.and(contains(head,available),contains_all(available,tail))
def count(values: List<&2,Nat>) -> Nat:
  match values:
    case Nil{}: 0n
    case Con{_, tail}: Nat.add(1n,count(tail))
def ordered_same(a: List<&2,Nat>,b: List<&2,Nat>) -> Bool:
  match a b:
    case Nil{} Nil{}: True{}
    case Con{x, xs} Con{y, ys}: Bool.and(Nat.is_eq(x,y),ordered_same(xs,ys))
    case _ _: False{}
def persistent(s: CSnap) -> Nat:
  match s:
    case CSnap{id,original,_,_,_,_,_,_}:
      match original:
        case None{}: id
        case Some{n}: n
def original_indexed(original: Maybe<&2,Nat>,key: Nat) -> Bool:
  match original:
    case None{}: False{}
    case Some{+n}: Bool.and(Bool.not(Nat.is_eq(n,0n)),Nat.is_eq(n,key))
def indexed(s: CSnap,+key: Nat) -> Bool:
  match s:
    case CSnap{id,original,_,_,_,_,_,_}:
      Bool.or(Nat.is_eq(id,key),original_indexed(original,key))
def similar(a: CSnap,b: CSnap) -> Bool:
  match a b:
    case CSnap{_,_,_,af,+ap,+at,ae,_} CSnap{_,_,_,bf,+bp,+bt,be,_}:
      Bool.and(Nat.is_eq(af,bf),Bool.and(Nat.is_eq(count(ap),count(bp)),Bool.and(Nat.is_eq(count(at),count(bt)),Bool.and(ordered_same(ae,be),Bool.and(contains_all(ap,bp),contains_all(at,bt))))))
def skip(+s: CSnap,destination: List<&2,CSnap>) -> Bool:
  match destination:
    case Nil{}: False{}
    case Con{+head, tail}: Bool.or(Bool.and(indexed(head,persistent(s)),similar(head,s)),skip(s,tail))
def persistent_fields(id: Nat,original: Maybe<&2,Nat>) -> Nat:
  match original:
    case None{}: id
    case Some{n}: n
def copied(s: CSnap,id: Nat) -> CSnap:
  match s:
    case CSnap{sid,original,_,fixed,paths,tags,excludes,ignored}: CSnap{id,Some{persistent_fields(sid,original)},None{},fixed,paths,tags,excludes,ignored}
def decision(+s: CSnap,destination: List<&2,CSnap>,accepted: Bool) -> Nat:
  Bool.pick(Nat,accepted,Bool.pick(Nat,skip(s,destination),0n,1n),12n)
def parent_text(value: Maybe<&2,Nat>) -> String:
  match value:
    case None{}: "-"
    case Some{_}: "parent"
def normalized_text(s: CSnap) -> String:
  match s:
    case CSnap{_,Some{origin},parent,fixed,_,_,_,_}: Nat.show(origin) ++ "/" ++ parent_text(parent) ++ "/" ++ Nat.show(fixed)
    case CSnap{_,None{},_,_,_,_,_,_}: "invalid"
def render(+s: CSnap,destination: List<&2,CSnap>,accepted: Bool,id: Nat) -> String:
  Nat.show(decision(s,destination,accepted)) ++ "/" ++ normalized_text(copied(s,id))
def sample(id: Nat,tags: List<&2,Nat>) -> CSnap:
  CSnap{id,None{},None{},1n,[1n],tags,[],1n}

law no_key_precedes_selection:
  {render(sample(1n,[1n]),[],False{},2n) == "12/1/-/1" : String}
def no_key_precedes_selection():
  {==}
law unrelated_origin_needs_copy:
  {decision(sample(1n,[1n]),[sample(2n,[1n])],True{}) == 1n : Nat}
def unrelated_origin_needs_copy():
  {==}
law existing_exact_copy_skips:
  {decision(sample(1n,[1n]),[copied(sample(1n,[1n]),2n)],True{}) == 0n : Nat}
def existing_exact_copy_skips():
  {==}
law changed_tags_need_another_copy:
  {decision(sample(1n,[1n]),[CSnap{2n,Some{1n},None{},1n,[1n],[1n,2n],[],1n}],True{}) == 1n : Nat}
def changed_tags_need_another_copy():
  {==}
law transitive_original_is_preserved:
  {normalized_text(copied(copied(sample(1n,[1n]),2n),3n)) == "1/-/1" : String}
def transitive_original_is_preserved():
  {==}
law duplicate_membership_is_directional:
  {similar(sample(1n,[1n,2n]),sample(2n,[1n,1n])) == True{} : Bool}
def duplicate_membership_is_directional():
  {==}
law reverse_duplicate_membership_differs:
  {similar(sample(1n,[1n,1n]),sample(2n,[1n,2n])) == False{} : Bool}
def reverse_duplicate_membership_differs():
  {==}
