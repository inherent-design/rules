namespace ApplicationStudy.EmpackChannels

/-- Opaque fixture labels, not hashes or URL/identifier parsers. -/
structure Binding where
  pack : Nat
  origin : Nat
  channel : Nat
  deriving BEq, ReflBEq, LawfulBEq, DecidableEq, Repr

structure Signature where
  key : Nat
  algorithmKnown : Bool
  canonical : Bool
  valid : Bool
  deriving Repr

structure Floor where
  binding : Binding
  sequence : Nat
  payload : Nat
  deriving BEq, ReflBEq, LawfulBEq, DecidableEq, Repr

structure EngineEvidence where
  authoredBounds : Bool
  prereleaseAdmitted : Bool
  deriving Repr

def engineAdmits (e : EngineEvidence) : Bool := e.authoredBounds && e.prereleaseAdmitted

/-- Crypto validity, strong keys, normalized origin and syntax are admitted
    witnesses in this domain model. The selected source/fixture supplies them;
    this is not an Ed25519, URL, JSON or SemVer implementation. -/
structure Request where
  keys : List Nat
  enrollmentShape : Bool
  envelopeShape : Bool
  documentShape : Bool
  signatures : List Signature
  expected : Binding
  document : Binding
  engine : EngineEvidence
  sequence : Nat
  payload : Nat
  floor : Option Floor
  deriving Repr

def unique (keys : List Nat) : Bool := decide keys.Nodup
def enrollmentAdmits (keys : List Nat) (shape : Bool) : Bool :=
  shape && !keys.isEmpty && decide (keys.length ≤ 16) && unique keys

def signatureAdmits (keys : List Nat) (s : Signature) : Bool :=
  s.algorithmKnown && s.canonical && (!(keys.contains s.key) || s.valid)

def authenticates (keys : List Nat) (shape : Bool) (signatures : List Signature) : Bool :=
  shape && !signatures.isEmpty && decide (signatures.length ≤ 16) &&
    unique (signatures.map Signature.key) && signatures.all (signatureAdmits keys) &&
    signatures.any (fun s => keys.contains s.key && s.valid)

def floorAdmits (expected : Binding) (sequence payload : Nat) (floor : Floor) : Bool :=
  floor.binding == expected && decide (floor.sequence ≤ sequence) &&
    (floor.sequence != sequence || floor.payload == payload)

def admitted (r : Request) : Bool :=
  enrollmentAdmits r.keys r.enrollmentShape && authenticates r.keys r.envelopeShape r.signatures &&
    r.documentShape && r.document == r.expected && engineAdmits r.engine &&
    r.floor.all (floorAdmits r.expected r.sequence r.payload)

def signingAdmits (payloadValid : Bool) (keys : List Nat) : Bool :=
  payloadValid && enrollmentAdmits keys true

/-- Optional typed cause present in the selected API error. This is not the
    production classifier's fallback or final CLI exit policy. -/
inductive TypedCause | absent | publisherAuthentication | incompatibleEngine
  deriving BEq, DecidableEq, Repr

def typedCause (r : Request) : TypedCause :=
  if !enrollmentAdmits r.keys r.enrollmentShape then .absent
  else if !authenticates r.keys r.envelopeShape r.signatures then .publisherAuthentication
  else if !r.documentShape || r.document != r.expected then .absent
  else if !engineAdmits r.engine then .incompatibleEngine
  else .absent

def candidate (r : Request) : Floor := ⟨r.expected, r.sequence, r.payload⟩

/-- Current cached method reuses next-offer admission. The proposed method adds
    exact agreement with the stored floor. New-offer advancement stays unchanged. -/
def cachedCurrent (recordShape observedPresent : Bool) (r : Request) : Bool :=
  recordShape && observedPresent && admitted r

def cachedExact (recordShape observedPresent : Bool) (r : Request) : Bool :=
  cachedCurrent recordShape observedPresent r && r.floor == some (candidate r)

