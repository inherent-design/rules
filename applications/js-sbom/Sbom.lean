namespace ApplicationStudy.JsSbom

-- Three direct local archives, each 1.0.0, no scripts/peers/workspaces.
-- Install is the qualified successful seed event, not an installer proof.
inductive Profile where | npm | pnpm deriving BEq, DecidableEq, Repr
inductive Format where | cyclonedx | spdx | missing deriving BEq, DecidableEq, Repr
inductive Operation where
  | install | query | report | replaceCode | holdEntry | restoreEntry | holdLock
  deriving BEq, DecidableEq, Repr
structure Request where
  operation : Operation
  format : Format := .cyclonedx
  lockOnly : Bool := false
  runtimeOnly : Bool := false
  deriving BEq, DecidableEq, Repr
structure Context where
  profile : Profile
  declaredName : String
  directoryName : String
  prodDigest : String
  devDigest : String
  optionalDigest : String
  deriving BEq, DecidableEq, Repr
structure State where
  installed : Bool := false
  lock : Bool := false
  entry : Bool := false
  changedCode : Bool := false
  deriving BEq, DecidableEq, Repr
inductive GraphBasis where | installedMetadata | lock deriving BEq, DecidableEq, Repr
inductive MetadataBasis where | installed | saved | virtualStore | unavailable deriving BEq, DecidableEq, Repr
def graphBasis (p : Profile) (r : Request) : GraphBasis :=
  if p == .npm && !r.lockOnly then .installedMetadata else .lock
def metadataBasis (p : Profile) (r : Request) : MetadataBasis :=
  if p == .npm then if r.lockOnly then .saved else .installed
  else if r.lockOnly then .unavailable else .virtualStore
def code (p : Profile) (s : State) (r : Request) : Nat :=
  if r.format == .missing then if p == .npm then 1 else 2
  else if p == .pnpm || r.lockOnly then if s.lock then 0 else 1
  -- In this file-tarball fixture the resolved-location witness comes from
  -- the lock; removing it does not prove the installed edges valid.
  else if s.installed && s.entry && s.lock then 0 else 1
def rootName (c : Context) (f : Format) : String :=
  if c.profile == .npm && f == .cyclonedx then c.directoryName else c.declaredName
-- Proposed correction only; package and placement identities stay distinct.
def candidateRootName (c : Context) : String := c.declaredName
def versionText (p : Profile) (f : Format) : String :=
  if f == .spdx then "SPDX-2.3" else if p == .npm then "1.5" else "1.7"
def phase (r : Request) : String :=
  if r.format == .spdx then "-" else if r.lockOnly then "pre-build" else "build"
def scope (p : Profile) (r : Request) (dev optional : Bool) : String :=
  if r.format == .spdx then
    if p == .pnpm then "DEPENDS_ON"
    else if dev then "DEV_DEPENDENCY_OF" else if optional then "OPTIONAL_DEPENDENCY_OF" else "DEPENDENCY_OF"
  else if p == .pnpm then if dev then "excluded" else "-"
  else if optional || (dev && r.lockOnly) then "optional" else "required"
structure Component where
  name : String
  digest : String -- archive SHA512 assertion, not current installed-file SHA
  scope : String
  development : Bool
  license : Bool
  deriving BEq, DecidableEq, Repr
structure Report where
  rootDisplay : String
  rootPackage : String
  version : String
  phase : String
  components : List Component
  deriving BEq, DecidableEq, Repr
def component (c : Context) (r : Request) (name digest : String) (dev optional : Bool) : Component :=
  ⟨name,digest,scope c.profile r dev optional,
    r.format == .cyclonedx && dev, metadataBasis c.profile r != .unavailable⟩
def document (c : Context) (r : Request) : Report :=
  let prod := component c r "rules-sbom-prod" c.prodDigest false false
  let dev := component c r "rules-sbom-dev" c.devDigest true false
  let optional := component c r "rules-sbom-optional" c.optionalDigest false true
  ⟨rootName c r.format,c.declaredName,versionText c.profile r.format,phase r,
    if r.runtimeOnly then [prod] else [dev,optional,prod]⟩
-- An inventory generator reports artifact assertions; this study never adds
-- an observed-file verification receipt merely because a document exists.
def verifiesInstalledBytes (_ : Report) : Bool := false
structure Result where
  exitCode : Nat
  after : State
  runtime : Option String := none
  report : Option Report := none
  deriving BEq, DecidableEq, Repr
