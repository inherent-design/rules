namespace ApplicationStudy.PrismJava

/-- Projection of Setting/OverrideSetting/PassthroughSetting with synchronous
    storage delivery. It does not model the INI backend or object lifetime. -/
structure SettingState where
  passthrough : Bool
  gate : Bool
  globalDefault : String
  globalValue : String
  localValue : Option String
  deriving Repr, BEq, DecidableEq

def effective (s : SettingState) : String :=
  if s.gate then s.localValue.getD s.globalValue else s.globalValue

def defaultValue (s : SettingState) : String :=
  if s.passthrough && !s.gate then s.globalDefault else s.globalValue

inductive Action
  | set (value : String) | global (value : String) | gate (value : Bool) | reset
  deriving Repr

def step (s : SettingState) : Action → SettingState
  | .gate v => { s with gate := v }
  | .global v => { s with globalValue := v }
  | .set v =>
    let nextLocal := if (!s.passthrough || s.gate) && v != effective s then some v else s.localValue
    { s with localValue := nextLocal, globalValue := if s.passthrough then v else s.globalValue }
  | .reset =>
    { s with localValue := if !s.passthrough || s.gate then none else s.localValue
             globalValue := if s.passthrough then s.globalDefault else s.globalValue }

def trace (s : SettingState) : List Action → List SettingState
  | [] => [s]
  | a :: rest => s :: trace (step s a) rest

def settingText (s : SettingState) : String :=
  String.intercalate "|" [s.globalValue, s.localValue.getD "-", effective s, defaultValue s]

structure Metadata where
  version : String
  major : Nat
  architecture : String
  realArchitecture : String
  vendor : String
  deriving Repr, BEq, DecidableEq

def complete (m : Metadata) : Bool :=
  !m.version.isEmpty && !m.architecture.isEmpty && !m.realArchitecture.isEmpty && !m.vendor.isEmpty

structure Input where
  executable : Bool
  checkerAvailable : Bool
  override : Bool
  signatureMatches : Bool
  stored : Metadata
  probe : Nat -- admitted values: 0 error, 1 invalid data, 2 valid
  result : Metadata
  memory : Nat
  ignore : Bool
  majors : List Nat
  deriving Repr

structure Result where
  probed : Bool
  checkSucceeded : Bool
  checkFailed : Bool
  verifySucceeded : Bool
  verifyFailed : Bool
  memoryWarning : Bool
  ignoredMismatch : Bool
  invalidWarning : Bool
  signatureMatches : Bool
  after : Metadata
  localFields : List (Option String)
  deriving Repr

def probeRequired (i : Input) : Bool := !i.signatureMatches || !complete i.stored

/-- Caller order is observed in MinecraftInstance. These methods execute with
    injected result delivery; this is not a real process/launch trace. The
    pipeline fixture starts without local metadata, so effective and global
    metadata coincide after the passthrough writes. -/
def run (i : Input) : Result :=
  let ready := i.executable && i.checkerAvailable
  let probed := ready && probeRequired i
  let write := probed && i.probe == 2
  let success := ready && !(probed && i.probe == 0)
  let after := if write then i.result else i.stored
  let admitted := i.majors.isEmpty || i.majors.contains after.major
  let nextLocal := fun (old value : String) =>
    if write && i.override && value != old then some value else none
  { probed := probed
    checkSucceeded := success
    checkFailed := !success
    verifySucceeded := success && (admitted || i.ignore)
    verifyFailed := success && !(admitted || i.ignore)
    memoryWarning := success && after.architecture == "32" && i.memory > 2048
    ignoredMismatch := success && !admitted && i.ignore
    invalidWarning := probed && i.probe == 1
    signatureMatches := write || i.signatureMatches
    after := after
    localFields := [nextLocal i.stored.version after.version,
      nextLocal i.stored.architecture after.architecture,
      nextLocal i.stored.realArchitecture after.realArchitecture,
      nextLocal i.stored.vendor after.vendor] }

def bit (b : Bool) : String := if b then "1" else "0"

def resultText (r : Result) : String :=
  String.intercalate "|" ([bit r.probed, bit r.checkSucceeded, bit r.checkFailed,
    bit r.checkSucceeded, bit r.verifySucceeded, bit r.verifyFailed,
    bit r.memoryWarning, bit r.ignoredMismatch, bit r.invalidWarning,
    bit r.signatureMatches, toString r.after.major, r.after.version,
    r.after.architecture, r.after.realArchitecture, r.after.vendor] ++
    r.localFields.map (·.getD "-"))

