import Base

# Equality labels are injective only within each recorded field role.
# Canonical entry/member order is admitted; this is not a hash or path codec.
type IdOpt is Data:
  IdNone{}
  IdSome{value: Nat}
type IdObject is Data:
  IdObject{volume: Nat, number: Nat, created: IdOpt, token: IdOpt}
type IdOptionalObject is Data:
  IdAbsent{}
  IdPresent{object: IdObject}
type IdNode is Data:
  IdMissing{}
  IdAncestor{object: IdObject}
  IdFile{object: IdObject, content: Nat, bytes: Nat, readonly: Bool, mode: Nat}
  IdDirectory{object: IdObject, members: List<&2,String>}
type IdEntry is Data:
  IdEntry{path: String, node: IdNode}
type IdSnapshot is Data:
  IdSnapshot{root: IdObject, entries: List<&2,IdEntry>}
type IdAtom is Data:
  IdNumber{negative: Bool, magnitude: Nat}
  IdOther{}
type IdMember is Data:
  IdMember{name: String, array: Bool, atoms: List<&2,IdAtom>}

def opt_equal(a: IdOpt,b: IdOpt) -> Bool:
  match a b:
    case IdNone{} IdNone{}: True{}
    case IdSome{x} IdSome{y}: Nat.is_eq(x,y)
    case _ _: False{}
def durable(a: IdObject,b: IdObject) -> Bool:
  match a b:
    case IdObject{_,_,_,IdSome{x}} IdObject{_,_,_,IdSome{y}}: Nat.is_eq(x,y)
    case _ _: False{}
def live(a: IdObject,b: IdObject) -> Bool:
  match a b:
    case IdObject{v,n,c,t} IdObject{w,m,d,u}:
      Bool.and(Bool.and(Nat.is_eq(v,w),Nat.is_eq(n,m)),Bool.and(opt_equal(c,d),opt_equal(t,u)))
def available(a: IdObject) -> Bool:
  match a:
    case IdObject{_,_,_,IdSome{_}}: True{}
    case _: False{}
def bit(b: Bool) -> String:
  Bool.pick(String,b,"1","0")
def journal_object(+a: IdObject,b: IdOptionalObject) -> String:
  match b:
    case IdAbsent{}: Bool.pick(String,available(a),"1/0","0/-")
    case IdPresent{b}: Bool.pick(String,available(a),"1/" ++ bit(durable(a,b)),"0/-")
def journal(a: IdOptionalObject,b: IdOptionalObject) -> String:
  match a b:
    case IdAbsent{} IdAbsent{}: "1/1"
    case IdAbsent{} IdPresent{_}: "1/0"
    case IdPresent{a} b: journal_object(a,b)
def identity(+a: IdObject,+b: IdObject) -> String:
  bit(live(a,b)) ++ "/" ++ bit(durable(a,b)) ++ "/" ++ journal(IdPresent{a},IdPresent{b})
def strings_equal(a: List<&2,String>,b: List<&2,String>) -> Bool:
  match a b:
    case Nil{} Nil{}: True{}
    case x <> xs y <> ys: Bool.and(String.eq(x,y),strings_equal(xs,ys))
    case _ _: False{}
def object_equal(+a: IdObject,+b: IdObject,projected: Bool) -> Bool:
  Bool.pick(Bool,projected,durable(a,b),live(a,b))
def node_equal(a: IdNode,b: IdNode,+projected: Bool) -> Bool:
  match a b:
    case IdMissing{} IdMissing{}: True{}
    case IdAncestor{x} IdAncestor{y}: object_equal(x,y,projected)
    case IdFile{x,c,n,r,m} IdFile{y,d,k,s,l}:
      Bool.and(object_equal(x,y,projected),Bool.and(Bool.and(Nat.is_eq(c,d),Nat.is_eq(n,k)),
        Bool.and(Bool.not(Bool.xor(r,s)),Nat.is_eq(m,l))))
    case IdDirectory{x,xs} IdDirectory{y,ys}: Bool.and(object_equal(x,y,projected),strings_equal(xs,ys))
    case _ _: False{}
def entries_equal(a: List<&2,IdEntry>,b: List<&2,IdEntry>,+projected: Bool) -> Bool:
  match a b:
    case Nil{} Nil{}: True{}
    case IdEntry{p,x} <> xs IdEntry{q,y} <> ys:
      Bool.and(Bool.and(String.eq(p,q),node_equal(x,y,projected)),entries_equal(xs,ys,projected))
    case _ _: False{}
def node_available(n: IdNode) -> Bool:
  match n:
    case IdMissing{}: True{}
    case IdAncestor{o}: available(o)
    case IdFile{o,_,_,_,_}: available(o)
    case IdDirectory{o,_}: available(o)
def entries_available(xs: List<&2,IdEntry>) -> Bool:
  match xs:
    case Nil{}: True{}
    case IdEntry{_,n} <> tail: Bool.and(node_available(n),entries_available(tail))
