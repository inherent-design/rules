import Base

# Domain projection. Signature validity and normalized bindings are admitted
# fixture/source witnesses, not a cryptographic or URL implementation.
type Binding is Data:
  Binding{pack: Nat, origin: Nat, channel: Nat}

type Signature is Data:
  Signature{key: Nat, algorithm_known: Bool, canonical: Bool, valid: Bool}

type Floor is Data:
  Floor{binding: Binding, sequence: Nat, payload: Nat}

type Request is Data:
  Request{keys: List<&2, Nat>, enrollment_shape: Bool, envelope_shape: Bool, document_shape: Bool, signatures: List<&2, Signature>, expected: Binding, document: Binding, bounds: Bool, prerelease: Bool, sequence: Nat, payload: Nat, floor: Maybe<&2, Floor>}

type TypedCause is Data:
  NoTypedCause{}
  PublisherAuthentication{}
  IncompatibleEngine{}

def count(keys: List<&2, Nat>) -> Nat:
  match keys:
    case Nil{}: 0n
    case Con{head,tail}: Nat.add(1n,count(tail))

def unique(keys: List<&2, Nat>) -> Bool:
  match keys:
    case Nil{}: True{}
    case Con{head,+tail}: Bool.and(Bool.not(List.contains(Nat,Nat.is_eq,tail,head)),unique(tail))

def enrollment_admits(+keys: List<&2, Nat>, shape: Bool) -> Bool:
  Bool.and(shape,Bool.and(Nat.is_gt(count(keys),0n),Bool.and(Nat.is_le(count(keys),16n),unique(keys))))

def signature_count(sigs: List<&2, Signature>) -> Nat:
  match sigs:
    case Nil{}: 0n
    case Con{head,tail}: Nat.add(1n,signature_count(tail))

def has_key(sigs: List<&2, Signature>, +id: Nat) -> Bool:
  match sigs:
    case Nil{}: False{}
    case Con{head,tail}:
      match head:
        case Signature{key,algorithm_known,canonical,valid}: Bool.or(Nat.is_eq(key,id),has_key(tail,id))

def signature_unique(sigs: List<&2, Signature>) -> Bool:
  match sigs:
    case Nil{}: True{}
    case Con{head,+tail}:
      match head:
        case Signature{key,algorithm_known,canonical,valid}: Bool.and(Bool.not(has_key(tail,key)),signature_unique(tail))

def signature_admits(keys: List<&2, Nat>, s: Signature) -> Bool:
  match s:
    case Signature{key,algorithm_known,canonical,valid}: Bool.and(algorithm_known,Bool.and(canonical,Bool.or(Bool.not(List.contains(Nat,Nat.is_eq,keys,key)),valid)))

def all_signatures(+keys: List<&2, Nat>, sigs: List<&2, Signature>) -> Bool:
  match sigs:
    case Nil{}: True{}
    case Con{head,tail}: Bool.and(signature_admits(keys,head),all_signatures(keys,tail))

def known_valid(keys: List<&2, Nat>, s: Signature) -> Bool:
  match s:
    case Signature{key,algorithm_known,canonical,valid}: Bool.and(List.contains(Nat,Nat.is_eq,keys,key),valid)

def any_known_valid(+keys: List<&2, Nat>, sigs: List<&2, Signature>) -> Bool:
  match sigs:
    case Nil{}: False{}
    case Con{head,tail}: Bool.or(known_valid(keys,head),any_known_valid(keys,tail))

def authenticates(+keys: List<&2, Nat>, shape: Bool, +sigs: List<&2, Signature>) -> Bool:
  Bool.and(shape,Bool.and(Nat.is_gt(signature_count(sigs),0n),Bool.and(Nat.is_le(signature_count(sigs),16n),Bool.and(signature_unique(sigs),Bool.and(all_signatures(keys,sigs),any_known_valid(keys,sigs))))))

def same_binding(a: Binding, b: Binding) -> Bool:
  match a:
    case Binding{ap,ao,ac}:
      match b:
        case Binding{bp,bo,bc}: Bool.and(Nat.is_eq(ap,bp),Bool.and(Nat.is_eq(ao,bo),Nat.is_eq(ac,bc)))

def floor_admits(expected: Binding, +sequence: Nat, payload: Nat, f: Floor) -> Bool:
  match f:
    case Floor{binding,+old_sequence,old_payload}: Bool.and(same_binding(expected,binding),Bool.and(Nat.is_le(old_sequence,sequence),Bool.or(Bool.not(Nat.is_eq(old_sequence,sequence)),Nat.is_eq(old_payload,payload))))

def optional_floor(expected: Binding, sequence: Nat, payload: Nat, floor: Maybe<&2, Floor>) -> Bool:
  match floor:
    case None{}: True{}
    case Some{value}: floor_admits(expected,sequence,payload,value)

