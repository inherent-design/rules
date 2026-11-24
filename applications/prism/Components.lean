namespace ApplicationStudy.PrismComponents

/-- Rank is admitted by the comparison adapter for selected suggestion strings.
    It is not an exact version identity or a general FlexVer implementation. -/
structure Hint where
  text : String
  rank : Nat
  deriving BEq, ReflBEq, LawfulBEq, DecidableEq, Repr

structure Requirement where
  uid : String
  exact : Option String
  hint : Option Hint
  first : Nat
  deriving BEq, ReflBEq, LawfulBEq, DecidableEq, Repr

structure Component where
  uid : String
  version : String
  dependencyOnly : Bool
  volatile : Bool
  custom : Bool
  disabled : Bool
  important : Bool
  requirements : List Requirement
  deriving Repr

def mergeExact (incoming existing : Option String) : Option (Option String) :=
  match incoming, existing with
  | none, other | other, none => some other
  | some a, some b => if a == b then some (some a) else none

def chooseHint (incoming existing : Option Hint) : Option Hint :=
  match incoming, existing with
  | none, other => other
  | other, none => other
  | some a, some b => if a.rank < b.rank then some b else some a

def compose (incoming existing : Requirement) : Option Requirement :=
  if incoming.uid != existing.uid then none else
  (mergeExact incoming.exact existing.exact).map fun exact =>
    ⟨incoming.uid, exact, chooseHint incoming.hint existing.hint, min incoming.first existing.first⟩

structure Gathered where
  ok : Bool
  requirements : List Requirement
  deriving Repr

def insertRequirement (state : Gathered) (req : Requirement) : Gathered :=
  match state.requirements.find? (fun old => old.uid == req.uid) with
  | none => {state with requirements := state.requirements ++ [req]}
  | some old => match compose req old with
    | none => {state with ok := false}
    | some combined => {state with requirements :=
        (state.requirements.filter fun item => item.uid != req.uid) ++ [combined]}

def gather (components : List Component) : Gathered :=
  let state := components.zipIdx.foldl (fun acc pair =>
    pair.1.requirements.foldl (fun out req => insertRequirement out {req with first := pair.2}) acc) ⟨true, []⟩
  {state with requirements := state.requirements.mergeSort (fun a b => decide (a.uid ≤ b.uid))}

def canDisable (c : Component) : Bool := !c.important && !c.dependencyOnly
def enabled (c : Component) : Bool := !canDisable c || !c.disabled

def obsolete (c : Component) (requirements : List Requirement) : Bool :=
  c.dependencyOnly && c.volatile && !requirements.any (fun req => req.uid == c.uid)

inductive Change | met | missing | adjust | locked deriving BEq, ReflBEq, LawfulBEq, DecidableEq, Repr

def decideChange (components : List Component) (req : Requirement) : Change :=
  match components.find? (fun c => c.uid == req.uid) with
  | none => .missing
  | some c => match req.exact with
    | none => .met
    | some exact => if c.version == exact then .met else
        if !c.custom && c.dependencyOnly then .adjust else .locked

structure Plan where
  gathered : Gathered
  ok : Option Bool
  removals : List String
  additions : List Requirement
  changes : List Requirement
  deriving Repr

/-- One pass only. Partial lists accompanying failure are observations, not
    executable authority. The caller's removal/reload fixed point is separate. -/
def plan (components : List Component) : Plan :=
  let g := gather components
  if !g.ok then ⟨g, none, [], [], []⟩ else
  ⟨g, some (g.requirements.all fun r => decideChange components r != .locked),
    (components.filter fun c => obsolete c g.requirements).map (·.uid),
    g.requirements.filter (fun r => decideChange components r == .missing),
    g.requirements.filter (fun r => decideChange components r == .adjust)⟩

def fixture (dependencyOnly volatile custom disabled important : Bool) : Component :=
  ⟨"target", "old", dependencyOnly, volatile, custom, disabled, important, []⟩

def need : Requirement := ⟨"target", some "new", none, 0⟩

theorem conflicting_exact_strings_refuse (a b : String) (h : a ≠ b) :
    mergeExact (some a) (some b) = none := by simp [mergeExact, h]

theorem unconstrained_preserves_exact (exact : Option String) :
    mergeExact none exact = some exact := by cases exact <;> rfl

theorem rank_tie_chooses_incoming (a b : Hint) (h : a.rank = b.rank) :
    chooseHint (some a) (some b) = some a := by simp [chooseHint, h]

theorem suggestion_composition_need_not_commute :
    chooseHint (some ⟨"1.2+left", 1⟩) (some ⟨"1.2+right", 1⟩) ≠
    chooseHint (some ⟨"1.2+right", 1⟩) (some ⟨"1.2+left", 1⟩) := by decide

theorem equivalent_rank_does_not_merge_exact_spelling :
    mergeExact (some "1.02") (some "1.2") = none := rfl

theorem merged_first_dependee_is_minimum (a b : Nat) :
    (compose ⟨"target", some "v", none, a⟩ ⟨"target", some "v", none, b⟩).map (·.first) =
      some (min a b) := rfl

theorem explicit_selection_is_protected :
    decideChange [fixture false false false false false] need = .locked := rfl

