namespace ApplicationStudy.EmpackPending

/-- Finite two-obligation profile. Record numbers label observed distinct opaque
    selectors; arithmetic below is a study revision, never a production hash. -/
structure State where
  record : Nat
  first : Bool
  second : Bool
  firstBacking : Nat
  secondBacking : Nat
  published : Bool
  deriving BEq, DecidableEq, Repr
structure Supply where
  key : Nat
  content : Nat
  deriving BEq, DecidableEq, Repr
structure Request where
  action : Nat
  selected : Nat
  files : List Supply
  discovered : List Nat
  deriving Repr
structure Result where
  code : Nat
  state : State
  deriving BEq, DecidableEq, Repr

/-- Tokens 1/2 denote independently checksum-verified fixture bytes; 0 is the
    deliberately wrong same-size bytes. This is not a digest implementation. -/
def validSupply (files : List Supply) : Bool :=
  (files.map (·.key)).eraseDups.length == files.length &&
    files.all (fun f => f.key < 2 && f.content == f.key + 1)
def has (files : List Supply) (discovered : List Nat) (key : Nat) : Bool :=
  files.any (fun f => f.key == key) || discovered.contains (key + 1)
def backingValid (s : State) : Bool :=
  (!s.first || s.firstBacking == 1) && (!s.second || s.secondBacking == 2)

def resume (s : State) (r : Request) : Result :=
  if !validSupply r.files then ⟨3,s⟩ else
  if !backingValid s then ⟨4,s⟩ else
  let first := s.first || has r.files r.discovered 0
  let second := s.second || has r.files r.discovered 1
  if first && second then ⟨6,{s with record := 0, first := false, second := false, published := true}⟩ else
  let changed := first != s.first || second != s.second
  ⟨5, { s with
    record := if changed then s.record + 1 else s.record
    first := first
    second := second
    firstBacking := if first then 1 else s.firstBacking
    secondBacking := if second then 2 else s.secondBacking }⟩

/-- Listing/show do not acquire input. Preview suppresses discovery/publication,
    but source resume still restores retained bytes and handles explicit supply.
    Other root/grant/resource/recipe gates and
    IO-error priority are outside this quiescent, admitted fixture projection. -/
def evaluate (s : State) (r : Request) : Result :=
  if r.action == 0 then ⟨0,s⟩ else
  if s.record == 0 || r.selected != s.record then ⟨2,s⟩ else
  if r.action == 1 then ⟨0,s⟩ else
  if r.action == 2 then
    if !validSupply r.files then ⟨3,s⟩ else if !backingValid s then ⟨4,s⟩ else ⟨1,s⟩
  else resume s r

def initial : State := ⟨1,false,false,0,0,false⟩
def retainedState : State := ⟨2,true,false,1,0,false⟩
def request (action selected : Nat) (files : List Supply := []) (found : List Nat := []) : Request :=
  ⟨action,selected,files,found⟩

theorem inspection_is_not_byte_verification (s : State) (id : Nat) (files : List Supply) (found : List Nat) :
    evaluate s ⟨0,id,files,found⟩ = ⟨0,s⟩ := rfl

theorem declined_selection_preserves_state (s : State) (r : Request)
    (ha : r.action ≠ 0) (hs : r.selected ≠ s.record) :
    evaluate s r = ⟨2,s⟩ := by simp [evaluate, ha, hs]

theorem preview_does_not_scan_download_directory :
    evaluate initial (request 2 1 [] [0]) = ⟨1,initial⟩ := rfl

theorem same_size_wrong_bytes_do_not_authorize_supply :
    evaluate initial (request 3 1 [⟨0,0⟩]) = ⟨3,initial⟩ := rfl

theorem unknown_key_refuses_without_mutation :
    evaluate initial (request 3 1 [⟨9,1⟩]) = ⟨3,initial⟩ := rfl

theorem repeated_key_refuses_even_for_correct_bytes :
    evaluate initial (request 3 1 [⟨0,1⟩,⟨0,1⟩]) = ⟨3,initial⟩ := rfl

theorem partial_supply_is_not_publication :
    evaluate initial (request 3 1 [⟨0,1⟩]) = ⟨5,retainedState⟩ := rfl

theorem previous_selector_stops_matching :
    evaluate retainedState (request 1 1) = ⟨2,retainedState⟩ := rfl

theorem saved_label_does_not_verify_corrupt_backing :
    let bad := {retainedState with firstBacking := 0}
    evaluate bad (request 0 2) = ⟨0,bad⟩ ∧ evaluate bad (request 3 2) = ⟨4,bad⟩ := by constructor <;> rfl

theorem duplicate_content_names_do_not_create_distinct_candidates :
    has [] [2,2] 1 = has [] [2] 1 := rfl

theorem completing_from_retained_and_discovered_bytes :
    evaluate retainedState (request 3 2 [] [0,1,2,2]) =
      ⟨6,⟨0,false,false,1,0,true⟩⟩ := rfl

theorem publication_does_not_mean_pending_content_eviction :
    (evaluate retainedState (request 3 2 [] [2])).state.firstBacking = 1 := rfl

end ApplicationStudy.EmpackPending
