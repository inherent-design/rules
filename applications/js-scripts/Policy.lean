namespace ApplicationStudy.JsScripts

/-- Effective profiles of the selected fixtures. npm uses non-strict review;
    pnpm uses its strict-dependency-build default and enabled pre/post run
    wrappers. Yarn uses the node-modules linker and a compatible hard package.
    This is not one universal `scripts disabled` setting. -/
inductive Profile
  | npm (ignore dangerous : Bool)
  | pnpm (ignore dangerous : Bool)
  | yarn (enabled : Bool)
  deriving Repr

/-- Result of the application's trusted-source policy matching, not the
    package's own request for authority or self-reported identity. -/
inductive Review | unreviewed | allow | deny deriving BEq, DecidableEq, Repr
inductive Scope | dependencyInstall | workspaceInstall | explicitRootRun deriving BEq, DecidableEq, Repr
inductive Decision | run | skip | reviewRequired deriving BEq, DecidableEq, Repr

def dependencyDecision (profile : Profile) (review : Review) : Decision :=
  match profile with
  | .npm ignore dangerous =>
    if ignore then .skip
    else if dangerous then .run
    else if review == .deny then .skip else .run
  | .pnpm ignore dangerous =>
    if ignore then .skip
    else if review == .deny then .skip
    else if dangerous || review == .allow then .run else .reviewRequired
  | .yarn enabled =>
    if review == .deny then .skip
    else if enabled || review == .allow then .run else .skip

def decision (profile : Profile) (scope : Scope) (review : Review) : Decision :=
  match scope with
  | .dependencyInstall => dependencyDecision profile review
  | .explicitRootRun => .run
  | .workspaceInstall => match profile with
    | .npm ignore _ | .pnpm ignore _ => if ignore then .skip else .run
    | .yarn _ => .run

def label : Decision → String
  | .run => "run"
  | .skip => "skip"
  | .reviewRequired => "review-required"

def installEffects (scope : Scope) (decision : Decision) : List String :=
  if decision != .run then []
  else match scope with
    | .dependencyInstall => ["dependency:preinstall", "dependency:install", "dependency:postinstall"]
    | .workspaceInstall => ["root:preinstall", "root:install", "root:postinstall"]
    | .explicitRootRun => []

/-- Controlled root `probe`, not arbitrary script names or configuration.
    pnpm's enabled wrappers are a profile premise; ignore affects installation,
    not this explicit request. Yarn has no implicit preprobe/postprobe here. -/
def explicitRootEffects : Profile → List String
  | .npm ignore _ => if ignore then ["root:probe"] else ["root:preprobe", "root:probe", "root:postprobe"]
  | .pnpm _ _ => ["root:preprobe", "root:probe", "root:postprobe"]
  | .yarn _ => ["root:probe"]

/-- The only injected failure is after the controlled dependency postinstall
    writes its marker. Missing files, signals and arbitrary child effects are
    not predicted. Earlier marker observations remain separate from status. -/
def installSucceeds (scope : Scope) (decision : Decision) (failAfterPost : Bool) : Bool :=
  decision != .reviewRequired && !(scope == .dependencyInstall && decision == .run && failAfterPost)

theorem npm_ignore_overrides_review (review : Review) (dangerous : Bool) :
    dependencyDecision (.npm true dangerous) review = .skip := rfl

theorem pnpm_ignore_overrides_review (review : Review) (dangerous : Bool) :
    dependencyDecision (.pnpm true dangerous) review = .skip := rfl

theorem pnpm_deny_overrides_broad_allow (dangerous : Bool) :
    dependencyDecision (.pnpm false dangerous) .deny = .skip := rfl

theorem npm_broad_allow_bypasses_deny :
    dependencyDecision (.npm false true) .deny = .run := rfl

theorem yarn_explicit_allow_overrides_disabled_default :
    dependencyDecision (.yarn false) .allow = .run := rfl

theorem yarn_workspace_scripts_ignore_dependency_default (enabled : Bool) (review : Review) :
    decision (.yarn enabled) .workspaceInstall review = .run := rfl

theorem explicit_run_is_a_separate_request (profile : Profile) (review : Review) :
    decision profile .explicitRootRun review = .run := rfl

theorem unreviewed_is_not_explicit_denial :
    dependencyDecision (.pnpm false false) .unreviewed ≠ dependencyDecision (.pnpm false false) .deny := by decide

theorem yarn_scope_changes_effect :
    decision (.yarn false) .dependencyInstall .deny = .skip ∧
    decision (.yarn false) .workspaceInstall .deny = .run := ⟨rfl, rfl⟩

theorem failed_hook_does_not_erase_observed_markers :
    installSucceeds .dependencyInstall .run true = false ∧
    (installEffects .dependencyInstall .run).length = 3 := ⟨rfl, rfl⟩

theorem explicit_probe_survives_install_disabling (profile : Profile) :
    "root:probe" ∈ explicitRootEffects profile := by
  cases profile with
  | npm ignore dangerous => cases ignore <;> simp [explicitRootEffects]
  | pnpm ignore dangerous => simp [explicitRootEffects]
  | yarn enabled => simp [explicitRootEffects]

end ApplicationStudy.JsScripts
