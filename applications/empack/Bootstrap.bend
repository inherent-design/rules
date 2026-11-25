import Base

# Closed macOS/offline profiles; not a wire/ACL/HTTP/crypto implementation.
type BChoice is Data:
  BChoice{engine: Nat, cache: Bool}
type BOutcome is Data:
  BOutcome{parent: String, engine: Nat, cache: Bool, delegated: Bool, child: String, cancellation: Nat}
def choose(explicit: Bool,local: Nat,cache: Nat) -> BChoice:
  Bool.pick(BChoice,explicit,BChoice{1n,False{}},
    Bool.pick(BChoice,Nat.is_eq(local,1n),BChoice{2n,False{}},
      Bool.pick(BChoice,Nat.is_eq(cache,1n),BChoice{3n,True{}},BChoice{0n,True{}})))
def failure(code: String,choice: BChoice) -> BOutcome:
  match choice:
    case BChoice{engine,cache}: BOutcome{code,engine,cache,False{},"-",0n}
def finish(choice: BChoice,+termination: Nat,+result: Nat) -> BOutcome:
  match choice:
    case BChoice{+engine,+cache}:
      Bool.pick(BOutcome,Nat.is_eq(termination,2n),BOutcome{"-9",engine,cache,True{},"6",2n},
        BOutcome{Nat.show(result),engine,cache,True{},Nat.show(result),Bool.pick(Nat,Nat.is_eq(termination,1n),1n,0n)})
def after_selection(+choice: BChoice,version: Bool,protocol: Bool,termination: Nat,result: Nat) -> BOutcome:
  match choice:
    case BChoice{+engine,+cache}:
      Bool.pick(BOutcome,Bool.and(Bool.not(Nat.is_eq(engine,0n)),Bool.and(version,protocol)),
        finish(BChoice{engine,cache},termination,result),failure("1",BChoice{engine,cache}))
def evaluate(record: Bool,options: Bool,explicit: Bool,local: Nat,cache: Nat,version: Bool,protocol: Bool,termination: Nat,result: Nat) -> BOutcome:
  Bool.pick(BOutcome,record,Bool.pick(BOutcome,options,
    after_selection(choose(explicit,local,cache),version,protocol,termination,result),failure("2",BChoice{0n,False{}})),
    failure("1",BChoice{0n,False{}}))
def release_match(+expected: String,+actual: String,development: Bool) -> Bool:
  Bool.or(String.eq(expected,actual),Bool.and(development,String.eq(actual,"0.0.0-dev")))
def peer_admitted(expected: String,received: String) -> Bool:
  String.eq(expected,received)
def render(o: BOutcome) -> String:
  match o:
    case BOutcome{parent,engine,cache,delegated,child,cancellation}:
      parent ++ "/" ++ Nat.show(engine) ++ "/" ++ Bool.pick(String,cache,"1","0") ++ "/" ++ Bool.pick(String,delegated,"1","0") ++ "/" ++ child ++ "/" ++ Nat.show(cancellation)
law explicit_has_no_fallback:
  {render(evaluate(True{},True{},True{},1n,1n,False{},True{},0n,0n)) == "1/1/0/0/-/0" : String}
def explicit_has_no_fallback():
  {==}
law distribution_local_bypasses_cache:
  {render(evaluate(True{},True{},False{},1n,1n,True{},True{},0n,0n)) == "0/2/0/1/0/0" : String}
def distribution_local_bypasses_cache():
  {==}
law refused_local_can_use_cache:
  {render(evaluate(True{},True{},False{},2n,1n,True{},True{},0n,0n)) == "0/3/1/1/0/0" : String}
def refused_local_can_use_cache():
  {==}
law offline_failure_can_create_coordination:
  {render(evaluate(True{},True{},False{},0n,0n,True{},True{},0n,0n)) == "1/0/1/0/-/0" : String}
def offline_failure_can_create_coordination():
  {==}
law invalid_file_does_no_engine_work:
  {render(evaluate(False{},True{},True{},0n,0n,True{},True{},0n,0n)) == "1/0/0/0/-/0" : String}
def invalid_file_does_no_engine_work():
  {==}
law invalid_options_do_no_engine_work:
  {render(evaluate(True{},False{},True{},0n,0n,True{},True{},0n,0n)) == "2/0/0/0/-/0" : String}
def invalid_options_do_no_engine_work():
  {==}
law version_match_is_case_sensitive:
  {release_match("0.8.8-beta","0.8.8-BETA",False{}) == False{} : Bool}
def version_match_is_case_sensitive():
  {==}
law protocol_refusal_prevents_delegation:
  {render(evaluate(True{},True{},True{},0n,0n,True{},False{},0n,0n)) == "1/1/0/0/-/0" : String}
def protocol_refusal_prevents_delegation():
  {==}
law cancellation_preserves_child_result:
  {render(evaluate(True{},True{},True{},0n,0n,True{},True{},1n,7n)) == "7/1/0/1/7/1" : String}
def cancellation_preserves_child_result():
  {==}
law killed_parent_and_child_are_distinct:
  {render(evaluate(True{},True{},True{},0n,0n,True{},True{},2n,0n)) == "-9/1/0/1/6/2" : String}
def killed_parent_and_child_are_distinct():
  {==}
law wrong_peer_is_not_admitted:
  {peer_admitted("one-use-token","wrong") == False{} : Bool}
def wrong_peer_is_not_admitted():
  {==}
def main() -> IO(Unit):
  IO.print("Invocation admission,exact engine selection and delegated lifetime are distinct.")
