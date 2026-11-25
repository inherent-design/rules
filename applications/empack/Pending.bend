import Base

# Two exact fixture obligations; opaque record labels are study revisions.
# Content tokens: 0=wrong/absent,1=first bytes,2=second bytes.
type PState is Data:
  PState{record: Nat, first: Bool, second: Bool, first_backing: Nat, second_backing: Nat, published: Bool}
type PSupply is Data:
  PSupply{key: Nat, content: Nat}
type PResult is Data:
  PResult{code: Nat, state: PState}
def contains(xs: List<&2,Nat>,+key: Nat) -> Bool:
  match xs:
    case Nil{}: False{}
    case head <> tail: Bool.or(Nat.is_eq(head,key),contains(tail,key))
def valid(files: List<&2,PSupply>,+seen: List<&2,Nat>) -> Bool:
  match files:
    case Nil{}: True{}
    case PSupply{+key,content} <> tail:
      Bool.and(Bool.and(Nat.is_lt(key,2n),Nat.is_eq(content,Nat.add(key,1n))),
        Bool.and(Bool.not(contains(seen,key)),valid(tail,key <> seen)))
def supplied(files: List<&2,PSupply>,+key: Nat) -> Bool:
  match files:
    case Nil{}: False{}
    case PSupply{k,_} <> tail: Bool.or(Nat.is_eq(k,key),supplied(tail,key))
def available(files: List<&2,PSupply>,found: List<&2,Nat>,+key: Nat) -> Bool:
  Bool.or(supplied(files,key),contains(found,Nat.add(key,1n)))
def backing(s: PState) -> Bool:
  match s:
    case PState{_,f,t,bf,bt,_}: Bool.and(Bool.or(Bool.not(f),Nat.is_eq(bf,1n)),Bool.or(Bool.not(t),Nat.is_eq(bt,2n)))
def same_bool(a: Bool,+b: Bool) -> Bool:
  Bool.pick(Bool,a,b,Bool.not(b))
def complete_or_wait(s: PState,+first: Bool,+second: Bool) -> PResult:
  match s:
    case PState{+record,+f,+t,+bf,+bt,p}:
      changed=Bool.or(Bool.not(same_bool(f,first)),Bool.not(same_bool(t,second)))
      next=Bool.pick(Nat,changed,Nat.add(record,1n),record)
      wait : PResult = PResult{5n,PState{next,first,second,Bool.pick(Nat,first,1n,bf),Bool.pick(Nat,second,2n,bt),p}}
      Bool.pick(PResult,Bool.and(first,second),PResult{6n,PState{0n,False{},False{},bf,bt,True{}}},wait)
def acquired(+s: PState,+files: List<&2,PSupply>,+found: List<&2,Nat>) -> PResult:
  match s:
    case PState{record,+f,+t,bf,bt,p}:
      complete_or_wait(PState{record,f,t,bf,bt,p},Bool.or(f,available(files,found,0n)),Bool.or(t,available(files,found,1n)))
def resume(+s: PState,+files: List<&2,PSupply>,found: List<&2,Nat>) -> PResult:
  Bool.pick(PResult,valid(files,[]),Bool.pick(PResult,backing(s),acquired(s,files,found),PResult{4n,s}),PResult{3n,s})
def preview(+s: PState,+files: List<&2,PSupply>) -> PResult:
  Bool.pick(PResult,valid(files,[]),Bool.pick(PResult,backing(s),PResult{1n,s},PResult{4n,s}),PResult{3n,s})
def evaluate(+s: PState,+action: Nat,selected: Nat,+files: List<&2,PSupply>,found: List<&2,Nat>) -> PResult:
  match s:
    case PState{+record,f,t,bf,bt,p}:
      +same : PState = PState{record,f,t,bf,bt,p}
      current=Bool.and(Bool.not(Nat.is_eq(record,0n)),Nat.is_eq(selected,record))
      allowed=Bool.pick(PResult,Nat.is_eq(action,1n),PResult{0n,same},Bool.pick(PResult,Nat.is_eq(action,2n),preview(same,files),resume(same,files,found)))
      Bool.pick(PResult,Nat.is_eq(action,0n),PResult{0n,same},Bool.pick(PResult,current,allowed,PResult{2n,same}))
def render(r: PResult) -> String:
  match r:
    case PResult{code,PState{record,f,t,bf,bt,p}}:
      Nat.show(code) ++ "/" ++ Nat.show(record) ++ "/" ++ Bool.pick(String,f,"1","0") ++ "/" ++ Bool.pick(String,t,"1","0") ++ "/" ++ Nat.show(bf) ++ "/" ++ Nat.show(bt) ++ "/" ++ Bool.pick(String,p,"1","0")
def initial() -> PState:
  PState{1n,False{},False{},0n,0n,False{}}
def retained() -> PState:
  PState{2n,True{},False{},1n,0n,False{}}
law inspect_does_not_verify_bytes:
  {render(evaluate(PState{2n,True{},False{},0n,0n,False{}},0n,2n,[],[])) == "0/2/1/0/0/0/0" : String}
def inspect_does_not_verify_bytes():
  {==}
law preview_does_not_scan_download_directory:
  {render(evaluate(initial(),2n,1n,[],[0n])) == "1/1/0/0/0/0/0" : String}
def preview_does_not_scan_download_directory():
  {==}
law wrong_bytes_refused:
  {render(evaluate(initial(),3n,1n,[PSupply{0n,0n}],[])) == "3/1/0/0/0/0/0" : String}
def wrong_bytes_refused():
  {==}
law unknown_key_refused:
  {render(evaluate(initial(),3n,1n,[PSupply{9n,1n}],[])) == "3/1/0/0/0/0/0" : String}
def unknown_key_refused():
  {==}
law duplicate_key_refused:
  {render(evaluate(initial(),3n,1n,[PSupply{0n,1n},PSupply{0n,1n}],[])) == "3/1/0/0/0/0/0" : String}
def duplicate_key_refused():
  {==}
law partial_is_not_publication:
  {render(evaluate(initial(),3n,1n,[PSupply{0n,1n}],[])) == "5/2/1/0/1/0/0" : String}
def partial_is_not_publication():
  {==}
law old_selector_refused:
  {render(evaluate(retained(),1n,1n,[],[])) == "2/2/1/0/1/0/0" : String}
def old_selector_refused():
  {==}
law corrupt_retained_bytes_refused:
  {render(evaluate(PState{2n,True{},False{},0n,0n,False{}},3n,2n,[],[])) == "4/2/1/0/0/0/0" : String}
def corrupt_retained_bytes_refused():
  {==}
law duplicate_names_do_not_make_distinct_content:
  {available([],[2n,2n],1n) == available([],[2n],1n) : Bool}
def duplicate_names_do_not_make_distinct_content():
  {==}
law publication_keeps_historical_pending_blob:
  {render(evaluate(retained(),3n,2n,[],[0n,1n,2n,2n])) == "6/0/0/0/1/0/1" : String}
def publication_keeps_historical_pending_blob():
  {==}
def main() -> IO(Unit):
  IO.print("Read, verify, retain, select and publish are separate pending facts.")
