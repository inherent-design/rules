import Base

# Opaque observed signature/data labels. Zero=absent; not a Cargo hash codec.
type FState is Data:
  FState{script_valid: Bool,basis: Nat,generated: Nat,rust_valid: Bool,binary: Nat,macro_value: Nat,runs: Nat}
type FOut is Data:
  FOut{code: Nat,ran: Bool,reported: Bool,fresh: Nat,state: FState}
def needs(script_valid: Bool,basis: Nat,wanted: Nat) -> Bool:
  Bool.or(Bool.not(script_valid),Bool.not(Nat.is_eq(basis,wanted)))
def rust_phase(+ran: Bool,+request_basis: Nat,+macro_value: Nat,+generated: Nat,rust_valid: Bool,+binary: Nat,+old_macro: Nat,+runs: Nat) -> FOut:
  dirty=Bool.or(ran,Bool.or(Bool.not(rust_valid),Bool.or(Bool.not(Nat.is_eq(binary,generated)),Bool.not(Nat.is_eq(old_macro,macro_value)))))
  Bool.pick(FOut,Nat.is_eq(generated,0n),FOut{101n,ran,True{},2n,FState{True{},request_basis,generated,False{},binary,old_macro,runs}},
    FOut{0n,ran,True{},Bool.pick(Nat,dirty,0n,1n),FState{True{},request_basis,generated,True{},generated,macro_value,runs}})
def after_decision(+ran: Bool,old_basis: Nat,request_basis: Nat,+generated: Nat,rust_valid: Bool,+binary: Nat,+old_macro: Nat,macro_value: Nat,+runs: Nat,fail: Bool) -> FOut:
  Bool.pick(FOut,Bool.and(ran,fail),FOut{101n,True{},False{},2n,FState{False{},old_basis,generated,False{},binary,old_macro,runs}},
    rust_phase(ran,request_basis,macro_value,generated,rust_valid,binary,old_macro,runs))
def build(s: FState,+request_basis: Nat,data: Nat,macro_value: Nat,fail: Bool) -> FOut:
  match s:
    case FState{script_valid,+basis,generated,rust_valid,binary,old_macro,runs}:
      +ran=needs(script_valid,basis,request_basis)
      after_decision(ran,basis,request_basis,Bool.pick(Nat,ran,data,generated),rust_valid,binary,old_macro,macro_value,Nat.add(runs,Bool.pick(Nat,ran,1n,0n)),fail)
def clean(s: FState) -> FState:
  match s:
    case FState{_,_,_,_,_,_,runs}: FState{False{},0n,0n,False{},0n,0n,runs}
def evaluate(+s: FState,action: Nat,basis: Nat,data: Nat,macro_value: Nat,fail: Bool) -> FOut:
  Bool.pick(FOut,Nat.is_eq(action,1n),FOut{0n,False{},False{},2n,clean(s)},build(s,basis,data,macro_value,fail))
def render(o: FOut) -> String:
  match o:
    case FOut{code,ran,reported,fresh,FState{sv,basis,generated,rv,binary,macro_value,runs}}:
      Nat.show(code) ++ "/" ++ Bool.pick(String,ran,"1","0") ++ "/" ++ Bool.pick(String,reported,"1","0") ++ "/" ++ Nat.show(fresh) ++ "/" ++ Bool.pick(String,sv,"1","0") ++ "/" ++ Nat.show(basis) ++ "/" ++ Nat.show(generated) ++ "/" ++ Bool.pick(String,rv,"1","0") ++ "/" ++ Nat.show(binary) ++ "/" ++ Nat.show(macro_value) ++ "/" ++ Nat.show(runs)
def good() -> FState:
  FState{True{},1n,1n,True{},1n,1n,1n}
law cached_message_not_execution:
  {render(build(good(),1n,1n,1n,False{})) == "0/0/1/1/1/1/1/1/1/1/1" : String}
def cached_message_not_execution():
  {==}
law untracked_change_not_in_signature:
  {render(build(good(),1n,2n,1n,False{})) == "0/0/1/1/1/1/1/1/1/1/1" : String}
def untracked_change_not_in_signature():
  {==}
law watched_change_runs:
  {render(build(good(),2n,2n,1n,False{})) == "0/1/1/0/1/2/2/1/2/1/2" : String}
def watched_change_runs():
  {==}
law macro_change_compiles_without_script:
  {render(build(good(),1n,1n,2n,False{})) == "0/0/1/0/1/1/1/1/1/2/1" : String}
def macro_change_compiles_without_script():
  {==}
law script_failure_preserves_old_binary_and_partial_output:
  {render(build(good(),2n,2n,1n,True{})) == "101/1/0/2/0/1/2/0/1/1/2" : String}
def script_failure_preserves_old_binary_and_partial_output():
  {==}
law repeated_failure_runs_again:
  {render(build(FState{False{},1n,2n,False{},1n,1n,2n},2n,2n,1n,True{})) == "101/1/0/2/0/1/2/0/1/1/3" : String}
def repeated_failure_runs_again():
  {==}
law old_basis_does_not_restore_invalidated_trust:
  {render(build(FState{False{},1n,2n,False{},1n,1n,2n},1n,1n,1n,False{})) == "0/1/1/0/1/1/1/1/1/1/3" : String}
def old_basis_does_not_restore_invalidated_trust():
  {==}
law missing_generated_file_can_fail_without_script_run:
  {render(build(FState{True{},1n,0n,True{},1n,1n,1n},1n,1n,1n,False{})) == "101/0/1/2/1/1/0/0/1/1/1" : String}
def missing_generated_file_can_fail_without_script_run():
  {==}
law recompile_does_not_require_different_product:
  {render(build(FState{False{},1n,1n,False{},1n,1n,1n},1n,1n,1n,False{})) == "0/1/1/0/1/1/1/1/1/1/2" : String}
def recompile_does_not_require_different_product():
  {==}
law target_cleanup_preserves_external_history:
  {render(evaluate(good(),1n,0n,0n,0n,False{})) == "0/0/0/2/0/0/0/0/0/0/1" : String}
def target_cleanup_preserves_external_history():
  {==}
def main() -> IO(Unit):
  IO.print("Reuse,physical execution,partial outputs and valid fingerprints are separate.")
