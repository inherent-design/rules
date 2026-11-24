namespace TerminalStudy

/-- These are independent observations, not a single interactive flag. -/
structure Streams where
  inputTty : Bool
  outputTty : Bool
  errorTty : Bool
  controllingTerminal : Bool
  deriving DecidableEq, Repr

inductive Channel | stdout | stderr deriving DecidableEq, Repr
inductive Payload | human | json | ndjson deriving DecidableEq, Repr
/-- Net change in the observed scope/projection, not proof no syscall occurred. -/
inductive EffectKnowledge | unchanged | changed | unknown deriving DecidableEq, Repr
inductive Completion | completed | failed | interrupted | uncertain deriving DecidableEq, Repr
inductive Next | done | inspectDiagnostic | inspectEffects | inspectRecovery deriving DecidableEq, Repr

structure Effects where
  project : EffectKnowledge
  durable : EffectKnowledge
  cache : EffectKnowledge
  deriving DecidableEq, Repr

structure Report where
  completion : Completion
  effects : Effects
  diagnostic : Bool
  deriving DecidableEq, Repr

/-- An observed nonzero status alone does not populate any effect field. -/
def statusOnlyFailure : Report :=
  ⟨.failed, ⟨.unknown, .unknown, .unknown⟩, false⟩

def next (r : Report) : Next :=
  if r.completion = .uncertain ∨ r.effects.durable = .unknown then .inspectRecovery
  else if r.effects.project ≠ .unchanged then .inspectEffects
  else if r.completion ≠ .completed then .inspectDiagnostic
  else .done

theorem status_does_not_prove_rollback :
    statusOnlyFailure.effects.project = .unknown := rfl

theorem unknown_ownership_requires_inspection (r : Report)
    (h : r.effects.durable = .unknown) : next r = .inspectRecovery := by
  simp [next, h]

theorem observed_partial_effects_survive (r : Report) :
    ({ r with completion := .interrupted } : Report).effects = r.effects := rfl

end TerminalStudy