/-- Proposed reporting classification. Historical fields remain available but
    invalid output cannot become fresh runtime evidence merely because the
    current compatibility predicate happened to succeed. -/
def evidence (i : Input) : String :=
  let r := run i
  if !r.checkSucceeded then "unavailable"
  else if r.invalidWarning then "unknown-with-saved-fields"
  else if r.probed then "current-probe" else "cached"

theorem disabled_reads_global (s : SettingState) (h : s.gate = false) :
    effective s = s.globalValue := by simp [effective, h]

theorem absent_override_inherits (s : SettingState) (h : s.localValue = none) :
    effective s = s.globalValue := by simp [effective, h]

theorem override_write_preserves_global (s : SettingState) (v : String)
    (h : s.passthrough = false) : (step s (.set v)).globalValue = s.globalValue := by
  simp [step, h]

theorem passthrough_write_reaches_global (s : SettingState) (v : String)
    (h : s.passthrough = true) : (step s (.set v)).globalValue = v := by
  simp [step, h]

theorem passthrough_disabled_reset_retains_local (s : SettingState)
    (h : s.passthrough = true) (g : s.gate = false) :
    (step s .reset).localValue = s.localValue := by simp [step, h, g]

theorem passthrough_reset_reaches_global (s : SettingState)
    (h : s.passthrough = true) : (step s .reset).globalValue = s.globalDefault := by
  simp [step, h]

theorem equal_write_does_not_pin (s : SettingState) :
    (step s (.set (effective s))).localValue = s.localValue := by simp [step]

theorem gate_only_preserves_values (s : SettingState) (v : Bool) :
    (step s (.gate v)).localValue = s.localValue ∧
    (step s (.gate v)).globalValue = s.globalValue := by constructor <;> rfl

theorem no_executable_no_probe (i : Input) (h : i.executable = false) :
    (run i).probed = false ∧ (run i).checkFailed = true := by simp [run, h]

theorem no_checker_no_probe (i : Input) (h : i.checkerAvailable = false) :
    (run i).probed = false ∧ (run i).checkFailed = true := by simp [run, h]

theorem complete_match_uses_cache (i : Input) (h : i.signatureMatches = true)
    (c : complete i.stored = true) : (run i).probed = false := by
  simp [run, probeRequired, h, c]

theorem incomplete_forces_probe (i : Input) (e : i.executable = true)
    (j : i.checkerAvailable = true) (c : complete i.stored = false) :
    (run i).probed = true := by simp [run, probeRequired, e, j, c]

theorem invalid_preserves_saved_fields (i : Input) (p : i.probe = 1) :
    (run i).after = i.stored := by simp [run, p]

theorem failed_check_does_not_verify (i : Input) (h : (run i).checkSucceeded = false) :
    (run i).verifySucceeded = false ∧ (run i).verifyFailed = false := by
  have hs : (run i).verifySucceeded = ((run i).checkSucceeded &&
      ((i.majors.isEmpty || i.majors.contains (run i).after.major) || i.ignore)) := rfl
  have hf : (run i).verifyFailed = ((run i).checkSucceeded &&
      !((i.majors.isEmpty || i.majors.contains (run i).after.major) || i.ignore)) := rfl
  simp only [hs, hf, h, Bool.false_and, and_self]

def old : Metadata := ⟨"21.0.1", 21, "64", "aarch64", "old-vendor"⟩
def newer : Metadata := ⟨"25.0.1", 25, "64", "aarch64", "fixture-vendor"⟩
def exampleInput : Input := ⟨true, true, true, false, old, 1, newer, 4096, false, [21]⟩

theorem invalid_output_can_pass_using_old_major :
    (run exampleInput).verifySucceeded = true ∧ (run exampleInput).after.major = 21 := by decide

theorem invalid_output_is_not_fresh_evidence :
    evidence exampleInput = "unknown-with-saved-fields" := by decide

theorem memory_warning_is_not_refusal :
    let r := run { exampleInput with signatureMatches := true, stored := { old with architecture := "32" } }
    r.memoryWarning = true ∧ r.verifySucceeded = true := by decide

theorem known_mismatch_can_be_explicitly_ignored :
    let r := run { exampleInput with probe := 2, ignore := true }
    r.ignoredMismatch = true ∧ r.verifySucceeded = true := by decide

theorem no_requirement_does_not_establish_known_version :
    let r := run { exampleInput with stored := { old with version := "", major := 0 }, majors := [] }
    r.verifySucceeded = true ∧ r.after.major = 0 := by decide

end ApplicationStudy.PrismJava
