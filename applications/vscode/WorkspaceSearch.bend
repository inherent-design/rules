import Base

# Admitted URI identities and independently observed match facts. No general
# glob/regex/URI normalization, file traversal or resource-group preparation.
def append(a: List<&2,String>,b: List<&2,String>) -> List<&2,String>:
  match a:
    case Nil{}: b
    case Con{head,tail}: Con{head,append(tail,b)}
def contains(xs: List<&2,String>,+key: String) -> Bool:
  match xs:
    case Nil{}: False{}
    case Con{head,tail}: Bool.or(String.eq(head,key),contains(tail,key))
def distinct(xs: List<&2,String>) -> Bool:
  match xs:
    case Nil{}: True{}
    case Con{head,+tail}: Bool.and(Bool.not(contains(tail,head)),distinct(tail))
def length(xs: List<&2,String>) -> Nat:
  match xs:
    case Nil{}: 0n
    case Con{_,tail}: 1n+length(tail)
def take(n: Nat,xs: List<&2,String>) -> List<&2,String>:
  match n xs:
    case 0n _: Nil{}
    case 1n+p Nil{}: Nil{}
    case 1n+p Con{head,tail}: Con{head,take(p,tail)}
def drop(n: Nat,xs: List<&2,String>) -> List<&2,String>:
  match n xs:
    case 0n xs: xs
    case 1n+p Nil{}: Nil{}
    case 1n+p Con{_,tail}: drop(p,tail)
def same(a: List<&2,String>,b: List<&2,String>) -> Bool:
  match a b:
    case Nil{} Nil{}: True{}
    case Con{a,arest} Con{b,brest}: Bool.and(String.eq(a,b),same(arest,brest))
    case _ _: False{}
def comma_tail(xs: List<&2,String>) -> String:
  match xs:
    case Nil{}: ""
    case Con{head,tail}: "," ++ head ++ comma_tail(tail)

def comma(xs: List<&2,String>) -> String:
  match xs:
    case Nil{}: ""
    case Con{head,tail}: head ++ comma_tail(tail)

type W is Data:
  W{confirmed: List<&2,String>,pending: Maybe<&2,List<&2,String>>}
type WR is Data:
  WR{accepted: Bool,state: W}
def visible(w: W) -> List<&2,String>:
  match w:
    case W{c,None{}}: c
    case W{_,Some{p}}: p
def has_pending(w: W) -> Bool:
  match w:
    case W{_,None{}}: False{}
    case W{_,Some{_}}: True{}
def confirm(+w: W) -> W:
  W{visible(w),None{}}
def request(+w: W,+start: Nat,+count: Nat,+adds: List<&2,String>) -> WR:
  match w:
    case W{+c,_}:
      +proposed=append(take(start,c),append(adds,drop(Nat.add(start,count),c)))
      invalid=Bool.or(has_pending(w),Bool.or(Nat.is_gt(Nat.add(start,count),length(c)),Bool.or(Bool.and(Nat.is_eq(count,0n),Nat.is_eq(length(adds),0n)),Bool.or(Bool.not(distinct(proposed)),same(proposed,c)))))
      Bool.pick(WR,invalid,WR{False{},w},WR{True{},W{c,Some{proposed}}})
def request_text(r: WR) -> String:
  match r:
    case WR{accepted,+state}: "W|" ++ Bool.pick(String,accepted,"1","0") ++ "|" ++ comma(visible(state)) ++ "|" ++ comma(visible(confirm(state)))

def workspace_text(w: W,start: Nat,count: Nat,adds: List<&2,String>) -> String:
  request_text(request(w,start,count,adds))

type R is Data:
  R{identity: String,root: String,present: Bool,excluded: Bool,provider_match: Bool,open_eligible: Bool,open_match: Bool}
def provider(+roots: List<&2,String>,respect: Bool,r: R) -> Bool:
  match r:
    case R{_,root,present,excluded,_,_,_}: Bool.and(present,Bool.and(contains(roots,root),Bool.or(Bool.not(respect),Bool.not(excluded))))
def file_results(rs: List<&2,R>,+roots: List<&2,String>,+respect: Bool) -> List<&2,String>:
  match rs:
    case Nil{}: Nil{}
    case Con{+r,tail}:
      match r:
        case R{id,_,_,_,_,_,_}:
          +rest=file_results(tail,roots,respect)
          Bool.pick(List<&2,String>,provider(roots,respect,r),Con{id,rest},rest)
