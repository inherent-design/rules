namespace ApplicationStudy.VscodeActivation

inductive Workspace | a | b deriving BEq, DecidableEq, Repr
inductive Action | start | activate | disable | enable | ping | quit | retire
  deriving BEq, DecidableEq, Repr

structure Policy where
  globallyDisabled : Bool := false
  a : Option Bool := none
  b : Option Bool := none
  deriving BEq, DecidableEq, Repr

def overrideFor (p : Policy) : Workspace → Option Bool
  | .a => p.a | .b => p.b
def allows (p : Policy) (w : Workspace) : Bool :=
  (overrideFor p w).getD (!p.globallyDisabled)
def setWorkspace (p : Policy) (w : Workspace) (value : Bool) : Policy :=
  match w with | .a => { p with a := some value } | .b => { p with b := some value }

structure State where
  policy : Policy := {}
  workspace : Workspace := .a
  alive : Bool := false
  quitting : Bool := false
  visible : Bool := false
  activated : Bool := false
  deriving BEq, DecidableEq, Repr

/-- Scoped normal lifecycle: eligible installed owned target, no automatic
    activation, disabled active code needs restart, and inactive enablement can
    add its description. Other gates and arbitrary extension disposal are open. -/
def step (s : State) (w : Workspace) (action : Action) : State :=
  match action with
  | .start => { s with workspace := w, alive := true, quitting := false, visible := allows s.policy w, activated := false }
  | .activate => { s with activated := s.visible }
  | .disable => { s with policy := setWorkspace s.policy s.workspace false, visible := s.activated }
  | .enable => { s with policy := setWorkspace s.policy s.workspace true, visible := true }
  | .ping => s
  | .quit => { s with quitting := true }
  | .retire => { s with alive := false, quitting := false, visible := false, activated := false }

structure Observation where
  visible : Option Bool
  apiActive : Option Bool
  ping : Bool
  storedOverride : Option Nat
  hooks : Option Bool
  retired : Bool
  deriving BEq, DecidableEq, Repr

def overrideCode : Option Bool → Nat
  | none => 0 | some true => 1 | some false => 2

/-- Stored policy is compared only at independently read after-exit checkpoints.
    A retirement event is admitted only with exit and PID-absence witnesses. -/
def observe (before : State) (w : Workspace) (action : Action) : Observation :=
  let after := step before w action
  ⟨if after.alive then some after.visible else none,
   if after.alive && after.visible then some after.activated else none,
   (action == .activate && after.activated) || (action == .ping && before.activated),
   if action == .retire then some (overrideCode (overrideFor after.policy after.workspace)) else none,
   if action == .retire then some before.activated else none,
   !after.alive⟩

def running : State := ⟨{},.a,true,false,true,true⟩

theorem workspace_override_precedes_global (disabled value : Bool) :
    allows ⟨disabled,some value,none⟩ .a = value := rfl
theorem default_follows_global (disabled : Bool) :
    allows ⟨disabled,none,none⟩ .a = !disabled := rfl
theorem changing_a_preserves_b (p : Policy) (value : Bool) :
    allows (setWorkspace p .a value) .b = allows p .b := rfl
theorem opening_does_not_activate (s : State) (w : Workspace) :
    (step s w .start).activated = false := rfl
theorem disable_keeps_activation_flag_and_changes_policy :
    (step running .a .disable).activated = true ∧
    allows (step running .a .disable).policy .a = false := by decide
theorem enabled_dormant_stays_dormant :
    (step { running with activated := false, visible := false } .a .enable).activated = false := rfl
theorem quit_request_preserves_activation_flag (s : State) (w : Workspace) :
    (step s w .quit).activated = s.activated := rfl
theorem confirmed_retirement_clears_runtime (s : State) (w : Workspace) :
    (step s w .retire).alive = false ∧ (step s w .retire).activated = false := ⟨rfl,rfl⟩
theorem inactive_admission_does_not_ping :
    (observe { running with activated := false, visible := false } .a .enable).ping = false := by decide
theorem held_api_can_ping_after_disable :
    (observe (step running .a .disable) .a .ping).ping = true := by decide
theorem restart_applies_disabled_workspace :
    (step (step (step running .a .disable) .a .retire) .a .start).visible = false := by decide
theorem no_mid_command_durability_claim (s : State) (w : Workspace) :
    (observe s w .disable).storedOverride = none := rfl

end ApplicationStudy.VscodeActivation
