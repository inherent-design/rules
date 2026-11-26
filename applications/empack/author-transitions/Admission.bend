import Base
# Bounded supplied-value core fixture, not a provider or native admission oracle.
# phase:0existing-adopt,1initial-adopt,2validate-target;code:0ready,1runtime,2invalid-project.
def failure(+phase: Nat,held: Bool,version: Nat,missing: Bool,runtime_matches: Bool) -> Nat:
  Bool.pick(Nat,Bool.not(runtime_matches),Bool.pick(Nat,Nat.is_eq(phase,0n),1n,2n),
    Bool.pick(Nat,Bool.or(Bool.and(Nat.is_eq(phase,1n),missing),Bool.and(held,Bool.not(Nat.is_eq(version,1n)))),2n,0n))
def error(+code: Nat) -> String:
  Bool.pick(String,Nat.is_eq(code,0n),"null",Bool.pick(String,Nat.is_eq(code,1n),"\"runtime-mismatch\"","\"invalid-project\""))
def author_pin(held: Bool) -> String:
  Bool.pick(String,held,"\"Version1\"","null")
def locked(phase: Nat) -> String:
  Bool.pick(String,Nat.is_eq(phase,1n),"[\"a\",\"b\"]","[\"a\",\"b\",\"c\"]")
def changed(+phase: Nat,version: Nat,code: Nat) -> String:
  Bool.pick(String,Bool.or(Bool.not(Nat.is_eq(code,0n)),Nat.is_eq(phase,2n)),"null",
    Bool.pick(String,Nat.is_eq(phase,1n),"[\"a\",\"b\"]",Bool.pick(String,Nat.is_eq(version,1n),"[]","[\"a\"]")))
def bindings(phase: Nat,code: Nat) -> String:
  Bool.pick(String,Bool.or(Bool.not(Nat.is_eq(code,0n)),Nat.is_eq(phase,2n)),"null","[\"a\",\"b\"]")
def runtime(phase: Nat) -> String:
  Bool.pick(String,Nat.is_eq(phase,2n),"\"1.21.2\"","\"1.21.1\"")
def result(id: String,+phase: Nat,+held: Bool,+version: Nat,missing: Bool,runtime_matches: Bool) -> String:
  +code = failure(phase,held,version,missing,runtime_matches)
  ok = Nat.is_eq(code,0n)
  body = "{\"rootPin\":" ++ author_pin(held) ++ ",\"roots\":[\"a\"],\"locked\":" ++ locked(phase) ++ ",\"selected\":" ++ Nat.show(version) ++ ",\"intentPreserved\":true,\"runtime\":" ++ runtime(phase) ++ ",\"edges\":[\"b\"],\"coverageComplete\":true}"
  "{\"id\":\"" ++ id ++ "\",\"accepted\":" ++ Bool.pick(String,ok,"true","false") ++ ",\"error\":" ++ error(code) ++ ",\"after\":" ++ Bool.pick(String,Nat.is_eq(code,0n),body,"null") ++ ",\"changed\":" ++ changed(phase,version,code) ++ ",\"bindings\":" ++ bindings(phase,code) ++ ",\"inputUnchanged\":true}"

law automatic_adoption_admitted:
  {failure(0n,False{},2n,False{},True{}) == 0n : Nat}
def automatic_adoption_admitted(): {==}
law held_changed_refused:
  {failure(0n,True{},2n,False{},True{}) == 2n : Nat}
def held_changed_refused(): {==}
law held_same_admitted:
  {failure(0n,True{},1n,False{},True{}) == 0n : Nat}
def held_same_admitted(): {==}
law existing_runtime_has_own_failure:
  {failure(0n,True{},2n,False{},False{}) == 1n : Nat}
def existing_runtime_has_own_failure(): {==}
law initial_missing_root_refused:
  {failure(1n,False{},1n,True{},True{}) == 2n : Nat}
def initial_missing_root_refused(): {==}
law initial_authored_pin_preserved:
  {failure(1n,True{},2n,False{},True{}) == 2n : Nat}
def initial_authored_pin_preserved(): {==}
law target_old_runtime_refused:
  {failure(2n,False{},1n,False{},False{}) == 2n : Nat}
def target_old_runtime_refused(): {==}
law target_retagged_held_core_admitted:
  {failure(2n,True{},1n,False{},True{}) == 0n : Nat}
def target_retagged_held_core_admitted(): {==}
law target_changed_pin_refused:
  {failure(2n,True{},2n,False{},True{}) == 2n : Nat}
def target_changed_pin_refused(): {==}
law existing_retains_unlisted:
  {locked(0n) == "[\"a\",\"b\",\"c\"]" : String}
def existing_retains_unlisted(): {==}
law initial_has_only_group:
  {locked(1n) == "[\"a\",\"b\"]" : String}
def initial_has_only_group(): {==}
law unchanged_existing_has_no_changes:
  {changed(0n,1n,0n) == "[]" : String}
def unchanged_existing_has_no_changes(): {==}
law initial_records_group:
  {changed(1n,1n,0n) == "[\"a\",\"b\"]" : String}
def initial_records_group(): {==}
law target_has_no_adoption_plan:
  {bindings(2n,0n) == "null" : String}
def target_has_no_adoption_plan(): {==}
