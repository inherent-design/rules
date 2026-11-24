namespace ApplicationStudy.EmpackIdentity

/-- Injective equality labels for the finite recorded values, not inode numbers,
    creation timestamps, hashes, or a new production wire representation. -/
structure Object where
  volume : Nat
  number : Nat
  created : Option Nat
  token : Option Nat
  deriving BEq, DecidableEq, Repr
def liveEqual (a b : Object) : Bool := decide (a = b)
def durableEqual (a b : Object) : Bool :=
  match a.token,b.token with
  | some x,some y => x == y
  | _,_ => false
inductive JournalResult | unavailable | comparison (equal : Bool)
  deriving BEq, DecidableEq, Repr
def journal (saved observed : Option Object) : JournalResult :=
  match saved with
  | none => .comparison observed.isNone
  | some saved => match saved.token with
    | none => .unavailable
    | some _ => .comparison (observed.any (durableEqual saved))

inductive Atom | number (negative : Bool) (magnitude : Nat) | other
  deriving BEq, DecidableEq, Repr
structure Member where
  name : String
  array : Bool
  atoms : List Atom
  deriving BEq, DecidableEq, Repr
def byteAtom : Atom → Bool
  | .number negative n => !negative && n < 256
  | .other => false
/-- Shape projection after independent duplicate-preserving JSON parsing.
    It neither parses JSON text nor validates an outer recovery journal. -/
def bindingCodec (object : Bool) (members : List Member) : Bool :=
  object && match members with
  | [member] => member.name == "persistent" && member.array &&
      member.atoms.length == 32 && member.atoms.all byteAtom
  | _ => false

inductive Node
  | absent
  | ancestor (object : Object)
  | file (object : Object) (content bytes : Nat) (readonly : Bool) (mode : Nat)
  | directory (object : Object) (members : List String)
  deriving BEq, DecidableEq, Repr
structure Entry where
  path : String
  node : Node
  deriving BEq, DecidableEq, Repr
structure Snapshot where
  root : Object
  entries : List Entry
  deriving BEq, DecidableEq, Repr
inductive ProjectedNode
  | absent
  | ancestor (token : Nat)
  | file (token content bytes : Nat) (readonly : Bool) (mode : Nat)
  | directory (token : Nat) (members : List String)
  deriving BEq, DecidableEq, Repr
def projectNode : Node → Option ProjectedNode
  | .absent => some .absent
  | .ancestor object => object.token.map .ancestor
  | .file object content bytes readonly mode => object.token.map (fun t => .file t content bytes readonly mode)
  | .directory object members => object.token.map (fun t => .directory t members)
structure Projection where
  rootToken : Nat
  entries : List (String × ProjectedNode)
  deriving BEq, DecidableEq, Repr
/-- Canonical path/member order is an admitted premise. This is the structural
    hash input projection; no SHA-256 implementation or collision claim. -/
def project (snapshot : Snapshot) : Option Projection := do
  let root ← snapshot.root.token
  let entries ← snapshot.entries.mapM fun e => do
    let node ← projectNode e.node
    pure (e.path,node)
  pure ⟨root,entries⟩
def projectionEqual (a b : Snapshot) : Option Bool := do
  let a ← project a
  let b ← project b
  pure (a == b)

inductive AssociationResult | misnamed | unavailable | comparison (equal : Bool)
  deriving BEq, DecidableEq, Repr
/-- Names are independently derived from the original Binding key and the
    actual argument to matches(). No directory lookup or root authority. -/
def association (original selected : String) (saved : Nat) (observed : Option Nat) : AssociationResult :=
  if original != selected then .misnamed
  else match observed with
    | none => .unavailable
    | some token => .comparison (saved == token)
inductive Availability | unavailable | error
  deriving BEq, DecidableEq, Repr
def availability (reason : String) : Availability :=
  if ["ENOTSUP","ENOTTY","ENOSYS","EACCES","EPERM"].contains reason then .unavailable else .error

