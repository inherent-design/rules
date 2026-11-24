namespace ApplicationStudy.JsConfiguration

inductive App | npm | pnpm | yarn
  deriving BEq, DecidableEq, Repr
inductive Scope | global | home | project
  deriving BEq, DecidableEq, Repr
inductive Action | read | explain | set | unset
  deriving BEq, DecidableEq, Repr
inductive Source | fallback | global | home | project | environment | command
  deriving BEq, DecidableEq, Repr
structure State where
  global : Option Nat
  home : Option Nat
  project : Option Nat
  deriving BEq, DecidableEq, Repr
structure Context where
  environment : Option Nat
  command : Option Nat
  globalMode : Bool
  customRc : Bool
  fallback : Nat
  deriving Repr
structure Request where
  app : App
  state : State
  context : Context
  action : Action
  location : Option Scope
  value : Nat
  deriving Repr
structure Effective where
  value : Nat
  source : Source
  deriving BEq, DecidableEq, Repr

def defaultTarget : App → Scope
  | .npm => .home | .pnpm => .global | .yarn => .project

def target (r : Request) : Scope := r.location.getD (defaultTarget r.app)

def put (s : State) (destination : Scope) (value : Option Nat) : State := match destination with
  | .global => {s with global := value}
  | .home => {s with home := value}
  | .project => {s with project := value}

def after (r : Request) : State := match r.action with
  | .set => put r.state (target r) (some r.value)
  | .unset => put r.state (target r) none
  | _ => r.state

/-- Fixed scalar registry profile. This is not a map/array merge, key codec,
    auth policy, filesystem parser, or generic config precedence law. -/
def effective (app : App) (s : State) (c : Context) (homeReaderMatchesWriter : Bool := false) : Effective :=
  if let some value := c.command then ⟨value,.command⟩
  else if let some value := c.environment then ⟨value,.environment⟩
  else if !c.globalMode && s.project.isSome then ⟨s.project.getD 0,.project⟩
  else if app == .npm && s.home.isSome then ⟨s.home.getD 0,.home⟩
  else if app == .yarn && (!c.customRc || homeReaderMatchesWriter) && s.home.isSome then ⟨s.home.getD 0,.home⟩
  else if app != .yarn && s.global.isSome then ⟨s.global.getD 0,.global⟩
  else ⟨c.fallback,.fallback⟩

def currentEffective (r : Request) : Effective := effective r.app (after r) r.context

/-- Current Yarn set headline prints the reloaded effective value. Requested
    stored value and masking source are separate facts for proposed reporting. -/
def reportedSetValue (r : Request) : Option Nat :=
  if r.app == .yarn && r.action == .set then some (currentEffective r).value else none

def writtenValue (r : Request) : Option Nat := if r.action == .set then some r.value else none

def initial : State := ⟨some 1,some 2,some 3⟩
def normal : Context := ⟨none,none,false,false,9⟩
def yarnMasked : Request := ⟨.yarn,initial,{normal with environment := some 4},.set,some .home,7⟩

theorem defaults_are_distinct :
    defaultTarget .npm = .home ∧ defaultTarget .pnpm = .global ∧ defaultTarget .yarn = .project := by decide

theorem read_is_not_a_write (r : Request) : after {r with action := .read} = r.state := rfl

theorem explain_is_not_a_write (r : Request) : after {r with action := .explain} = r.state := rfl

theorem explicit_location_wins (r : Request) (s : Scope) : target {r with location := some s} = s := rfl

theorem project_write_preserves_home (s : State) (v : Option Nat) : (put s .project v).home = s.home := rfl

theorem home_write_preserves_project (s : State) (v : Option Nat) : (put s .home v).project = s.project := rfl

theorem command_overrides_environment (app : App) (s : State) (c : Context) (v : Nat) :
    effective app s {c with command := some v} = ⟨v,.command⟩ := rfl

theorem environment_masks_file_write :
    (after yarnMasked).home = some 7 ∧ currentEffective yarnMasked = ⟨4,.environment⟩ := by decide

theorem current_headline_can_differ_from_written_value :
    reportedSetValue yarnMasked = some 4 ∧ writtenValue yarnMasked = some 7 := by decide

theorem npm_global_mode_still_reads_user :
    effective .npm initial {normal with globalMode := true} = ⟨2,.home⟩ := by decide

theorem pnpm_global_mode_reads_global :
    effective .pnpm {initial with home := none} {normal with globalMode := true} = ⟨1,.global⟩ := by decide

theorem custom_yarn_home_write_is_not_loaded :
    effective .yarn ⟨none,some 7,none⟩ {normal with customRc := true} = ⟨9,.fallback⟩ := by decide

theorem standard_yarn_home_is_loaded :
    effective .yarn ⟨none,some 7,none⟩ normal = ⟨7,.home⟩ := by decide

theorem proposed_aligned_home_reader_retains_written_value :
    effective .yarn ⟨none,some 7,none⟩ {normal with customRc := true} true = ⟨7,.home⟩ := by decide

theorem proposed_reader_does_not_bypass_environment :
    effective .yarn ⟨none,some 7,none⟩ {normal with customRc := true, environment := some 4} true = ⟨4,.environment⟩ := by decide

theorem unset_project_exposes_next_scope :
    effective .npm (put initial .project none) normal = ⟨2,.home⟩ := by decide

theorem same_effective_value_does_not_prove_same_saved_state :
    effective .npm initial normal = effective .npm {initial with home := some 7} normal ∧
    initial ≠ {initial with home := some 7} := by decide

end ApplicationStudy.JsConfiguration
