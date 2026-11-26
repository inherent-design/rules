import Base

def current(auth: Bool,+old: Nat,+next: Nat,doc: Bool) -> Bool:
  Bool.and(auth,Bool.or(Nat.is_lt(old,next),Bool.and(Nat.is_eq(next,old),doc)))
def subscriber(auth: Bool,+old: Nat,+next: Nat,payload: Bool) -> Bool:
  Bool.and(auth,Bool.or(Nat.is_lt(old,next),Bool.and(Nat.is_eq(next,old),payload)))
def proposed(+auth: Bool,+old: Nat,+next: Nat,doc: Bool,payload: Bool) -> Bool:
  Bool.and(current(auth,old,next,doc),Bool.or(Nat.is_lt(old,next),payload))
def word(value: Bool) -> String:
  Bool.pick(String,value,"true","false")
def optional(auth: Bool,value: Bool) -> String:
  Bool.pick(String,auth,word(value),"null")
def render(+auth: Bool,+old: Nat,+next: Nat,+doc: Bool,+payload: Bool) -> String:
  "{\"publisher\":" ++ word(current(auth,old,next,doc)) ++ ",\"subscriber\":" ++ optional(auth,subscriber(auth,old,next,payload)) ++ ",\"proposed\":" ++ word(proposed(auth,old,next,doc,payload)) ++ "}"

def law_unauthenticated_refused() -> Bool:
  Bool.not(current(False{},3n,3n,True{}))
def law_exact_payload_retry() -> Bool:
  subscriber(True{},3n,3n,True{})
def law_semantic_retry_publisher() -> Bool:
  current(True{},3n,3n,True{})
def law_changed_payload_subscriber() -> Bool:
  Bool.not(subscriber(True{},3n,3n,False{}))
def law_proposed_refuses_changed_payload() -> Bool:
  Bool.not(proposed(True{},3n,3n,True{},False{}))
def law_changed_document_refused() -> Bool:
  Bool.not(current(True{},3n,3n,False{}))
def law_advancing_current() -> Bool:
  current(True{},3n,4n,False{})
def law_advancing_subscriber() -> Bool:
  subscriber(True{},3n,4n,False{})
def law_proposed_preserves_exact_retry() -> Bool:
  proposed(True{},3n,3n,True{},True{})