def admitted(r: Request) -> Bool:
  match r:
    case Request{+keys,enrollment_shape,envelope_shape,document_shape,signatures,+expected,document,bounds,prerelease,sequence,payload,floor}:
      Bool.and(enrollment_admits(keys,enrollment_shape),Bool.and(authenticates(keys,envelope_shape,signatures),Bool.and(document_shape,Bool.and(same_binding(document,expected),Bool.and(Bool.and(bounds,prerelease),optional_floor(expected,sequence,payload,floor))))))

def signing_admits(payload_valid: Bool, keys: List<&2, Nat>) -> Bool:
  enrollment_admits(keys,payload_valid)

def cause_engine(binding_valid: Bool, engine_valid: Bool) -> TypedCause:
  match binding_valid:
    case False{}: NoTypedCause{}
    case True{}:
      match engine_valid:
        case False{}: IncompatibleEngine{}
        case True{}: NoTypedCause{}

def cause_auth(enrollment_valid: Bool, authentication_valid: Bool, binding_valid: Bool, engine_valid: Bool) -> TypedCause:
  match enrollment_valid:
    case False{}: NoTypedCause{}
    case True{}:
      match authentication_valid:
        case False{}: PublisherAuthentication{}
        case True{}: cause_engine(binding_valid,engine_valid)

def typed_cause(r: Request) -> TypedCause:
  match r:
    case Request{+keys,enrollment_shape,envelope_shape,document_shape,signatures,expected,document,bounds,prerelease,sequence,payload,floor}:
      cause_auth(enrollment_admits(keys,enrollment_shape),authenticates(keys,envelope_shape,signatures),Bool.and(document_shape,same_binding(document,expected)),Bool.and(bounds,prerelease))

type Recipient is Data:
  Recipient{keys: List<&2, Nat>, floor: Maybe<&2, Floor>, installed: Nat}

def replace_keys(s: Recipient, keys: List<&2, Nat>) -> Recipient:
  match s:
    case Recipient{old_keys,floor,installed}: Recipient{keys,floor,installed}

def rollback(s: Recipient, installed: Nat) -> Recipient:
  match s:
    case Recipient{keys,floor,old_installed}: Recipient{keys,floor,installed}

def candidate(r: Request) -> Floor:
  match r:
    case Request{keys,enrollment_shape,envelope_shape,document_shape,signatures,expected,document,bounds,prerelease,sequence,payload,floor}: Floor{expected,sequence,payload}

def commit_if(allowed: Bool, s: Recipient, selected: Floor) -> Recipient:
  match allowed:
    case False{}: s
    case True{}:
      match s:
        case Recipient{keys,floor,installed}: Recipient{keys,Some{selected},installed}

# Unlike Lean's dependent Offer, this executable representation recomputes the
# admission predicate. Host-current and authorization remain separate premises.
def persist(s: Recipient, +r: Request, current: Bool, authorized: Bool) -> Recipient:
  commit_if(Bool.and(admitted(r),Bool.and(current,authorized)),s,candidate(r))

def same_floor(a: Floor, b: Floor) -> Bool:
  match a:
    case Floor{ab,as,ap}:
      match b:
        case Floor{bb,bs,bp}: Bool.and(same_binding(ab,bb),Bool.and(Nat.is_eq(as,bs),Nat.is_eq(ap,bp)))

def selected_floor(floor: Maybe<&2, Floor>, selected: Floor) -> Bool:
  match floor:
    case None{}: False{}
    case Some{value}: same_floor(value,selected)

def selection_checks_current(s: Recipient, selected: Floor, root_current: Bool, authentication_current: Bool) -> Bool:
  match s:
    case Recipient{keys,floor,installed}: Bool.and(root_current,Bool.and(authentication_current,selected_floor(floor,selected)))

law unknown_signer_cannot_enroll_itself:
  {authenticates(Con{1n,Nil{}},True{},Con{Signature{2n,True{},True{},True{}},Nil{}}) == False{} : Bool}
def unknown_signer_cannot_enroll_itself():
  {==}

law unknown_bad_cosigner_can_be_ignored:
  {authenticates(Con{1n,Nil{}},True{},Con{Signature{1n,True{},True{},True{}},Con{Signature{2n,True{},True{},False{}},Nil{}}}) == True{} : Bool}
def unknown_bad_cosigner_can_be_ignored():
  {==}

law known_bad_cosigner_refuses:
  {authenticates(Con{1n,Con{2n,Nil{}}},True{},Con{Signature{1n,True{},True{},True{}},Con{Signature{2n,True{},True{},False{}},Nil{}}}) == False{} : Bool}
def known_bad_cosigner_refuses():
  {==}

law duplicate_signing_input_refuses:
  {signing_admits(True{},Con{1n,Con{1n,Nil{}}}) == False{} : Bool}
def duplicate_signing_input_refuses():
  {==}