def selectedGuard (recordShape : Bool) (r : Request) (selected : Floor) : Bool :=
  recordShape && r.floor == some selected

def savedChecksCurrent (recordShape observedPresent : Bool) (r : Request) (selected : Floor) : Bool :=
  selectedGuard recordShape r selected && cachedCurrent recordShape observedPresent r

def savedChecksProposed (recordShape observedPresent : Bool) (r : Request) (selected : Floor) : Bool :=
  selectedGuard recordShape r selected && cachedExact recordShape observedPresent r

/-- Mirrors an opaque authenticated-offer boundary; it is not durable state or
    host write authority. No native/browser storage implementation is modeled. -/
structure Offer where
  request : Request
  authentication : admitted request = true

structure Recipient where
  keys : List Nat
  floor : Option Floor
  installed : Nat
  deriving BEq, DecidableEq, Repr

def replaceKeys (s : Recipient) (keys : List Nat) : Recipient := {s with keys := keys}
def rollback (s : Recipient) (release : Nat) : Recipient := {s with installed := release}

/-- Host-current and authorization witnesses are separate caller premises.
    This models a successful commit, not filesystem publication or recovery. -/
def persist (s : Recipient) (offer : Offer) (hostCurrent authorized : Bool) : Recipient :=
  if hostCurrent && authorized then {s with floor := some (candidate offer.request)} else s

def selectionChecksCurrent (s : Recipient) (selected : Floor) (rootCurrent authenticationCurrent : Bool) : Bool :=
  rootCurrent && authenticationCurrent && s.floor == some selected

def binding : Binding := ⟨1, 1, 1⟩
def known : Signature := ⟨1, true, true, true⟩
def unknownBad : Signature := ⟨2, true, true, false⟩
def base : Request := ⟨[1], true, true, true, [known], binding, binding, ⟨true, true⟩, 3, 7, none⟩
def baselineFloor : Floor := candidate base
def baselineOffer : Offer := ⟨base, by decide⟩

theorem no_enrolled_keys_refuse (r : Request) : admitted {r with keys := []} = false := by
  simp [admitted, enrollmentAdmits]

theorem enrollment_shape_is_required (r : Request) :
    admitted {r with enrollmentShape := false} = false := by simp [admitted, enrollmentAdmits]

theorem downloaded_unknown_signer_is_not_enrollment :
    authenticates [1] true [⟨2, true, true, true⟩] = false := by decide

theorem one_known_signer_is_sufficient : authenticates [1, 2] true [known] = true := by decide

theorem unknown_bad_cosigner_does_not_authenticate_itself :
    authenticates [1] true [known, unknownBad] = true ∧
    authenticates [1] true [unknownBad] = false := by decide

theorem known_bad_cosigner_refuses_even_with_valid_signer :
    authenticates [1, 2] true [known, unknownBad] = false := by decide

theorem unknown_bad_metadata_still_refuses :
    authenticates [1] true [known, ⟨2, false, true, true⟩] = false := by decide

theorem duplicate_signatures_refuse : authenticates [1] true [known, known] = false := by decide

theorem noncanonical_context_refuses (r : Request) :
    admitted {r with envelopeShape := false} = false := by simp [admitted, authenticates]

theorem bounds_are_not_relaxed (pre : Bool) : engineAdmits ⟨false, pre⟩ = false := rfl

theorem stable_only_does_not_admit_fixture_prerelease : engineAdmits ⟨true, false⟩ = false := rfl

theorem identical_offer_retries : admitted {base with floor := some baselineFloor} = true := by decide

theorem earlier_offer_refuses :
    admitted {base with sequence := 2, floor := some baselineFloor} = false := by decide

theorem absence_of_floor_does_not_invent_replay_protection :
    admitted {base with sequence := 2} = true := by decide

theorem changed_bytes_at_same_sequence_refuse :
    admitted {base with payload := 8, floor := some baselineFloor} = false := by decide

