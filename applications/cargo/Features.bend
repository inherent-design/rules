import Base

# Closed declaration/role projection, not Cargo's complete feature resolver.
# Feature indices: normal,build,dev,platform,extra,explicit,defaulted,sibling,default.
type Request is Data:
  Request{legacy: Bool, no_default: Bool, all_features: Bool, argument: Nat, workspace: Bool, tests: Bool}
type Edge is Data:
  Normal{}
  Build{}
  Dev{}
  Windows{}
  Sibling{}

def app_defaults(q: Request) -> Bool:
  match q:
    case Request{legacy,n,a,arg,w,t}: Bool.or(Bool.not(n),a)
def sibling_defaults(+q: Request) -> Bool:
  match q:
    case Request{legacy,n,a,arg,w,t}: Bool.and(w,Bool.or(legacy,app_defaults(q)))
def explicit(q: Request) -> Bool:
  match q:
    case Request{legacy,n,a,arg,w,t}: Bool.or(Bool.not(Nat.is_eq(arg,0n)),a)
def admitted(q: Request, host: Bool, e: Edge) -> Bool:
  match q:
    case Request{legacy,n,a,arg,w,t}:
      match e:
        case Normal{}: Bool.or(legacy,Bool.not(host))
        case Build{}: Bool.or(legacy,host)
        case Dev{}: Bool.or(legacy,Bool.and(Bool.not(host),t))
        case Windows{}: legacy
        case Sibling{}: Bool.and(w,Bool.or(legacy,Bool.not(host)))
def declared(e: Edge,+f: Nat) -> Bool:
  match e:
    case Normal{}: Nat.is_eq(f,0n)
    case Build{}: Nat.is_eq(f,1n)
    case Dev{}: Nat.is_eq(f,2n)
    case Windows{}: Nat.is_eq(f,3n)
    case Sibling{}: Bool.or(Nat.is_eq(f,6n),Nat.is_eq(f,8n))
def forwarded(+q: Request,e: Edge,+f: Nat) -> Bool:
  match e:
    case Sibling{}: Bool.and(Nat.is_eq(f,7n),sibling_defaults(q))
    case _:
      Bool.or(Bool.and(Nat.is_eq(f,4n),app_defaults(q)),Bool.and(Nat.is_eq(f,5n),explicit(q)))
def contribution(+q: Request,host: Bool,+e: Edge,+f: Nat) -> Bool:
  Bool.and(admitted(q,host,e),Bool.or(declared(e,f),forwarded(q,e,f)))
def selected(+q: Request,+host: Bool,+f: Nat) -> Bool:
  Bool.or(contribution(q,host,Normal{},f),
    Bool.or(contribution(q,host,Build{},f),
      Bool.or(contribution(q,host,Dev{},f),
        Bool.or(contribution(q,host,Windows{},f),contribution(q,host,Sibling{},f)))))
def weighted(q: Request,host: Bool,f: Nat,weight: Nat) -> Nat:
  Bool.pick(Nat,selected(q,host,f),weight,0n)
def mask(+q: Request,+host: Bool) -> Nat:
  Nat.add(weighted(q,host,0n,1n),Nat.add(weighted(q,host,1n,2n),
    Nat.add(weighted(q,host,2n,4n),Nat.add(weighted(q,host,3n,8n),
      Nat.add(weighted(q,host,4n,16n),Nat.add(weighted(q,host,5n,32n),
        Nat.add(weighted(q,host,6n,64n),Nat.add(weighted(q,host,7n,128n),weighted(q,host,8n,256n)))))))))
def refused(q: Request) -> Bool:
  match q:
    case Request{legacy,n,a,arg,w,t}: Bool.and(legacy,Nat.is_eq(arg,2n))
def render(+q: Request) -> String:
  Bool.pick(String,refused(q),"101,-,-", "0," ++ Nat.show(mask(q,False{})) ++ "," ++ Nat.show(mask(q,True{})))

law dependency_default_is_positive:
  {selected(Request{False{},True{},False{},0n,True{},False{}},False{},8n) == True{} : Bool}
def dependency_default_is_positive():
  {==}
law root_no_default_disables_sibling_forwarding_in_split_context:
  {selected(Request{False{},True{},False{},0n,True{},False{}},False{},7n) == False{} : Bool}
def root_no_default_disables_sibling_forwarding_in_split_context():
  {==}
law legacy_other_root_default_remains:
  {selected(Request{True{},True{},False{},0n,True{},False{}},False{},7n) == True{} : Bool}
def legacy_other_root_default_remains():
  {==}
law explicit_forwarding_reaches_build:
  {selected(Request{False{},True{},False{},1n,False{},False{}},True{},5n) == True{} : Bool}
def explicit_forwarding_reaches_build():
  {==}
law default_forwarding_reaches_build:
  {selected(Request{False{},False{},False{},0n,False{},False{}},True{},4n) == True{} : Bool}
def default_forwarding_reaches_build():
  {==}
law test_contributes_dev_to_normal:
  {selected(Request{False{},True{},False{},0n,False{},True{}},False{},2n) == True{} : Bool}
def test_contributes_dev_to_normal():
  {==}
law test_does_not_contribute_dev_to_build:
  {selected(Request{False{},True{},False{},0n,False{},True{}},True{},2n) == False{} : Bool}
def test_does_not_contribute_dev_to_build():
  {==}
law all_root_features_not_all_library_features:
  {selected(Request{False{},False{},True{},0n,False{},False{}},False{},6n) == False{} : Bool}
def all_root_features_not_all_library_features():
  {==}
law inactive_target_not_admitted_in_split_context:
  for +n: Bool
  for a: Bool
  for arg: Nat
  for w: Bool
  for t: Bool
  for host: Bool
  {admitted(Request{False{},n,a,arg,w,t},host,Windows{}) == False{} : Bool}
def inactive_target_not_admitted_in_split_context(n,a,arg,w,t,host):
  {==}
law qualified_legacy_member_request_refused:
  {refused(Request{True{},True{},False{},2n,False{},False{}}) == True{} : Bool}
def qualified_legacy_member_request_refused():
  {==}

def main() -> IO(Unit):
  IO.print(render(Request{False{},True{},False{},0n,True{},False{}}))
