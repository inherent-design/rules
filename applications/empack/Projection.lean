namespace ApplicationStudy.EmpackProjection

/-- Controlled domain projection over the captured pure-core cases. Source
    identities, destination labels and asset labels have different roles.
    The numeric labels are test values, not a selected project wire schema. -/
inductive Layer | common | sharedOverride | client | server deriving BEq, DecidableEq, Repr
inductive Side | client | server deriving BEq, DecidableEq, Repr
inductive Environments | client | server | both deriving BEq, DecidableEq, Repr
inductive View
  | flat (side : Side) (full : Bool)
  | layers (environments : Environments) (full : Bool)
  deriving Repr
inductive Requirement | unsupported | required | optional (defaultEnabled : Bool)
  deriving BEq, DecidableEq, Repr
/-- Download cases have no independent digest assertions: only the captured
    accepted-observation/origin fields vary. Digest-bearing references need
    additional cases and are not represented by this projection. -/
inductive Representation
  | embedded (asset : Nat)
  | unacquired
  | download (observed : Option Nat) (originNonempty : Bool)
  deriving BEq, DecidableEq, Repr

structure Entry where
  owner : Nat
  layer : Layer
  destination : Nat
  client : Requirement
  server : Requirement
  representation : Representation
  deriving BEq, DecidableEq, Repr

/-- This fixture uses one declared choice key, `extra`, with fixed description.
    `unknown` supplies a different key. General key maps are not modeled. -/
inductive Policy | preserve | unresolved | enable | disable | defaults | unknown
  deriving BEq, DecidableEq, Repr
inductive Error
  | duplicate | invalidEnvironment | conflictingChoice | unknownChoice
  | preserveRequired | overlayNeedsChoice | choiceRequired | invalidReference | materialization
  deriving BEq, DecidableEq, Repr
structure Choice where
  enabled : Bool
  usedDefault : Bool
  deriving BEq, DecidableEq, Repr
inductive Decision
  | skip (choice : Option Choice)
  | take (requirement : Requirement) (choice : Option Choice)
  deriving BEq, DecidableEq, Repr
structure Replacement where
  replacement : Nat
  replaced : Nat
  destination : Nat
  deriving BEq, DecidableEq, Repr
structure Plan where
  entries : List Entry
  precedence : List Replacement
  choice : Option Choice
  deriving BEq, DecidableEq, Repr
structure Pick where
  entry : Option Entry
  precedence : List Replacement
  choice : Option Choice
  deriving Repr

def layerRank : Layer → Nat | .common => 0 | .sharedOverride => 1 | .client => 2 | .server => 3

def isFull : View → Bool | .flat _ full | .layers _ full => full

def requirementFor (side : Side) (entry : Entry) : Requirement :=
  match side with | .client => entry.client | .server => entry.server

def invalidEnvironment (entry : Entry) : Bool :=
  (entry.client == .unsupported && entry.server == .unsupported) ||
  (entry.layer == .client && entry.server != .unsupported) ||
  (entry.layer == .server && entry.client != .unsupported)

private def declare (requirements : List Requirement) (current : Option Bool) : Except Error (Option Bool) :=
  match requirements with
  | [] => .ok current
  | .optional value :: rest =>
    if current.isSome && current != some value then .error .conflictingChoice
    else declare rest (some value)
  | _ :: rest => declare rest current

/-- Validate the whole supplied semantic input before eliminating shadowed
    obligations. This is distinct from asking for a missing choice at use time. -/
def validate (inputs : List Entry) (seen : List (Layer × Nat) := [])
    (declared : Option Bool := none) : Except Error (Option Bool) := do
  match inputs with
  | [] => pure declared
  | entry :: rest =>
    if seen.contains (entry.layer, entry.destination) then throw .duplicate
    if invalidEnvironment entry then throw .invalidEnvironment
    let next ← declare [entry.client, entry.server] declared
    validate rest ((entry.layer, entry.destination) :: seen) next

def policyGuard (view : View) (policy : Policy) (declared : Option Bool) : Except Error Unit := do
  if policy == .unknown || ((policy == .enable || policy == .disable) && declared.isNone) then
    throw .unknownChoice
  match view with
  | .layers _ _ => if policy != .preserve then throw .preserveRequired
  | .flat _ _ => pure ()

private def resolvedDecision (enabled useDefault : Bool) : Decision :=
  let receipt := some (Choice.mk enabled useDefault)
  if enabled then .take .required receipt else .skip receipt

def requirementDecision (policy : Policy) (full fallback : Bool) : Requirement → Except Error Decision
  | .unsupported => .ok (.skip none)
  | .required => .ok (.take .required none)
  | .optional defaultEnabled => match policy with
    | .preserve =>
      if fallback then .error .overlayNeedsChoice
      else if full then .error .choiceRequired
      else .ok (.take (.optional defaultEnabled) none)
    | .unresolved => .error .choiceRequired
    | .enable => .ok (resolvedDecision true false)
    | .disable => .ok (resolvedDecision false false)
    | .defaults => .ok (resolvedDecision defaultEnabled true)
    | .unknown => .error .unknownChoice

