import Base

# Complete quiescent host view; no IO, first-error ordering, or write authority.
type RToken is Data:
  RNoToken{}
  RToken{value: Nat}
type RKey is Data:
  RNoKey{}
  RKey{value: String}
type RRecord is Data:
  RMalformed{}
  RRecord{schema: Nat, original: RKey, token: Nat}
type RMarker is Data:
  RAbsent{}
  RUnreadable{}
  RWire{bytes: Nat, decoded: RRecord}
type REntry is Data:
  REntry{name: String, directory: Bool, marker: RMarker, children: List<&2,String>}
type RVerdict is Data:
  RIgnore{}
  RUnresolved{}
  RInvalid{}
  RClaim{name: String}
type RFacts is Data:
  RFacts{invalid: Bool, unresolved: Bool, claims: List<&2,String>}
type RScan is Data:
  RScan{count: Nat, facts: RFacts}

def eligible(+name: String,+suffix: String) -> Bool:
  Bool.and(String.starts_with(name,"project-"),String.ends_with(name,suffix))
def only_initializer_locks(xs: List<&2,String>) -> Bool:
  match xs:
    case Nil{}: True{}
    case head <> tail: Bool.and(String.eq(head,"state.lock"),only_initializer_locks(tail))
def named(original: RKey,name: String) -> Bool:
  match original:
    case RNoKey{}: False{}
    case RKey{old}: String.eq(old,name)
def match_record(+current: String,token: RToken,+name: String,record: RRecord) -> RVerdict:
  match token record:
    case RNoToken{} _: RInvalid{}
    case _ RMalformed{}: RInvalid{}
    case RToken{t} RRecord{schema,original,saved}:
      valid=Bool.and(Nat.is_eq(schema,1n),named(original,name))
      foreign=Bool.pick(RVerdict,String.eq(name,current),RInvalid{},RIgnore{})
      Bool.pick(RVerdict,valid,Bool.pick(RVerdict,Nat.is_eq(t,saved),RClaim{name},foreign),RInvalid{})
def marker_result(+current: String,token: RToken,+name: String,children: List<&2,String>,marker: RMarker) -> RVerdict:
  match marker:
    case RAbsent{}: Bool.pick(RVerdict,Bool.and(String.eq(name,current),only_initializer_locks(children)),RIgnore{},RUnresolved{})
    case RUnreadable{}: RInvalid{}
    case RWire{bytes,record}: Bool.pick(RVerdict,Nat.is_le(bytes,1024n),match_record(current,token,name,record),RInvalid{})
def classify(current: String,token: RToken,e: REntry) -> RVerdict:
  match e:
    case REntry{name,directory,marker,children}:
      Bool.pick(RVerdict,directory,marker_result(current,token,name,children,marker),RInvalid{})
def add(v: RVerdict,f: RFacts) -> RFacts:
  match v f:
    case RIgnore{} facts: facts
    case RInvalid{} RFacts{_,u,cs}: RFacts{True{},u,cs}
    case RUnresolved{} RFacts{i,_,cs}: RFacts{i,True{},cs}
    case RClaim{name} RFacts{i,u,cs}: RFacts{i,u,name <> cs}
def step(current: String,+suffix: String,token: RToken,e: REntry,+facts: RFacts) -> RFacts:
  match e:
    case REntry{+name,dir,marker,children}:
      Bool.pick(RFacts,eligible(name,suffix),add(classify(current,token,REntry{name,dir,marker,children}),facts),facts)
# One pass avoids retaining one evaluator frame per unfiltered entry.
def scan(+current: String,+suffix: String,+token: RToken,entries: List<&2,REntry>,count: Nat,facts: RFacts) -> RScan:
  match entries:
    case Nil{}: RScan{count,facts}
    case head <> tail: scan(current,suffix,token,tail,Nat.add(1n,count),step(current,suffix,token,head,facts))
def within(count: Nat) -> Bool:
  Nat.is_le(count,4096n)
def render_claims(current: String,claims: List<&2,String>) -> String:
  match claims:
    case Nil{}: "1/-/0/" ++ current
    case +only <> Nil{}: "1/" ++ only ++ "/1/" ++ only
    case _: "0/-/-/-"