def snapshot(a: IdSnapshot,b: IdSnapshot) -> String:
  match a b:
    case IdSnapshot{+x,+xs} IdSnapshot{+y,+ys}:
      +xa=Bool.and(available(x),entries_available(xs))
      +ya=Bool.and(available(y),entries_available(ys))
      equal=Bool.and(durable(x,y),entries_equal(xs,ys,True{}))
      bit(xa) ++ "/" ++ bit(ya) ++ "/" ++ Bool.pick(String,Bool.and(xa,ya),bit(equal),"-") ++
        "/" ++ bit(live(x,y)) ++ "/" ++ bit(entries_equal(xs,ys,False{}))
def atom_byte(a: IdAtom) -> Bool:
  match a:
    case IdNumber{negative,magnitude}: Bool.and(Bool.not(negative),Nat.is_lt(magnitude,256n))
    case IdOther{}: False{}
def atoms_bytes(xs: List<&2,IdAtom>) -> Bool:
  match xs:
    case Nil{}: True{}
    case head <> tail: Bool.and(atom_byte(head),atoms_bytes(tail))
def wire(object: Bool,members: List<&2,IdMember>) -> String:
  match members:
    case IdMember{name,array,+atoms} <> Nil{}:
      bit(Bool.and(object,Bool.and(String.eq(name,"persistent"),Bool.and(array,
        Bool.and(Nat.is_eq(List.length(&2,IdAtom,atoms),32n),atoms_bytes(atoms))))))
    case _: "0"
def association(original: String,selected: String,saved: Nat,observed: IdOpt) -> String:
  match observed:
    case IdNone{}: Bool.pick(String,String.eq(original,selected),"unavailable-error","name-error")
    case IdSome{t}: Bool.pick(String,String.eq(original,selected),bit(Nat.is_eq(saved,t)),"name-error")
def availability(+reason: String) -> String:
  bitvalue=Bool.or(Bool.or(String.eq(reason,"ENOTSUP"),String.eq(reason,"ENOTTY")),
    Bool.or(String.eq(reason,"ENOSYS"),Bool.or(String.eq(reason,"EACCES"),String.eq(reason,"EPERM"))))
  Bool.pick(String,bitvalue,"unavailable","error")

law unavailable_saved_is_not_absent:
  {journal(IdPresent{IdObject{1n,2n,IdNone{},IdNone{}}},IdAbsent{}) == "0/-" : String}
def unavailable_saved_is_not_absent():
  {==}
law absent_pairs_match:
  {journal(IdAbsent{},IdAbsent{}) == "1/1" : String}
def absent_pairs_match():
  {==}
law missing_tokens_do_not_match:
  {durable(IdObject{1n,2n,IdNone{},IdNone{}},IdObject{1n,2n,IdNone{},IdNone{}}) == False{} : Bool}
def missing_tokens_do_not_match():
  {==}
law volume_does_not_enter_durable_comparison:
  {durable(IdObject{1n,2n,IdSome{3n},IdSome{4n}},IdObject{9n,2n,IdSome{3n},IdSome{4n}}) == True{} : Bool}
def volume_does_not_enter_durable_comparison():
  {==}
law volume_enters_live_comparison:
  {live(IdObject{1n,2n,IdSome{3n},IdSome{4n}},IdObject{9n,2n,IdSome{3n},IdSome{4n}}) == False{} : Bool}
def volume_enters_live_comparison():
  {==}
law absent_entry_needs_no_token:
  {node_available(IdMissing{}) == True{} : Bool}
def absent_entry_needs_no_token():
  {==}
law missing_root_disables_projection:
  {snapshot(IdSnapshot{IdObject{1n,2n,IdNone{},IdNone{}},[]},IdSnapshot{IdObject{1n,2n,IdNone{},IdNone{}},[]}) == "0/0/-/1/1" : String}
def missing_root_disables_projection():
  {==}
law wrong_name_precedes_unavailable:
  {association("original","other",1n,IdNone{}) == "name-error" : String}
def wrong_name_precedes_unavailable():
  {==}
law negative_byte_is_invalid:
  {atom_byte(IdNumber{True{},1n}) == False{} : Bool}
def negative_byte_is_invalid():
  {==}
law oversized_byte_is_invalid:
  {atom_byte(IdNumber{False{},256n}) == False{} : Bool}
def oversized_byte_is_invalid():
  {==}
law duplicate_fields_are_invalid:
  {wire(True{},[IdMember{"persistent",True{},[]},IdMember{"persistent",True{},[]}]) == "0" : String}
def duplicate_fields_are_invalid():
  {==}
law io_error_is_not_unavailability:
  {availability("EIO") == "error" : String}
def io_error_is_not_unavailability():
  {==}

def main() -> IO(Unit):
  IO.print("Live identity,durable evidence,wire shape,and structural fingerprint projection.")
