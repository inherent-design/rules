namespace ApplicationStudy.EmpackBootstrap

/-- Closed invocation/host profile; decoded admissions are inputs, not a new
    JSON, SemVer, native-path, ACL, HTTP, or cryptographic implementation. -/
structure Input where
  recordOk : Bool
  optionsOk : Bool
  explicit : Bool
  localState : Nat
  cache : Nat
  versionOk : Bool
  protocolOk : Bool
  termination : Nat
  childResult : Int
  deriving Repr
structure Selection where
  engine : Nat
  cacheOpened : Bool
  deriving BEq, DecidableEq, Repr
structure Outcome where
  parent : Int
  engine : Nat
  cacheOpened : Bool
  delegated : Bool
  child : Option Int
  cancellation : Nat
  deriving BEq, DecidableEq, Repr

def selectEngine (r : Input) : Selection :=
  if r.explicit then ⟨1,false⟩ else
  if r.localState == 1 then ⟨2,false⟩ else
  if r.cache == 1 then ⟨3,true⟩ else ⟨0,true⟩
def failed (code : Int) (s : Selection := ⟨0,false⟩) : Outcome :=
  ⟨code,s.engine,s.cacheOpened,false,none,0⟩
def finish (s : Selection) (termination : Nat) (result : Int) : Outcome :=
  if termination == 2 then ⟨-9,s.engine,s.cacheOpened,true,some 6,2⟩ else
  ⟨result,s.engine,s.cacheOpened,true,some result,if termination == 1 then 1 else 0⟩
def evaluate (r : Input) : Outcome :=
  if !r.recordOk then failed 1 else
  if !r.optionsOk then failed 2 else
  let chosen := selectEngine r
  if chosen.engine == 0 || !r.versionOk || !r.protocolOk then failed 1 chosen
  else finish chosen r.termination r.childResult

/-- Probe responses are self-report/capability checks within an already selected
    executable trust boundary. They do not authenticate arbitrary local code. -/
def releaseMatch (expected actual : String) (development : Bool) : Bool :=
  actual == expected || (development && actual == "0.0.0-dev")
def peerAdmitted (expected received : String) : Bool := expected == received

theorem explicit_engine_does_not_fall_back (r : Input) (h : r.explicit = true) :
    selectEngine r = ⟨1,false⟩ := by simp [selectEngine,h]
theorem matching_local_bypasses_cache (r : Input) (h : r.explicit = false) (hl : r.localState = 1) :
    selectEngine r = ⟨2,false⟩ := by simp [selectEngine,h,hl]
theorem rejected_local_can_use_admitted_cache (r : Input) (h : r.explicit = false)
    (hl : r.localState ≠ 1) (hc : r.cache = 1) : selectEngine r = ⟨3,true⟩ := by simp [selectEngine,h,hl,hc]
theorem missing_offline_cache_still_opens_coordination :
    selectEngine ⟨true,true,false,0,0,true,true,0,0⟩ = ⟨0,true⟩ := rfl
theorem invalid_record_precedes_engine_work (r : Input) (h : r.recordOk = false) :
    evaluate r = failed 1 := by simp [evaluate,h]
theorem invalid_options_do_not_select_engine (r : Input) (h : r.recordOk = true) (ho : r.optionsOk = false) :
    evaluate r = failed 2 := by simp [evaluate,h,ho]
theorem exact_probe_is_case_sensitive : releaseMatch "0.8.8-beta" "0.8.8-BETA" false = false := rfl
theorem development_requires_explicit_policy :
    releaseMatch "0.8.8-beta" "0.0.0-dev" false = false ∧
    releaseMatch "0.8.8-beta" "0.0.0-dev" true = true := by constructor <;> rfl
theorem protocol_refusal_prevents_delegation :
    (evaluate ⟨true,true,true,0,0,true,false,0,0⟩).delegated = false := rfl
theorem cancellation_preserves_returned_child_status (s : Selection) (result : Int) :
    finish s 1 result = ⟨result,s.engine,s.cacheOpened,true,some result,1⟩ := rfl
theorem killed_parent_is_not_child_result (s : Selection) :
    (finish s 2 0).parent = -9 ∧ (finish s 2 0).child = some 6 := by constructor <;> rfl
theorem wrong_peer_does_not_authenticate : peerAdmitted "one-use-token" "wrong" = false := rfl

end ApplicationStudy.EmpackBootstrap