def step (c : Context) (s : State) (r : Request) : Result :=
  match r.operation with
  | .install => ⟨0,⟨true,true,true,false⟩,none,none⟩
  | .replaceCode => ⟨0,{s with changedCode := true},none,none⟩
  | .holdEntry => ⟨0,{s with entry := false},none,none⟩
  | .restoreEntry => ⟨0,{s with entry := true},none,none⟩
  | .holdLock => ⟨0,{s with lock := false},none,none⟩
  | .query => ⟨0,s,some (if !s.entry then "missing" else if s.changedCode then "changed" else "original"),none⟩
  | .report => let result := code c.profile s r
               ⟨result,s,none,if result == 0 then some (document c r) else none⟩
def trace (c : Context) (s : State) : List Request → List Result
  | [] => []
  | r::tail => let result := step c s r
               result :: trace c result.after tail
def componentText (c : Component) : String :=
  c.name ++ "," ++ c.digest ++ "," ++ c.scope ++ "," ++
  (if c.development then "dev" else "-") ++ "," ++ (if c.license then "MIT" else "-")
def reportText (d : Report) : String :=
  String.intercalate "|" [d.rootDisplay,d.rootPackage,d.version,d.phase,
    String.intercalate ";" (d.components.map componentText)]
def text (r : Result) : String :=
  toString r.exitCode ++ "/" ++ r.runtime.getD "-" ++ "/" ++ (r.report.map reportText).getD "-"
def npm : Context := ⟨.npm,"declared-root","physical-root","prod","dev","optional"⟩
def pnpm : Context := {npm with profile := .pnpm}
def installed : State := ⟨true,true,true,false⟩
def request : Request := {operation := .report}

theorem report_preserves_state (c : Context) (s : State) (r : Request) :
    (step c s {r with operation := .report}).after = s := rfl
theorem query_preserves_state (c : Context) (s : State) :
    (step c s {operation := .query}).after = s := rfl
theorem report_does_not_read_code_flag (c : Context) (s : State) (r : Request) :
    (step c {s with changedCode := true} {r with operation := .report}).report =
    (step c {s with changedCode := false} {r with operation := .report}).report := by rfl
theorem document_is_not_file_verification (c : Context) (r : Request) :
    verifiesInstalledBytes (document c r) = false := rfl
theorem missing_entry_refuses_npm_default :
    code .npm {installed with entry := false} request = 1 := by decide
theorem missing_entry_does_not_erase_pnpm_lock :
    code .pnpm {installed with entry := false} request = 0 := by decide
theorem explicit_lock_report_does_not_require_top_entry :
    code .npm {installed with entry := false} {request with lockOnly := true} = 0 := by decide
theorem missing_lock_refuses_both_explicit_modes :
    code .npm {installed with lock := false} {request with lockOnly := true} = 1 ∧
    code .pnpm {installed with lock := false} {request with lockOnly := true} = 1 := by decide
theorem local_tarball_profile_refuses_missing_location_witness :
    code .npm {installed with lock := false} request = 1 := by decide
theorem missing_format_exits_differ :
    code .npm installed {request with format := .missing} = 1 ∧
    code .pnpm installed {request with format := .missing} = 2 := by decide
theorem npm_actual_and_virtual_graphs_differ :
    graphBasis .npm request ≠ graphBasis .npm {request with lockOnly := true} := by decide
theorem pnpm_both_modes_have_lock_graph :
    graphBasis .pnpm request = .lock ∧ graphBasis .pnpm {request with lockOnly := true} = .lock := by decide
theorem lock_only_drops_pnpm_metadata_enrichment :
    (document pnpm {request with lockOnly := true}).components.all (fun c => !c.license) = true := by decide
theorem runtime_filter_keeps_only_prod :
    ((document npm {request with runtimeOnly := true}).components.map (·.name)) = ["rules-sbom-prod"] := by decide
theorem npm_root_display_uses_placement :
    rootName npm .cyclonedx = npm.directoryName ∧ rootName npm .spdx = npm.declaredName := by decide
theorem root_package_identity_is_format_independent :
    (document npm request).rootPackage = (document npm {request with format := .spdx}).rootPackage := by decide
theorem proposed_root_name_ignores_placement (c : Context) (other : String) :
    candidateRootName {c with directoryName := other} = candidateRootName c := rfl
theorem spdx_dependency_categories_are_tool_specific :
    scope .npm {request with format := .spdx} true false = "DEV_DEPENDENCY_OF" ∧
    scope .pnpm {request with format := .spdx} true false = "DEPENDS_ON" := by decide
theorem npm_actual_virtual_development_scopes_differ :
    scope .npm request true false = "required" ∧
    scope .npm {request with lockOnly := true} true false = "optional" := by decide
theorem holding_lock_preserves_entry_and_changed_code (c : Context) (s : State) :
    (step c s {operation := .holdLock}).after.entry = s.entry ∧
    (step c s {operation := .holdLock}).after.changedCode = s.changedCode := ⟨rfl,rfl⟩

end ApplicationStudy.JsSbom
