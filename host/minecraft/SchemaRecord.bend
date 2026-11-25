import Base

# Authored API-call subset. Forms0..5 and inputs0..4 are admitted by the DTO.
type RecordResult is Data:
  RecordResult{optional: Bool,defaultPresent: Bool,defaultValue: Nat,success: Bool,present: Bool,value: Nat,encoded: Bool}
def sc_absent(+form: Nat) -> Bool:
  Bool.or(Nat.is_eq(form,1n),Bool.or(Nat.is_eq(form,2n),Nat.is_eq(form,5n)))
def sc_missing(+input: Nat) -> Bool:
  Bool.or(Nat.is_eq(input,0n),Nat.is_eq(input,4n))
def sc_evaluate(+form: Nat,+input: Nat) -> RecordResult:
  +missing=sc_missing(input)
  +success=Bool.and(Bool.not(Nat.is_eq(input,3n)),Bool.or(Bool.not(missing),sc_absent(form)))
  +present=Bool.and(success,Bool.not(Bool.and(Nat.is_eq(form,1n),missing)))
  +value=Bool.pick(Nat,present,Bool.pick(Nat,Nat.is_eq(input,2n),7n,Bool.pick(Nat,Bool.and(Nat.is_eq(form,5n),missing),2n,0n)),0n)
  encoded=Bool.and(present,Bool.and(Bool.not(Bool.and(Nat.is_eq(form,2n),Nat.is_eq(value,0n))),Bool.not(Bool.and(Nat.is_eq(form,5n),Nat.is_eq(value,2n)))))
  RecordResult{Bool.not(Nat.is_eq(form,0n)),Nat.is_eq(form,2n),0n,success,present,value,encoded}

law sc_required_missing:
  {sc_evaluate(0n,0n) == RecordResult{False{},False{},0n,False{},False{},0n,False{}} : RecordResult}
def sc_required_missing():
  {==}
law sc_wrapper_missing:
  {sc_evaluate(1n,0n) == RecordResult{True{},False{},0n,True{},False{},0n,False{}} : RecordResult}
def sc_wrapper_missing():
  {==}
law sc_default_missing:
  {sc_evaluate(2n,0n) == RecordResult{True{},True{},0n,True{},True{},0n,False{}} : RecordResult}
def sc_default_missing():
  {==}
law sc_default_zero:
  {sc_evaluate(2n,1n) == RecordResult{True{},True{},0n,True{},True{},0n,False{}} : RecordResult}
def sc_default_zero():
  {==}
law sc_default_seven:
  {sc_evaluate(2n,2n) == RecordResult{True{},True{},0n,True{},True{},7n,True{}} : RecordResult}
def sc_default_seven():
  {==}
law sc_null_default_requires:
  {sc_evaluate(3n,0n) == RecordResult{True{},False{},0n,False{},False{},0n,False{}} : RecordResult}
def sc_null_default_requires():
  {==}
law sc_map_requires:
  {sc_evaluate(4n,0n) == RecordResult{True{},False{},0n,False{},False{},0n,False{}} : RecordResult}
def sc_map_requires():
  {==}
law sc_map_uses_default:
  {sc_evaluate(5n,0n) == RecordResult{True{},False{},0n,True{},True{},2n,False{}} : RecordResult}
def sc_map_uses_default():
  {==}
law sc_wrong_type_is_not_default:
  {sc_evaluate(2n,3n) == RecordResult{True{},True{},0n,False{},False{},0n,False{}} : RecordResult}
def sc_wrong_type_is_not_default():
  {==}
law sc_null_wrapper_is_empty:
  {sc_evaluate(1n,4n) == RecordResult{True{},False{},0n,True{},False{},0n,False{}} : RecordResult}
def sc_null_wrapper_is_empty():
  {==}
law sc_null_required_refuses:
  {sc_evaluate(0n,4n) == RecordResult{False{},False{},0n,False{},False{},0n,False{}} : RecordResult}
def sc_null_required_refuses():
  {==}
law sc_map_zero_is_not_default:
  {sc_evaluate(5n,1n) == RecordResult{True{},False{},0n,True{},True{},0n,True{}} : RecordResult}
def sc_map_zero_is_not_default():
  {==}
