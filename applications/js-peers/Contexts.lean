namespace ApplicationStudy.JsPeers

/- These profiles name this observed local-tarball workspace fixture. They
   do not encode a general hoisting algorithm or every option of each tool. -/
inductive FixtureProfile where
  | npmHoisted | pnpmIsolated | yarnNodeModules
  deriving DecidableEq, Repr

structure Instance where
  content : String
  peerProvider : String
  deriving DecidableEq, Repr

def fixtureProvider (profile : FixtureProfile) (direct hoisted : String) : String :=
  match profile with
  | .npmHoisted => hoisted
  | .pnpmIsolated | .yarnNodeModules => direct

def instantiate (profile : FixtureProfile) (content direct hoisted : String) : Instance :=
  ⟨content, fixtureProvider profile direct hoisted⟩

theorem distinct_peers_distinct_instances (a b : Instance)
    (different : a.peerProvider ≠ b.peerProvider) : a ≠ b := by
  intro equal
  exact different (congrArg Instance.peerProvider equal)

theorem instantiate_preserves_content (p : FixtureProfile) (content direct hoisted : String) :
    (instantiate p content direct hoisted).content = content := rfl

theorem pnpm_fixture_uses_direct (content direct hoisted : String) :
    (instantiate .pnpmIsolated content direct hoisted).peerProvider = direct := rfl

theorem yarn_fixture_uses_direct (content direct hoisted : String) :
    (instantiate .yarnNodeModules content direct hoisted).peerProvider = direct := rfl

theorem npm_fixture_uses_hoisted (content direct hoisted : String) :
    (instantiate .npmHoisted content direct hoisted).peerProvider = hoisted := rfl

/- Frozen admission is a projection of this refusal phase. Bases are semantic
   dependency selections, not raw manifest formatting. The accepted branch
   admits later work; it does not claim installation or execution completed. -/
structure InstallState where
  declaredBasis : String
  lockedBasis : String
  lockBytes : String
  installedBindingEvidence : String
  deriving DecidableEq, Repr

structure Admission where
  refused : Bool
  state : InstallState
  deriving DecidableEq, Repr

def frozenAdmission (s : InstallState) : Admission :=
  ⟨s.declaredBasis != s.lockedBasis, s⟩

theorem refusal_retains_current_draft (s : InstallState) :
    (frozenAdmission s).state.declaredBasis = s.declaredBasis := rfl

theorem admission_does_not_publish (s : InstallState) :
    (frozenAdmission s).state = s := rfl

theorem mismatch_refused (s : InstallState) (h : s.declaredBasis ≠ s.lockedBasis) :
    (frozenAdmission s).refused = true := by simp [frozenAdmission, h]

example : instantiate .pnpmIsolated "plugin" "api-two" "api-one" ≠
    instantiate .npmHoisted "plugin" "api-two" "api-one" := by decide

end ApplicationStudy.JsPeers