def render(current: String,count: Nat,root: Nat,f: RFacts) -> String:
  match f:
    case RFacts{invalid,unresolved,claims}:
      valid=Bool.and(Bool.and(Nat.is_eq(root,0n),within(count)),Bool.and(Bool.not(invalid),Bool.not(unresolved)))
      Bool.pick(String,valid,render_claims(current,claims),"0/-/-/-")
def render_scan(current: String,root: Nat,s: RScan) -> String:
  match s:
    case RScan{count,facts}: render(current,count,root,facts)
def evaluate(+current: String,suffix: String,token: RToken,root: Nat,entries: List<&2,REntry>) -> String:
  render_scan(current,root,scan(current,suffix,token,entries,0n,RFacts{False{},False{},[]}))

law empty_has_a_key_without_a_selected_record:
  {evaluate("project-current-x","-x",RToken{1n},0n,[]) == "1/-/0/project-current-x" : String}
def empty_has_a_key_without_a_selected_record():
  {==}
law current_empty_is_not_a_claim:
  {evaluate("project-current-x","-x",RToken{1n},0n,[REntry{"project-current-x",True{},RAbsent{},[]}]) == "1/-/0/project-current-x" : String}
def current_empty_is_not_a_claim():
  {==}
law current_state_lock_is_not_a_claim:
  {evaluate("project-current-x","-x",RToken{1n},0n,[REntry{"project-current-x",True{},RAbsent{},["state.lock"]}]) == "1/-/0/project-current-x" : String}
def current_state_lock_is_not_a_claim():
  {==}
law operation_lock_without_association_refuses:
  {evaluate("project-current-x","-x",RToken{1n},0n,[REntry{"project-current-x",True{},RAbsent{},["operation.lock"]}]) == "0/-/-/-" : String}
def operation_lock_without_association_refuses():
  {==}
law old_empty_is_not_initializer_scratch:
  {evaluate("project-current-x","-x",RToken{1n},0n,[REntry{"project-old-x",True{},RAbsent{},[]}]) == "0/-/-/-" : String}
def old_empty_is_not_initializer_scratch():
  {==}
law selected_old_key_is_preserved:
  {evaluate("project-current-x","-x",RToken{1n},0n,[REntry{"project-old-x",True{},RWire{120n,RRecord{1n,RKey{"project-old-x"},1n}},[]}]) == "1/project-old-x/1/project-old-x" : String}
def selected_old_key_is_preserved():
  {==}
law duplicate_claims_refuse:
  {render("current",2n,0n,RFacts{False{},False{},["old","current"]}) == "0/-/-/-" : String}
def duplicate_claims_refuse():
  {==}
law selected_record_does_not_hide_unresolved_state:
  {render("current",2n,0n,RFacts{False{},True{},["old"]}) == "0/-/-/-" : String}
def selected_record_does_not_hide_unresolved_state():
  {==}
law every_immediate_entry_counts:
  {within(4096n) == True{} : Bool}
def every_immediate_entry_counts():
  {==}
law one_extra_entry_refuses:
  {within(4097n) == False{} : Bool}
def one_extra_entry_refuses():
  {==}
law malformed_is_not_absent:
  {classify("current",RToken{1n},REntry{"current",True{},RWire{100n,RMalformed{}},[]}) == RInvalid{} : RVerdict}
def malformed_is_not_absent():
  {==}
law oversize_is_not_absent:
  {classify("current",RToken{1n},REntry{"current",True{},RWire{1025n,RRecord{1n,RKey{"current"},1n}},[]}) == RInvalid{} : RVerdict}
def oversize_is_not_absent():
  {==}
law unrelated_bad_record_is_skipped:
  {evaluate("project-current-x","-x",RToken{1n},0n,[REntry{"unrelated",False{},RUnreadable{},[]}]) == "1/-/0/project-current-x" : String}
def unrelated_bad_record_is_skipped():
  {==}
law root_replacement_refuses:
  {evaluate("project-current-x","-x",RToken{1n},2n,[]) == "0/-/-/-" : String}
def root_replacement_refuses():
  {==}

def main() -> IO(Unit):
  IO.print("Discovery selection preserves physical association;no recovery or write authority.")
