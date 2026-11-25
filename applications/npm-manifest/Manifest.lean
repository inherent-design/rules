namespace ApplicationStudy.NpmManifest

structure Projected where
  present : Bool
  truthy : Bool
  deriving DecidableEq, Repr

/-- Abstract JSON predicates for the admitted getter. Missing requested fields
    become an empty result object. Singleton arrays use their first value. -/
def project (fieldPresent isArray : Bool) (length : Nat) (leafTruthy : Bool) : Projected :=
  if !fieldPresent then ⟨true, true⟩
  else if isArray then
    if length == 0 then ⟨false, false⟩
    else if length == 1 then ⟨true, leafTruthy⟩
    else ⟨true, true⟩
  else ⟨true, leafTruthy⟩

/-- Current array tag for this profile, whose singleton elements are not arrays. -/
def currentArray (fieldPresent isArray : Bool) (length : Nat) : Bool :=
  fieldPresent && isArray && !(length == 0) && !(length == 1)
def shapeArray (fieldPresent isArray : Bool) : Bool := fieldPresent && isArray

def currentEmission (p : Projected) : Bool := p.present && p.truthy
/-- Proposed display contract only: distinguish absent payload from falsy JSON. -/
def displayCandidate (p : Projected) : Bool := p.present
/-- Separate opt-in query-shape proposal; no singleton/empty-array collapse. -/
def shapeCandidate (fieldPresent isArray : Bool) (_length : Nat) (leafTruthy : Bool) : Projected :=
  if !fieldPresent || isArray then ⟨true,true⟩ else ⟨true,leafTruthy⟩

/-- Versioned producer policy: npm12 explicit JSON keeps field mappings and
    array values; npm11's singleton lookup supplies the unwrapped value. -/
def producer (preserveArrays wrapped fieldPresent isArray : Bool) (length : Nat) (leafTruthy : Bool) : Projected :=
  if wrapped then ⟨true,true⟩
  else if preserveArrays then shapeCandidate fieldPresent isArray length leafTruthy
  else project fieldPresent isArray length leafTruthy

def policyArray (preserveArrays wrapped fieldPresent isArray : Bool) (length : Nat) : Bool :=
  if wrapped then false
  else if preserveArrays then shapeArray fieldPresent isArray
  else currentArray fieldPresent isArray length

def resultWritten (querySucceeded fieldPresent isArray : Bool) (length : Nat) (leafTruthy : Bool) : Bool :=
  querySucceeded && currentEmission (project fieldPresent isArray length leafTruthy)

structure Step where
  valid : Bool
  changes : Bool
  deriving DecidableEq, Repr
structure Effects where
  attempted : Nat
  changedFiles : Nat
  successful : Bool
  deriving DecidableEq, Repr

/-- Semantic validation before each save; admitted writes succeed. Filesystem
    write failure/crash is excluded, so this is not an atomic-I/O model. -/
def execute : List Step → Effects
  | [] => ⟨0,0,true⟩
  | s :: rest =>
    if s.valid then
      let tail := execute rest
      ⟨1 + tail.attempted, (if s.changes then 1 else 0) + tail.changedFiles, tail.successful⟩
    else ⟨1,0,false⟩

def appendCount (count : Nat) : Nat := count + 1

theorem missing_query_has_object : project false false 0 false = ⟨true,true⟩ := by decide
theorem falsy_scalar_lost : currentEmission (project true false 0 false) = false := by decide
theorem truthy_scalar_kept : currentEmission (project true false 0 true) = true := by decide
theorem empty_array_lost : currentEmission (project true true 0 false) = false := by decide
theorem single_array_unwraps_falsy : currentEmission (project true true 1 false) = false := by decide
theorem multi_array_truthy : currentEmission (project true true 2 false) = true := by decide
theorem display_candidate_preserves_falsy : displayCandidate (project true false 0 false) = true := by decide
theorem display_candidate_cannot_restore_empty_array : displayCandidate (project true true 0 false) = false := by decide
theorem shape_candidate_restores_array : displayCandidate (shapeCandidate true true 0 false) = true := by decide
theorem shape_candidate_keeps_scalar_predicate : shapeCandidate true false 0 false = ⟨true,false⟩ := by decide
theorem current_single_array_tag : currentArray true true 1 = false := by decide
theorem valid_prefix_retains_failure (changes : Bool) (rest : List Step)
    (h : (execute rest).successful = false) :
    (execute (⟨true,changes⟩ :: rest)).successful = false := by exact h
theorem candidate_single_array_tag : shapeArray true true = true := by decide
theorem failed_query_has_no_result (present array : Bool) (length : Nat) (truthy : Bool) :
    resultWritten false present array length truthy = false := by rfl
theorem invalid_single_preserves_file (changes : Bool) : execute [⟨false,changes⟩] = ⟨1,0,false⟩ := by rfl
theorem valid_noop : execute [⟨true,false⟩] = ⟨1,0,true⟩ := by decide
theorem workspace_prefix_is_retained : execute [⟨true,true⟩,⟨false,true⟩] = ⟨2,1,false⟩ := by decide
theorem later_workspace_not_attempted (rest : List Step) :
    execute (⟨false,true⟩ :: rest) = ⟨1,0,false⟩ := by rfl
theorem repeated_append_not_idempotent (count : Nat) : appendCount (appendCount count) ≠ appendCount count := by
  exact Nat.succ_ne_self (count + 1)
theorem legacy_policy_unchanged (present array : Bool) (length : Nat) (truthy : Bool) :
    producer false false present array length truthy = project present array length truthy := by rfl
theorem wrapped_json_emitted (preserve present array : Bool) (length : Nat) (truthy : Bool) :
    currentEmission (producer preserve true present array length truthy) = true := by rfl
theorem wrapped_wire_is_object (preserve present array : Bool) (length : Nat) :
    policyArray preserve true present array length = false := by rfl
theorem unwrapped_preserved_single_array : policyArray true false true true 1 = true := by decide

theorem array_retention_alone_not_falsy_fix :
    currentEmission (producer true false true false 0 false) = false := by decide

end ApplicationStudy.NpmManifest