theorem extra_signature_does_not_change_payload_floor :
    admitted {base with signatures := [known, unknownBad], floor := some baselineFloor} = true ∧
    candidate {base with signatures := [known, unknownBad]} = baselineFloor := by decide

theorem higher_sequence_can_choose_other_release :
    admitted {base with sequence := 4, payload := 8, floor := some baselineFloor} = true := by decide

theorem floor_binding_is_not_transferable :
    floorAdmits binding 4 8 ⟨⟨1, 2, 1⟩, 3, 7⟩ = false := by decide

theorem older_sequence_never_passes_floor (expected : Binding) (payload : Nat) (floor : Floor)
    (sequence : Nat) (h : sequence < floor.sequence) :
    floorAdmits expected sequence payload floor = false := by
  simp [floorAdmits, Nat.not_le_of_lt h]

theorem key_revocation_preserves_floor (s : Recipient) : (replaceKeys s []).floor = s.floor := rfl

theorem rollback_preserves_floor (s : Recipient) (release : Nat) :
    (rollback s release).floor = s.floor := rfl

theorem authenticated_offer_does_not_grant_write (s : Recipient) (offer : Offer) (current : Bool) :
    persist s offer current false = s := by simp [persist]

theorem stale_host_does_not_commit (s : Recipient) (offer : Offer) (authorized : Bool) :
    persist s offer false authorized = s := rfl

theorem observing_offer_does_not_install (s : Recipient) (offer : Offer) (current authorized : Bool) :
    (persist s offer current authorized).installed = s.installed := by unfold persist; split <;> rfl

theorem unrecorded_offer_does_not_authorize_acquisition (keys : List Nat) (installed : Nat)
    (selected : Floor) (root auth : Bool) :
    selectionChecksCurrent ⟨keys, none, installed⟩ selected root auth = false := by simp [selectionChecksCurrent]

theorem revoked_authentication_does_not_acquire (s : Recipient) (selected : Floor) (root : Bool) :
    selectionChecksCurrent s selected root false = false := by simp [selectionChecksCurrent]

theorem duplicate_signing_keys_refuse : signingAdmits true [1, 1] = false := by decide

theorem envelope_failure_preserves_typed_context :
    typedCause {base with envelopeShape := false} = .publisherAuthentication := by decide

theorem floor_refusal_does_not_claim_failed_signature :
    typedCause {base with sequence := 2, floor := some baselineFloor} = .absent := by decide

theorem engine_failure_is_a_different_typed_cause :
    typedCause {base with engine := ⟨false, true⟩} = .incompatibleEngine := by decide

def newerCached : Request := {base with sequence := 4, payload := 8, floor := some baselineFloor}

theorem current_cached_revalidation_can_return_unrecorded_floor :
    savedChecksCurrent true true newerCached baselineFloor = true ∧
    candidate newerCached ≠ baselineFloor := by decide

theorem proposed_cached_revalidation_refuses_that_mismatch :
    savedChecksProposed true true newerCached baselineFloor = false := by decide

theorem proposed_keeps_consistent_saved_observation :
    savedChecksProposed true true {base with floor := some baselineFloor} baselineFloor = true := by decide

theorem stricter_cached_rule_does_not_block_new_offer_admission :
    admitted newerCached = true ∧ cachedExact true true newerCached = false := by decide

theorem proposed_cached_selection_is_stricter (shape present : Bool) (r : Request) (selected : Floor)
    (h : savedChecksProposed shape present r selected = true) :
    savedChecksCurrent shape present r selected = true := by
  have parts : selectedGuard shape r selected = true ∧
      (cachedCurrent shape present r = true ∧ (r.floor == some (candidate r)) = true) := by
    simpa only [savedChecksProposed, cachedExact, Bool.and_eq_true] using h
  simp [savedChecksCurrent, parts.1, parts.2.1]

theorem missing_observation_never_authenticates (shape : Bool) (r : Request) :
    cachedCurrent shape false r = false := by simp [cachedCurrent]

end ApplicationStudy.EmpackChannels
