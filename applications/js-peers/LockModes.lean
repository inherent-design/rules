namespace ApplicationStudy.JsLockModes

/-- Fixed single-dependency fixture labels; `absent` is not an unknown observation.
    The decoder admits only nonempty manifest selections `one` and `two`. -/
inductive Revision | absent | one | two deriving BEq, ReflBEq, LawfulBEq, DecidableEq, Repr
inductive Profile | npm | pnpm | yarn deriving BEq, ReflBEq, LawfulBEq, DecidableEq, Repr
inductive Mode | refresh | frozen | resolveOnly deriving BEq, ReflBEq, LawfulBEq, DecidableEq, Repr

structure State where
  wanted : Revision
  locked : Revision
  payload : Revision
  hidden : Revision
  deriving BEq, DecidableEq, Repr

/-- Nonempty direct dependency and no other lock-setting drift in this profile. -/
def accepted (mode : Mode) (s : State) : Bool :=
  mode != .frozen || (s.locked != .absent && s.locked == s.wanted)

/-- Projection of the measured npm hidden-lock reuse, not an implementation of
    Arborist admission (which also checks presence/mtime, topology, and options).
    pnpm/Yarn do not use this npm-specific field in the selected profile. -/
def step (profile : Profile) (mode : Mode) (s : State) : State :=
  if !accepted mode s then s else
  let payload := match mode with
    | .resolveOnly => s.payload
    | .frozen => s.wanted
    | .refresh => if profile == .npm && s.hidden == s.wanted then s.payload else s.wanted
  { s with
    locked := s.wanted
    payload := payload
    hidden := if profile == .npm then s.wanted else .absent }

/-- The owner-run control removes only the private npm hidden index. This is a
    candidate invalidation action, not a product change or general repair API. -/
def invalidateHidden (s : State) : State := {s with hidden := .absent}

def oldInstall : State := ⟨.two, .one, .one, .one⟩
def resolvedOnly : State := step .npm .resolveOnly oldInstall

theorem missing_lock_refuses_frozen (wanted : Revision) (payload hidden : Revision) :
    accepted .frozen ⟨wanted, .absent, payload, hidden⟩ = false := by cases wanted <;> rfl

theorem stale_lock_refuses_frozen : accepted .frozen oldInstall = false := rfl

theorem refusal_preserves_state (profile : Profile) (mode : Mode) (s : State)
    (h : accepted mode s = false) : step profile mode s = s := by simp [step, h]

theorem manifest_is_not_edited (profile : Profile) (mode : Mode) (s : State) :
    (step profile mode s).wanted = s.wanted := by unfold step; split <;> rfl

theorem lock_only_preserves_payload (profile : Profile) (s : State) :
    (step profile .resolveOnly s).payload = s.payload := by simp [step, accepted]

theorem frozen_success_keeps_lock (profile : Profile) (s : State)
    (h : accepted .frozen s = true) : (step profile .frozen s).locked = s.locked := by
  have same : s.locked = s.wanted := by simpa [accepted] using (by simpa [accepted] using h : s.locked ≠ .absent ∧ s.locked = s.wanted).2
  simp [step, h, same]

theorem frozen_success_materializes_wanted (profile : Profile) (s : State)
    (h : accepted .frozen s = true) : (step profile .frozen s).payload = s.wanted := by
  simp [step, h]

theorem current_lock_does_not_mean_current_payload :
    resolvedOnly.locked = resolvedOnly.wanted ∧ resolvedOnly.payload ≠ resolvedOnly.wanted := by
  constructor <;> decide

theorem hidden_index_can_disagree_with_payload :
    resolvedOnly.hidden = .two ∧ resolvedOnly.payload = .one := ⟨rfl, rfl⟩

theorem successful_refresh_can_leave_old_payload :
    accepted .refresh resolvedOnly = true ∧
    (step .npm .refresh resolvedOnly).payload = .one := ⟨rfl, rfl⟩

theorem invalidation_control_changes_refresh_result :
    (step .npm .refresh (invalidateHidden resolvedOnly)).payload = .two := rfl

theorem clean_frozen_bypasses_stale_hidden_claim :
    (step .npm .frozen resolvedOnly).payload = .two := rfl

theorem lock_only_then_refresh_counterexample :
    (step .npm .refresh (step .npm .resolveOnly oldInstall)).payload ≠ oldInstall.wanted := by decide

end ApplicationStudy.JsLockModes