theorem live_equality_includes_volume (a b : Object) (h : liveEqual a b = true) : a.volume = b.volume := by
  have same : a = b := by simpa [liveEqual] using h
  exact congrArg Object.volume same
theorem missing_tokens_do_not_establish_durable_identity (a b : Object) (h : a.token = none) :
    durableEqual a b = false := by simp [durableEqual,h]
theorem durable_comparison_ignores_other_live_fields (v n v' n' token : Nat) (c c' : Option Nat) :
    durableEqual ⟨v,n,c,some token⟩ ⟨v',n',c',some token⟩ = true := by simp [durableEqual]
theorem durable_equality_does_not_imply_live_equality :
    durableEqual ⟨1,2,some 3,some 4⟩ ⟨9,2,some 3,some 4⟩ = true ∧
    liveEqual ⟨1,2,some 3,some 4⟩ ⟨9,2,some 3,some 4⟩ = false := by decide
theorem absent_pairs_match : journal none none = .comparison true := rfl
theorem absent_saved_does_not_match_an_object (o : Object) : journal none (some o) = .comparison false := rfl
theorem saved_object_does_not_match_absence (v n t : Nat) (c : Option Nat) :
    journal (some ⟨v,n,c,some t⟩) none = .comparison false := rfl
theorem unavailable_saved_is_not_a_mismatch (v n : Nat) (c : Option Nat) (observed : Option Object) :
    journal (some ⟨v,n,c,none⟩) observed = .unavailable := rfl
theorem unavailable_observed_does_not_match :
    journal (some ⟨1,2,some 3,some 4⟩) (some ⟨1,2,none,none⟩) = .comparison false := rfl
theorem duplicate_binding_fields_are_rejected (a b : Member) : bindingCodec true [a,b] = false := rfl
theorem nonobject_binding_is_rejected (fields : List Member) : bindingCodec false fields = false := rfl
theorem negative_byte_is_rejected : byteAtom (.number true 1) = false := rfl
theorem oversized_byte_is_rejected : byteAtom (.number false 256) = false := rfl
theorem wrong_type_byte_is_rejected : byteAtom .other = false := rfl
theorem absent_node_needs_no_object_token : projectNode .absent = some .absent := rfl
theorem missing_root_prevents_fingerprint (v n : Nat) (c : Option Nat) (entries : List Entry) :
    project ⟨⟨v,n,c,none⟩,entries⟩ = none := rfl
theorem fingerprint_projection_does_not_supply_live_equality :
    projectionEqual ⟨⟨1,2,some 3,some 4⟩,[]⟩ ⟨⟨9,2,some 3,some 4⟩,[]⟩ = some true ∧
    liveEqual ⟨1,2,some 3,some 4⟩ ⟨9,2,some 3,some 4⟩ = false := by decide
theorem file_projection_preserves_mode_distinction :
    projectNode (.file ⟨1,2,some 3,some 4⟩ 5 6 false 7) ≠
    projectNode (.file ⟨1,2,some 3,some 4⟩ 5 6 false 8) := by decide
theorem file_projection_preserves_content_distinction :
    projectNode (.file ⟨1,2,some 3,some 4⟩ 5 6 false 7) ≠
    projectNode (.file ⟨1,2,some 3,some 4⟩ 9 6 false 7) := by decide
theorem wrong_record_name_is_rejected_first (a b : String) (h : a ≠ b) (saved : Nat) (observed : Option Nat) :
    association a b saved observed = .misnamed := by simp [association,h]
theorem missing_association_evidence_is_not_absence (name : String) (saved : Nat) :
    association name name saved none = .unavailable := by simp [association]
theorem permission_classifier_is_not_durable_evidence : availability "EACCES" = .unavailable := rfl
theorem unrelated_io_error_is_retained : availability "EIO" = .error := rfl

end ApplicationStudy.EmpackIdentity