law earlier_floor_refuses:
  {floor_admits(Binding{1n,1n,1n},2n,7n,Floor{Binding{1n,1n,1n},3n,7n}) == False{} : Bool}
def earlier_floor_refuses():
  {==}

law identical_floor_retries:
  {floor_admits(Binding{1n,1n,1n},3n,7n,Floor{Binding{1n,1n,1n},3n,7n}) == True{} : Bool}
def identical_floor_retries():
  {==}

law changed_payload_same_sequence_refuses:
  {floor_admits(Binding{1n,1n,1n},3n,8n,Floor{Binding{1n,1n,1n},3n,7n}) == False{} : Bool}
def changed_payload_same_sequence_refuses():
  {==}

law key_revocation_preserves_floor:
  {replace_keys(Recipient{Con{1n,Nil{}},Some{Floor{Binding{1n,1n,1n},3n,7n}},5n},Nil{}) == Recipient{Nil{},Some{Floor{Binding{1n,1n,1n},3n,7n}},5n} : Recipient}
def key_revocation_preserves_floor():
  {==}

law rollback_preserves_floor:
  {rollback(Recipient{Con{1n,Nil{}},Some{Floor{Binding{1n,1n,1n},3n,7n}},5n},2n) == Recipient{Con{1n,Nil{}},Some{Floor{Binding{1n,1n,1n},3n,7n}},2n} : Recipient}
def rollback_preserves_floor():
  {==}

law unrecorded_offer_cannot_acquire:
  {selection_checks_current(Recipient{Con{1n,Nil{}},None{},5n},Floor{Binding{1n,1n,1n},3n,7n},True{},True{}) == False{} : Bool}
def unrecorded_offer_cannot_acquire():
  {==}

def request_floor(r: Request) -> Maybe<&2, Floor>:
  match r:
    case Request{keys,enrollment_shape,envelope_shape,document_shape,signatures,expected,document,bounds,prerelease,sequence,payload,floor}: floor

def cached_current(record_shape: Bool, observed_present: Bool, r: Request) -> Bool:
  Bool.and(record_shape,Bool.and(observed_present,admitted(r)))

def cached_exact(record_shape: Bool, observed_present: Bool, +r: Request) -> Bool:
  Bool.and(cached_current(record_shape,observed_present,r),selected_floor(request_floor(r),candidate(r)))

def optional_cached(record_shape: Bool, observed: Maybe<&2, Request>) -> Bool:
  match observed:
    case None{}: False{}
    case Some{r}: cached_current(record_shape,True{},r)

def optional_exact(record_shape: Bool, observed: Maybe<&2, Request>) -> Bool:
  match observed:
    case None{}: False{}
    case Some{r}: cached_exact(record_shape,True{},r)

type SavedOutcome is Data:
  NotDecoded{}
  Checked{guard: Bool, authenticated: Bool, exact: Bool, current_checks: Bool, proposed_checks: Bool}

def saved_fields(+guard: Bool, +authenticated: Bool, +exact: Bool) -> SavedOutcome:
  Checked{guard,authenticated,exact,Bool.and(guard,authenticated),Bool.and(guard,exact)}

# Each check is observed separately by the fixture. The conjunction describes
# source composition, not an end-to-end network/install execution trace.
def saved_outcome(record_shape: Bool, +observed: Maybe<&2, Request>, stored: Maybe<&2, Floor>, selected: Floor) -> SavedOutcome:
  match record_shape:
    case False{}: NotDecoded{}
    case True{}: saved_fields(selected_floor(stored,selected),optional_cached(True{},observed),optional_exact(True{},observed))

def fixed_request(sequence: Nat, payload: Nat, floor: Maybe<&2, Floor>) -> Request:
  Request{Con{1n,Nil{}},True{},True{},True{},Con{Signature{1n,True{},True{},True{}},Nil{}},Binding{1n,1n,1n},Binding{1n,1n,1n},True{},True{},sequence,payload,floor}

law current_cached_method_can_advance_unsaved_floor:
  {cached_current(True{},True{},fixed_request(4n,8n,Some{Floor{Binding{1n,1n,1n},3n,7n}})) == True{} : Bool}
def current_cached_method_can_advance_unsaved_floor():
  {==}

law proposed_cached_method_requires_exact_floor:
  {cached_exact(True{},True{},fixed_request(4n,8n,Some{Floor{Binding{1n,1n,1n},3n,7n}})) == False{} : Bool}
def proposed_cached_method_requires_exact_floor():
  {==}

law proposed_preserves_consistent_observation:
  {cached_exact(True{},True{},fixed_request(3n,7n,Some{Floor{Binding{1n,1n,1n},3n,7n}})) == True{} : Bool}
def proposed_preserves_consistent_observation():
  {==}

def main() -> IO(Unit):
  IO.print("Enrolled trust, authenticated offers, durable floors, and installation are separate facts.")
