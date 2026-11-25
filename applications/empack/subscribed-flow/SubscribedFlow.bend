import Base
import ../Channels.bend as C

# Existing channel admission; the successful host commit is a separate premise.
def admitted(+old: Nat,old_payload: Nat,sequence: Nat,payload: Nat,valid: Bool) -> Bool:
  C.admitted(C.Request{Con{1n,Nil{}},True{},True{},True{},Con{C.Signature{1n,True{},True{},valid},Nil{}},C.Binding{1n,1n,1n},C.Binding{1n,1n,1n},True{},True{},sequence,payload,Bool.pick(Maybe<&2,C.Floor>,Nat.is_eq(old,0n),None{},Some{C.Floor{C.Binding{1n,1n,1n},old,old_payload}})})

# 0enroll,1previewA,2observeA,3installA,4playerEdit,5previewB,6observeB,
# 7previewInstallB,8missingInputB,9installB,10checkB,11ensureOld,12rollbackA,
# 13staleA,14badSignature,15checkRollback. One admitted fixture, not arbitrary operations.
def enrolled(op: Nat,prior: Nat) -> Nat:
  Bool.pick(Nat,Nat.is_eq(op,0n),1n,prior)
def floor(+op: Nat,+prior: Nat,+prior_payload: Nat) -> Nat:
  Bool.pick(Nat,Nat.is_eq(op,2n),Bool.pick(Nat,admitted(prior,prior_payload,1n,1n,True{}),1n,prior),
    Bool.pick(Nat,Nat.is_eq(op,6n),Bool.pick(Nat,admitted(prior,prior_payload,2n,2n,True{}),2n,prior),prior))
def floor_payload(+op: Nat,+prior: Nat,+prior_payload: Nat) -> Nat:
  Bool.pick(Nat,Nat.is_eq(op,2n),Bool.pick(Nat,admitted(prior,prior_payload,1n,1n,True{}),1n,prior_payload),
    Bool.pick(Nat,Nat.is_eq(op,6n),Bool.pick(Nat,admitted(prior,prior_payload,2n,2n,True{}),2n,prior_payload),prior_payload))
def installed(+op: Nat,prior: Nat) -> Nat:
  Bool.pick(Nat,Bool.or(Nat.is_eq(op,3n),Nat.is_eq(op,12n)),1n,Bool.pick(Nat,Nat.is_eq(op,9n),2n,prior))
def seed(+op: Nat,prior: Nat) -> Nat:
  Bool.pick(Nat,Nat.is_eq(op,3n),1n,Bool.pick(Nat,Nat.is_eq(op,4n),2n,prior))
def note(op: Nat,prior: Nat) -> Nat:
  Bool.pick(Nat,Nat.is_eq(op,4n),1n,prior)
def exit(+op: Nat,+floor: Nat,+payload: Nat) -> Nat:
  Bool.pick(Nat,Nat.is_eq(op,8n),1n,
    Bool.pick(Nat,Nat.is_eq(op,13n),Bool.pick(Nat,admitted(floor,payload,1n,1n,True{}),0n,1n),
      Bool.pick(Nat,Nat.is_eq(op,14n),Bool.pick(Nat,admitted(floor,payload,2n,2n,False{}),0n,1n),0n)))

law new_offer_admitted:
  {admitted(1n,1n,2n,2n,True{}) == True{} : Bool}
def new_offer_admitted(): {==}
law stale_offer_refused:
  {admitted(2n,2n,1n,1n,True{}) == False{} : Bool}
def stale_offer_refused(): {==}
law forged_offer_refused:
  {admitted(2n,2n,2n,2n,False{}) == False{} : Bool}
def forged_offer_refused(): {==}
law offer_preview_keeps_floor:
  {floor(5n,1n,1n) == 1n : Nat}
def offer_preview_keeps_floor(): {==}
law second_observation_advances:
  {floor(6n,1n,1n) == 2n : Nat}
def second_observation_advances(): {==}
law observation_keeps_installed:
  {installed(6n,1n) == 1n : Nat}
def observation_keeps_installed(): {==}
law failed_input_keeps_floor:
  {floor(8n,2n,2n) == 2n : Nat}
def failed_input_keeps_floor(): {==}
law failed_input_keeps_installed:
  {installed(8n,1n) == 1n : Nat}
def failed_input_keeps_installed(): {==}
law failed_input_nonzero:
  {exit(8n,2n,2n) == 1n : Nat}
def failed_input_nonzero(): {==}
law install_keeps_floor:
  {floor(9n,2n,2n) == 2n : Nat}
def install_keeps_floor(): {==}
law install_advances_completed:
  {installed(9n,1n) == 2n : Nat}
def install_advances_completed(): {==}
law install_keeps_seed:
  {seed(9n,2n) == 2n : Nat}
def install_keeps_seed(): {==}
law ensure_old_keeps_installed:
  {installed(11n,2n) == 2n : Nat}
def ensure_old_keeps_installed(): {==}
law rollback_keeps_floor:
  {floor(12n,2n,2n) == 2n : Nat}
def rollback_keeps_floor(): {==}
law rollback_restores_completed:
  {installed(12n,2n) == 1n : Nat}
def rollback_restores_completed(): {==}
law rollback_keeps_note:
  {note(12n,1n) == 1n : Nat}
def rollback_keeps_note(): {==}