# 0 absent,1 disk,2 buffer. Eligible no-match masks disk even when it matches.
def text_origin(+roots: List<&2,String>,respect: Bool,+r: R) -> Nat:
  match r:
    case R{_,_,_,_,disk,open,match_value}:
      Bool.pick(Nat,open,Bool.pick(Nat,match_value,2n,0n),Bool.pick(Nat,Bool.and(provider(roots,respect,r),disk),1n,0n))
def text_results(rs: List<&2,R>,+roots: List<&2,String>,+respect: Bool) -> List<&2,String>:
  match rs:
    case Nil{}: Nil{}
    case Con{+r,tail}:
      match r:
        case R{id,_,_,_,_,_,_}:
          +rest=text_results(tail,roots,respect)
          Bool.pick(List<&2,String>,Nat.is_gt(text_origin(roots,respect,r),0n),Con{id,rest},rest)
def file_query_text(rs: List<&2,R>,roots: List<&2,String>,respect: Bool,cancelled: Bool) -> String:
  "F|" ++ comma(Bool.pick(List<&2,String>,cancelled,[],file_results(rs,roots,respect)))
def current_guard(submitted: Nat,actual: Nat) -> Bool:
  Nat.is_eq(submitted,actual)
def planned_guard(+planned: Nat,+submitted: Nat,actual: Nat) -> Bool:
  Bool.and(Nat.is_eq(planned,submitted),Nat.is_eq(submitted,actual))
type G is Data:
  G{admitted: Bool,effects: List<&2,String>}
type GR is Data:
  GR{accepted: Bool,effects: List<&2,String>}
def add_effects(prefix: List<&2,String>,r: GR) -> GR:
  match r:
    case GR{accepted,effects}: GR{accepted,append(prefix,effects)}
def run_groups(groups: List<&2,G>) -> GR:
  match groups:
    case Nil{}: GR{True{},Nil{}}
    case Con{G{admitted,effects},rest}: Bool.pick(GR,admitted,add_effects(effects,run_groups(rest)),GR{False{},Nil{}})
def group_result_text(r: GR) -> String:
  match r:
    case GR{accepted,effects}: "G|" ++ Bool.pick(String,accepted,"1","0") ++ "|" ++ comma(effects)

def groups_text(groups: List<&2,G>) -> String:
  group_result_text(run_groups(groups))

law pending_is_visible_before_confirmation:
  {visible(W{["a","b"],Some{["a","b","c"]}}) == ["a","b","c"] : List<&2,String>}
def pending_is_visible_before_confirmation(): {==}
law duplicate_uri_is_refused:
  {workspace_text(W{["a","b","c"],None{}},3n,0n,["c"]) == "W|0|a,b,c|a,b,c" : String}
def duplicate_uri_is_refused(): {==}
law tail_add_is_admitted:
  {workspace_text(W{["a","b"],None{}},2n,0n,["c"]) == "W|1|a,b,c|a,b,c" : String}
def tail_add_is_admitted(): {==}
law open_no_match_masks_disk:
  for roots: List<&2,String>
  for respect: Bool
  for id: String
  for root: String
  for present: Bool
  for excluded: Bool
  for disk: Bool
  {text_origin(roots,respect,R{id,root,present,excluded,disk,True{},False{}}) == 0n : Nat}
def open_no_match_masks_disk(roots,respect,id,root,present,excluded,disk): {==}
law open_match_can_lie_outside_provider_roots:
  {text_origin(["a"],False{},R{"outside","",True{},False{},True{},True{},True{}}) == 2n : Nat}
def open_match_can_lie_outside_provider_roots(): {==}
law submission_match_does_not_establish_plan_freshness:
  {Bool.and(current_guard(4n,4n),Bool.not(planned_guard(3n,4n,4n))) == True{} : Bool}
def submission_match_does_not_establish_plan_freshness(): {==}
law failure_retains_prior_group_effects:
  {groups_text([G{True{},["created"]},G{False{},[]},G{True{},["later"]}]) == "G|0|created" : String}
def failure_retains_prior_group_effects(): {==}
law initial_refusal_has_no_later_effects:
  {groups_text([G{False{},[]},G{True{},["later"]}]) == "G|0|" : String}
def initial_refusal_has_no_later_effects(): {==}
law precancelled_query_has_no_results:
  for resources: List<&2,R>
  for roots: List<&2,String>
  for respect: Bool
  {file_query_text(resources,roots,respect,True{}) == "F|" : String}
def precancelled_query_has_no_results(resources,roots,respect): {==}