theorem custom_dependency_is_protected :
    decideChange [fixture true false true false false] need = .locked := rfl

theorem noncustom_dependency_can_adjust :
    decideChange [fixture true false false false false] need = .adjust := rfl

theorem nonvolatile_dependency_is_retained (reqs : List Requirement) :
    obsolete (fixture true false false false false) reqs = false := rfl

theorem required_dependency_is_retained :
    obsolete (fixture true true false false false) [need] = false := rfl

theorem important_does_not_prevent_removal_proposal :
    obsolete (fixture true true false false true) [] = true := rfl

theorem dependency_only_flag_cannot_disable :
    enabled (fixture true false false true false) = true := rfl

theorem important_flag_cannot_disable :
    enabled (fixture false false false true true) = true := rfl

theorem activation_is_not_requirement_identity (c : Component) (disabled : Bool) :
    ({c with disabled := disabled}).requirements = c.requirements := rfl

/-- Projected cached field plus one required/conflicting entry in the fixture.
    Metadata availability is supplied by the chosen transition, not inferred
    from the resulting cached list. No readiness authority is represented. -/
structure Cache where
  volatile : Bool
  requiredExact : Option String
  hasConflict : Bool
  notifications : Nat
  deriving BEq, ReflBEq, LawfulBEq, DecidableEq, Repr

/-- Current writer uses cachedVolatile, decoder reads volatile. Selected wire
    has no legacy volatile key. This is not a general component codec. -/
def currentRoundtrip (_writtenVolatile : Bool) : Cache := ⟨false, some "1", true, 0⟩

def missingMetadata (s : Cache) : Cache :=
  {s with requiredExact := none, hasConflict := false, notifications := s.notifications + 1}

def loadedMetadata (s : Cache) (volatile : Bool) (exact : String) : Cache :=
  let changed := s.volatile != volatile || s.requiredExact != some exact || !s.hasConflict
  ⟨volatile, some exact, true, s.notifications + if changed then 1 else 0⟩

theorem cached_volatile_does_not_roundtrip : (currentRoundtrip true).volatile = false := rfl

theorem missing_metadata_keeps_cached_bit (s : Cache) :
    (missingMetadata s).volatile = s.volatile := rfl

theorem missing_metadata_clears_requirement_projection (s : Cache) :
    (missingMetadata s).requiredExact = none := rfl

theorem loaded_metadata_reestablishes_cached_bit (s : Cache) (bit : Bool) (exact : String) :
    (loadedMetadata s bit exact).volatile = bit := rfl

theorem unchanged_metadata_does_not_emit (bit : Bool) (exact : String) (n : Nat) :
    (loadedMetadata ⟨bit, some exact, true, n⟩ bit exact).notifications = n := by simp [loadedMetadata]

/-- Stable one-candidate removal boundary; no whole scheduler or filesystem
    implementation. The source ignores a false remove result and retries. -/
def afterRemoval (pending removed : Bool) : Bool := pending && !removed

structure RemovalFiles where
  record : Bool
  patch : Bool
  jar : Bool
  deriving BEq, ReflBEq, LawfulBEq, DecidableEq, Repr

/-- One local patch and at most one fixture-resolved local JAR. A false
    result preserves the component record, not necessarily all earlier files. -/
def removalAttempt (s : RemovalFiles) (important patchWritable jarWritable : Bool) : RemovalFiles × Bool :=
  if !s.record || important then (s, false) else
  if s.patch && !patchWritable then (s, false) else
  let afterPatch := {s with patch := false}
  if s.jar && !jarWritable then (afterPatch, false) else
  (⟨false, false, false⟩, true)

def repeatedRemoval : Nat → RemovalFiles → Bool → Bool → Bool → RemovalFiles
  | 0, s, _, _, _ => s
  | n + 1, s, important, patchWritable, jarWritable =>
      let next := if s.record then (removalAttempt s important patchWritable jarWritable).1 else s
      repeatedRemoval n next important patchWritable jarWritable

inductive RemovalPrefixResult | prefixComplete | retry | failedRemoval deriving BEq, ReflBEq, LawfulBEq, DecidableEq, Repr

def currentResult (pending removed : Bool) : RemovalPrefixResult :=
  if pending && !removed then .retry else .prefixComplete

def proposedResult (pending removed : Bool) : RemovalPrefixResult :=
  if pending && !removed then .failedRemoval else .prefixComplete

theorem failed_removal_preserves_pending : afterRemoval true false = true := rfl

theorem repeated_false_removal_makes_no_progress :
    afterRemoval (afterRemoval (afterRemoval true false) false) false = true := rfl

theorem successful_removal_clears_pending : afterRemoval true true = false := rfl

/-- Stopping retries does not manufacture removal. -/
theorem proposed_guard_reports_failure_and_preserves_candidate :
    proposedResult true false = .failedRemoval ∧ afterRemoval true false = true := ⟨rfl, rfl⟩

theorem failed_jar_removal_can_follow_patch_deletion :
    removalAttempt ⟨true, true, true⟩ false true false = (⟨true, false, true⟩, false) := rfl

theorem repeating_partial_failure_keeps_partial_effects :
    repeatedRemoval 3 ⟨true, true, true⟩ false true false = ⟨true, false, true⟩ := rfl

end ApplicationStudy.PrismComponents