def flattened (side : Side) (entry : Entry) (requirement : Requirement) : Entry :=
  {entry with
    layer := .common
    client := if side == .client then requirement else .unsupported
    server := if side == .server then requirement else .unsupported}

private def replaced (side : Side) (winner : Entry) (lower : List Entry) : List Replacement :=
  (lower.filter fun entry => requirementFor side entry != .unsupported).map fun entry =>
    ⟨winner.owner, entry.owner, winner.destination⟩

private def choose (side : Side) (full : Bool) (policy : Policy) : List Entry → Except Error Pick
  | [] => .ok ⟨none, [], none⟩
  | entry :: lower => do
    let fallback := lower.any fun candidate => requirementFor side candidate != .unsupported
    let decision ← requirementDecision policy full fallback (requirementFor side entry)
    match decision with
    | .take requirement receipt => pure ⟨some (flattened side entry requirement), replaced side entry lower, receipt⟩
    | .skip receipt =>
      let result ← choose side full policy lower
      pure {result with choice := result.choice.or receipt}

private def sideLayer : Side → Layer | .client => .client | .server => .server

private def flatPaths (inputs : List Entry) (paths : List Nat) (side : Side) (full : Bool)
    (policy : Policy) (plan : Plan) : Except Error Plan := do
  match paths with
  | [] => pure plan
  | destination :: rest =>
    let layers := (inputs.filter fun entry => entry.destination == destination &&
      (entry.layer == .common || entry.layer == .sharedOverride || entry.layer == sideLayer side)).mergeSort
      (fun a b => layerRank a.layer ≥ layerRank b.layer)
    let picked ← choose side full policy layers
    let entries := match picked.entry with | none => plan.entries | some entry => plan.entries ++ [entry]
    flatPaths inputs rest side full policy ⟨entries, plan.precedence ++ picked.precedence, picked.choice.or plan.choice⟩

private def projected (environments : Environments) (entry : Entry) : Option Entry :=
  let selected := {entry with
    client := if environments == .server then .unsupported else entry.client,
    server := if environments == .client then .unsupported else entry.server}
  if selected.client == .unsupported && selected.server == .unsupported then none else some selected

def select (inputs : List Entry) (view : View) (policy : Policy) : Except Error Plan := do
  let declared ← validate inputs
  policyGuard view policy declared
  match view with
  | .layers environments _ =>
    let ordered := inputs.mergeSort fun a b => layerRank a.layer < layerRank b.layer ||
      (a.layer == b.layer && a.destination ≤ b.destination)
    pure ⟨ordered.filterMap (projected environments), [], none⟩
  | .flat side full => flatPaths inputs ((inputs.map (·.destination)).eraseDups.mergeSort) side full policy ⟨[], [], none⟩

def completeRepresentation (full : Bool) : Representation → Except Error Unit
  | .unacquired => .error .materialization
  | .embedded _ => .ok ()
  | .download observed origin =>
    if observed.isNone || !origin then .error .invalidReference
    else if full then .error .materialization else .ok ()

def finish (view : View) (plan : Plan) : Except Error Plan := do
  for entry in plan.entries do completeRepresentation (isFull view) entry.representation
  pure plan

theorem required_does_not_ask_for_lower_choice (policy : Policy) (full fallback : Bool) :
    requirementDecision policy full fallback .required = .ok (.take .required none) := rfl

theorem disabled_optional_uses_fallback (full fallback defaultEnabled : Bool) :
    requirementDecision .disable full fallback (.optional defaultEnabled) = .ok (.skip (some ⟨false, false⟩)) := rfl

theorem preserved_overlay_cannot_erase_fallback (full defaultEnabled : Bool) :
    requirementDecision .preserve full true (.optional defaultEnabled) = .error .overlayNeedsChoice := rfl

theorem unresolved_selected_choice_is_not_guessed (full fallback defaultEnabled : Bool) :
    requirementDecision .unresolved full fallback (.optional defaultEnabled) = .error .choiceRequired := rfl

theorem flattened_retains_source_identity (side : Side) (entry : Entry) (req : Requirement) :
    (flattened side entry req).owner = entry.owner := rfl

theorem flattened_retains_representation (side : Side) (entry : Entry) (req : Requirement) :
    (flattened side entry req).representation = entry.representation := rfl

theorem flattened_retains_destination (side : Side) (entry : Entry) (req : Requirement) :
    (flattened side entry req).destination = entry.destination := rfl

theorem selected_missing_bytes_are_not_complete (full : Bool) :
    completeRepresentation full .unacquired = .error .materialization := rfl

theorem invalid_origin_is_not_a_complete_reference (full : Bool) (asset : Option Nat) :
    completeRepresentation full (.download asset false) = .error .invalidReference := by
  cases asset <;> rfl

theorem reference_cannot_supply_full_bytes (asset : Nat) :
    completeRepresentation true (.download (some asset) true) = .error .materialization := rfl

end ApplicationStudy.EmpackProjection
