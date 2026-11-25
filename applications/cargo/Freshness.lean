namespace ApplicationStudy.CargoFreshness

/-- Opaque signature/data labels from a closed observed input catalog. Zero is
    absence, not an empty env string. This is not Cargo's fingerprint encoder. -/
structure State where
  scriptValid : Bool
  basis : Nat
  generated : Nat
  rustValid : Bool
  binary : Nat
  macroValue : Nat
  runs : Nat
  deriving BEq, DecidableEq, Repr
structure Request where
  basis : Nat
  dataValue : Nat
  macroValue : Nat
  fail : Bool
  deriving Repr
structure Outcome where
  code : Nat
  ran : Bool
  reported : Bool
  artifactFresh : Nat
  state : State
  deriving BEq, DecidableEq, Repr

def needsScript (s : State) (r : Request) : Bool := !s.scriptValid || s.basis != r.basis
/-- Dirty work invalidates trust before execution. Partial generated output and
    the previous physical executable survive the controlled script failure. -/
def build (s : State) (r : Request) : Outcome :=
  let ran := needsScript s r
  let generated := if ran then r.dataValue else s.generated
  let runs := s.runs + if ran then 1 else 0
  if ran && r.fail then
    ⟨101,true,false,2,{s with scriptValid := false, generated := generated, rustValid := false, runs := runs}⟩
  else
    let prepared : State := {s with scriptValid := true, basis := r.basis, generated := generated, runs := runs}
    if generated == 0 then ⟨101,ran,true,2,{prepared with rustValid := false}⟩ else
    let dirty := ran || !s.rustValid || s.binary != generated || s.macroValue != r.macroValue
    ⟨0,ran,true,if dirty then 0 else 1,
      {prepared with rustValid := true, binary := generated, macroValue := r.macroValue}⟩
def clean (s : State) : State := ⟨false,0,0,false,0,0,s.runs⟩

def initial : State := ⟨false,0,0,false,0,0,0⟩
def good : State := ⟨true,1,1,true,1,1,1⟩
def same : Request := ⟨1,1,1,false⟩

theorem cold_build_runs_script : (build initial same).ran = true := rfl
theorem cached_message_is_not_physical_execution :
    (build good same).reported = true ∧ (build good same).ran = false := by constructor <;> rfl
theorem untracked_read_does_not_expand_signature :
    build good ⟨1,2,1,false⟩ = ⟨0,false,true,1,good⟩ := rfl
theorem changed_watch_basis_reruns : (build good ⟨2,2,1,false⟩).ran = true := rfl
theorem macro_change_can_compile_without_script :
    (build good ⟨1,1,2,false⟩).ran = false ∧ (build good ⟨1,1,2,false⟩).artifactFresh = 0 := by constructor <;> rfl
theorem failed_script_preserves_old_binary : (build good ⟨2,2,1,true⟩).state.binary = good.binary := rfl
theorem failed_script_keeps_partial_generated_bytes : (build good ⟨2,2,1,true⟩).state.generated = 2 := rfl
theorem failed_script_invalidates_script_and_dependent :
    let after := (build good ⟨2,2,1,true⟩).state
    after.scriptValid = false ∧ after.rustValid = false := by constructor <;> rfl
theorem failure_is_not_a_successful_fingerprint :
    (build (build good ⟨2,2,1,true⟩).state ⟨2,2,1,true⟩).ran = true := rfl
theorem returning_to_prior_basis_still_runs_after_failure :
    (build (build good ⟨2,2,1,true⟩).state same).ran = true := rfl
theorem missing_generated_file_does_not_rerun_script :
    build {good with generated := 0} same = ⟨101,false,true,2,⟨true,1,0,false,1,1,1⟩⟩ := rfl
theorem recompile_can_preserve_semantic_product :
    let invalidated := {good with scriptValid := false, rustValid := false}
    (build invalidated same).artifactFresh = 0 ∧ (build invalidated same).state.binary = good.binary := by constructor <;> rfl
theorem target_cleanup_preserves_external_run_history (s : State) : (clean s).runs = s.runs := rfl

end ApplicationStudy.CargoFreshness
