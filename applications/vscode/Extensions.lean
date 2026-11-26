namespace ApplicationStudy.VscodeExtensions

inductive Surface | desktop | browser deriving BEq, DecidableEq, Repr
inductive Kind | ui | workspace | web deriving BEq, DecidableEq, Repr

structure HostRequest where
  surface : Surface
  localKinds : List Kind
  remoteKinds : List Kind
  localInstalled : Bool
  remoteInstalled : Bool
  remoteHost : Bool
  worker : Bool
  localDevelopment : Bool
  remoteDevelopment : Bool
  deriving Repr

/-- This preference belongs to development placement, not a user trust grant. -/
def preference (r : HostRequest) : Nat :=
  if r.localDevelopment && !r.remoteDevelopment then 1
  else if r.remoteDevelopment && !r.localDevelopment then 2 else 0

def effectiveKinds (r : HostRequest) : List Kind :=
  if r.localInstalled then r.localKinds else r.remoteKinds

/-- Codes: 1 local process, 2 local worker, 3 remote. Zero means no host. -/
def priority (r : HostRequest) (host : Nat) : Nat :=
  if preference r == 0 || (preference r == 2) == (host == 3) then 0 else 1

/-- A ranked candidate list is independent of the original early-return loop. -/
def candidate (r : HostRequest) (k : Kind) : Option (Nat × Nat) :=
  match r.surface,k with
  | .desktop,.ui => if r.localInstalled then some (priority r 1,1) else none
  | .desktop,.workspace =>
    if r.remoteInstalled then some (priority r 3,3)
    else if !r.remoteHost then some (priority r 1,1) else none
  | .desktop,.web => if r.localInstalled && r.worker then some (priority r 2,2) else none
  | .browser,.ui =>
    if r.remoteInstalled then some (if preference r == 2 then 0 else 2,3) else none
  | .browser,.workspace => if r.remoteInstalled then some (priority r 3,3) else none
  | .browser,.web =>
    if r.localInstalled || r.remoteInstalled then some (priority r 2,2) else none

def select (r : HostRequest) : Nat := Id.run do
  let candidates := (effectiveKinds r).filterMap (candidate r)
  for rank in [0,1,2] do
    if let some (_,host) := candidates.find? (fun pair => pair.1 == rank) then return host
  return 0

inductive Operation | query | install | uninstall deriving BEq, DecidableEq, Repr

structure ManagementRequest where
  operation : Operation
  registered : Nat
  requested : Nat
  compatible : Bool
  deriving Repr

structure ManagementOutcome where
  action : String
  exit : Nat
  registered : Nat
  deriving BEq, DecidableEq, Repr

/-- Bounded ordinary local VSIX requests: no force, cancellation, remote,
    builtin, allowed-publisher policy, dependency installation, or crash. -/
def manage (r : ManagementRequest) : ManagementOutcome :=
  match r.operation with
  | .query => ⟨"listed",0,r.registered⟩
  | .install =>
    if r.registered > r.requested then ⟨"skipped",0,r.registered⟩
    else if !r.compatible then ⟨"refused",1,r.registered⟩
    else ⟨"installed",0,r.requested⟩
  | .uninstall =>
    if r.registered == 0 then ⟨"absent",1,0⟩ else ⟨"removed",0,0⟩

def localWorkspace : HostRequest :=
  ⟨.desktop,[.workspace],[.workspace],true,false,false,false,false,false⟩

theorem local_manifest_kinds_win (r : HostRequest) :
    effectiveKinds { r with localInstalled := true } = r.localKinds := rfl
theorem both_development_has_no_preference (r : HostRequest) :
    preference { r with localDevelopment := true, remoteDevelopment := true } = 0 := rfl
theorem local_workspace_selects_process : select localWorkspace = 1 := by decide
theorem local_install_is_not_remote_placement :
    select { localWorkspace with remoteHost := true, worker := true } = 0 := by decide
theorem browser_cannot_use_local_workspace_process :
    select { localWorkspace with surface := .browser, worker := true } = 0 := by decide
theorem worker_availability_matters :
    select { localWorkspace with localKinds := [.web] } = 0 ∧
    select { localWorkspace with localKinds := [.web], worker := true } = 2 := by decide
theorem browser_ui_is_last_resort :
    select { localWorkspace with surface := .browser, localKinds := [.ui,.web], remoteInstalled := true, remoteHost := true } = 2 := by decide
theorem remote_development_can_prefer_remote_ui :
    select { localWorkspace with surface := .browser, localKinds := [.ui,.web], remoteInstalled := true, remoteHost := true, remoteDevelopment := true } = 3 := by decide
theorem query_preserves_registration (r : ManagementRequest) :
    (manage { r with operation := .query }).registered = r.registered := rfl
theorem incompatible_newer_preserves_registration :
    manage ⟨.install,1,3,false⟩ = ⟨"refused",1,1⟩ := by decide
theorem successful_exit_can_skip_change :
    manage ⟨.install,2,1,true⟩ = ⟨"skipped",0,2⟩ := by decide
theorem uninstall_changes_membership_only_in_this_projection :
    manage ⟨.uninstall,2,0,true⟩ = ⟨"removed",0,0⟩ := by decide

end ApplicationStudy.VscodeExtensions
