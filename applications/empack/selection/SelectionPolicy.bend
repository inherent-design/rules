import Base

# Current-core fixture decisions. 0A/1B/2C/3D; caller checks the profile.
def effective(project: String,root: String,operation: String,has_root: Bool,has_operation: Bool,applies: Bool) -> String:
  Bool.pick(String,has_operation,operation,Bool.pick(String,Bool.and(has_root,applies),root,project))
def valid_pin_preference(pinned: Bool,preference: Bool) -> Bool:
  Bool.not(Bool.and(pinned,preference))
# Research codes: 0ready,1runtime,2occupied,3retained-evidence,4missing,
# 5invalid-pin,6invalid-project. These are not production error codes.
def failure(+key: Nat,held: Bool,+version: Nat,+requested: Bool,+request_key: Nat,request_version: Nat,runtime: Bool,foreign: Bool,evidence_matches: Bool) -> Nat:
  Bool.pick(Nat,runtime,1n,Bool.pick(Nat,foreign,2n,
    Bool.pick(Nat,Bool.and(Nat.is_eq(key,0n),Bool.and(Nat.is_eq(version,1n),Bool.not(evidence_matches))),3n,
      Bool.pick(Nat,Nat.is_eq(key,3n),4n,
        Bool.pick(Nat,Bool.and(requested,Bool.or(Bool.not(Nat.is_eq(request_key,key)),Bool.or(Bool.not(Nat.is_eq(request_key,0n)),Bool.not(Nat.is_eq(request_version,version))))),5n,
          Bool.pick(Nat,Bool.and(held,Bool.and(Nat.is_eq(key,0n),Bool.and(Bool.not(Nat.is_eq(version,1n)),Bool.not(requested)))),6n,0n))))))
def accepted(code: Nat) -> Bool:
  Nat.is_eq(code,0n)
def author_pin(held: Bool,requested: Bool,key: Nat,version: Nat) -> String:
  Bool.pick(String,Bool.and(requested,Nat.is_eq(key,0n)),"Version" ++ Nat.show(version),Bool.pick(String,held,"Version1","automatic"))
def author_preference(held: Bool,requested: Bool,key: Nat) -> String:
  Bool.pick(String,Bool.or(held,Bool.and(requested,Nat.is_eq(key,0n))),"none","stable-only")
def key_name(+key: Nat) -> String:
  Bool.pick(String,Nat.is_eq(key,0n),"a",Bool.pick(String,Nat.is_eq(key,1n),"b",Bool.pick(String,Nat.is_eq(key,2n),"c","d")))
def optional_pin(code: Nat,held: Bool,requested: Bool,key: Nat,version: Nat) -> String:
  Bool.pick(String,accepted(code),"some:" ++ author_pin(held,requested,key,version),"none")
def optional_preference(code: Nat,held: Bool,requested: Bool,key: Nat) -> String:
  Bool.pick(String,accepted(code),"some:" ++ author_preference(held,requested,key),"none")
def selected(code: Nat,version: Nat) -> String:
  Bool.pick(String,accepted(code),"some:" ++ Nat.show(version),"none")
def changed(code: Nat,key: Nat,version: Nat) -> String:
  Bool.pick(String,accepted(code),Bool.pick(String,Nat.is_eq(version,1n),"[]","[\"" ++ key_name(key) ++ "\"]"),"null")
def existing(code: Nat,key: Nat) -> String:
  Bool.pick(String,accepted(code),"[\"" ++ key_name(key) ++ "\"]","null")
def other_intent_preserved(code: Nat) -> String:
  Bool.pick(String,accepted(code),"true","null")
def author_roots(code: Nat) -> String:
  Bool.pick(String,accepted(code),"[\"a\"]","null")
# Source-only aggregate predicate, not a native engine observation.
def assessment_complete(rows: Bool,joint_not_applicable: Bool,joint_validated: Bool,declarations: Bool) -> Bool:
  Bool.and(rows,Bool.or(joint_not_applicable,Bool.and(joint_validated,declarations)))

law operation_wins:
  {effective("prefer-stable","stable-only","any",True{},True{},True{}) == "any" : String}
def operation_wins(): {==}

law unrelated_key_uses_project:
  {effective("prefer-stable","stable-only","",True{},False{},False{}) == "prefer-stable" : String}
def unrelated_key_uses_project(): {==}

law root_wins:
  {effective("prefer-stable","stable-only","",True{},False{},True{}) == "stable-only" : String}
def root_wins(): {==}

law pin_preference_invalid:
  {valid_pin_preference(True{},True{}) == False{} : Bool}
def pin_preference_invalid(): {==}

law automatic_keeps_policy:
  {author_preference(False{},False{},0n) == "stable-only" : String}
def automatic_keeps_policy(): {==}

law exact_pin_clears_preference:
  {author_preference(False{},True{},0n) == "none" : String}
def exact_pin_clears_preference(): {==}

law automatic_does_not_mint_pin:
  {author_pin(False{},False{},0n,2n) == "automatic" : String}
def automatic_does_not_mint_pin(): {==}

law held_needs_review:
  {failure(0n,True{},2n,False{},0n,0n,False{},False{},False{}) == 6n : Nat}
def held_needs_review(): {==}

law reviewed_pin_admitted:
  {failure(0n,True{},2n,True{},0n,2n,False{},False{},False{}) == 0n : Nat}
def reviewed_pin_admitted(): {==}

law mismatched_pin_refused:
  {failure(0n,True{},2n,True{},0n,3n,False{},False{},False{}) == 5n : Nat}
def mismatched_pin_refused(): {==}

law retained_pin_refused:
  {failure(2n,False{},2n,True{},2n,2n,False{},False{},False{}) == 5n : Nat}
def retained_pin_refused(): {==}

law same_pin_needs_matching_evidence:
  {failure(0n,True{},1n,True{},0n,1n,False{},False{},False{}) == 3n : Nat}
def same_pin_needs_matching_evidence(): {==}

law same_pin_matching_admitted:
  {failure(0n,True{},1n,True{},0n,1n,False{},False{},True{}) == 0n : Nat}
def same_pin_matching_admitted(): {==}

law new_is_not_update:
  {failure(3n,False{},2n,False{},0n,0n,False{},False{},False{}) == 4n : Nat}
def new_is_not_update(): {==}

law runtime_is_not_update:
  {failure(0n,False{},2n,False{},0n,0n,True{},False{},False{}) == 1n : Nat}
def runtime_is_not_update(): {==}

law identity_is_not_update:
  {failure(0n,False{},2n,False{},0n,0n,False{},True{},False{}) == 2n : Nat}
def identity_is_not_update(): {==}

law incomplete_rows_stay_incomplete:
  {assessment_complete(False{},False{},True{},True{}) == False{} : Bool}
def incomplete_rows_stay_incomplete(): {==}

law declarations_are_separate:
  {assessment_complete(True{},False{},True{},False{}) == False{} : Bool}
def declarations_are_separate(): {==}
