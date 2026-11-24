namespace ApplicationStudy.EmpackRootState

/-- This model assumes a complete quiescent directory view and attributed native
    root evidence. It models admission/selection, not error priority or IO. -/
inductive RootEvidence | same | missing | replaced
  deriving BEq, DecidableEq, Repr
structure Record where
  schema : Nat
  original : Option String
  token : Nat
  deriving BEq, DecidableEq, Repr
inductive Marker
  | absent
  | unreadable
  | wire (bytes : Nat) (decoded : Option Record)
  deriving BEq, DecidableEq, Repr
structure Entry where
  name : String
  directory : Bool
  marker : Marker
  children : List String
  deriving BEq, DecidableEq, Repr
structure Input where
  root : RootEvidence
  current : String
  suffix : String
  token : Option Nat
  entries : List Entry
  deriving BEq, DecidableEq, Repr
private def isPrefixChars : List Char → List Char → Bool
  | [],_ => true
  | _,[] => false
  | a::as,b::bs => a == b && isPrefixChars as bs
/-- Character-list implementation keeps the finite name laws kernel reducible. -/
def eligible (name suffix : String) : Bool :=
  isPrefixChars "project-".toList name.toList && isPrefixChars suffix.toList.reverse name.toList.reverse
inductive Verdict | ignored | unresolved | invalid | claim (name : String)
  deriving BEq, DecidableEq, Repr
def classify (current : String) (token : Option Nat) (entry : Entry) : Verdict :=
  if !entry.directory then .invalid else
  match entry.marker with
  | .absent =>
    if entry.name == current && entry.children.all (· == "state.lock") then .ignored else .unresolved
  | .unreadable => .invalid
  | .wire bytes decoded =>
    if bytes > 1024 then .invalid else
    match decoded with
    | none => .invalid
    | some r =>
      if r.schema != 1 || r.original != some entry.name then .invalid else
      match token with
      | none => .invalid
      | some token =>
        if r.token == token then .claim entry.name
        else if entry.name == current then .invalid else .ignored
structure Findings where
  invalid : Bool := false
  unresolved : Bool := false
  claims : List String := []
  deriving BEq, DecidableEq, Repr
def collect (current : String) (token : Option Nat) : List Entry → Findings
  | [] => {}
  | e::es =>
    let rest := collect current token es
    match classify current token e with
    | .ignored => rest
    | .invalid => { rest with invalid := true }
    | .unresolved => { rest with unresolved := true }
    | .claim name => { rest with claims := name :: rest.claims }
structure Outcome where
  ok : Bool
  selected : Option String
  found : Option Bool
  bound : Option String
  deriving BEq, DecidableEq, Repr
def refused : Outcome := ⟨false,none,none,none⟩
def evaluate (input : Input) : Outcome :=
  let entries := input.entries.filter (fun e => eligible e.name input.suffix)
  let facts := collect input.current input.token entries
  if input.root != .same || input.entries.length > 4096 || facts.invalid ||
      facts.unresolved || facts.claims.length > 1 then refused
  else
    let selected := facts.claims.head?
    ⟨true,selected,some selected.isSome,some (selected.getD input.current)⟩

theorem every_entry_counts_before_filtering (input : Input) (h : input.entries.length > 4096) :
    evaluate input = refused := by simp [evaluate,h]

private def current : String := "project-current-x"
private def old : String := "project-old-x"
private def emptySlot : Entry := ⟨current,true,.absent,[]⟩
private def oldSlot : Entry := ⟨old,true,.wire 120 (some ⟨1,some old,1⟩),["root-identity.json"]⟩
private def base (entries : List Entry) : Input := ⟨.same,current,"-x",some 1,entries⟩
theorem no_state_has_a_key_but_no_selected_record :
    evaluate (base []) = ⟨true,none,some false,some current⟩ := by decide
theorem current_empty_does_not_create_a_claim :
    evaluate (base [emptySlot]) = evaluate (base []) := by decide
theorem initializer_lock_does_not_create_a_claim :
    evaluate (base [{emptySlot with children := ["state.lock"]}]) = evaluate (base []) := by decide
theorem operation_lock_without_association_refuses :
    evaluate (base [{emptySlot with children := ["operation.lock"]}]) = refused := by decide
theorem historical_empty_is_not_current_initializer_scratch :
    evaluate (base [{emptySlot with name := old}]) = refused := by decide
theorem old_association_retains_its_physical_key :
    evaluate (base [oldSlot]) = ⟨true,some old,some true,some old⟩ := by decide
theorem a_valid_claim_does_not_hide_unresolved_state :
    evaluate (base [oldSlot,{emptySlot with children := ["journal.json"]}]) = refused := by decide
theorem multiple_claims_refuse :
    evaluate (base [oldSlot,⟨current,true,.wire 120 (some ⟨1,some current,1⟩),[]⟩]) = refused := by decide
theorem matching_token_does_not_authorize_misnamed_record :
    classify current (some 1) ⟨current,true,.wire 120 (some ⟨1,some old,1⟩),[]⟩ = .invalid := by decide
theorem unavailable_token_does_not_verify_a_record :
    classify current none oldSlot = .invalid := by decide
theorem foreign_old_record_is_not_selected :
    classify current (some 2) oldSlot = .ignored := by decide
theorem foreign_current_record_refuses :
    classify old (some 2) oldSlot = .invalid := by decide
theorem unsupported_schema_refuses :
    classify current (some 1) ⟨current,true,.wire 120 (some ⟨2,some current,1⟩),[]⟩ = .invalid := by decide
theorem byte_limit_is_inclusive :
    classify current (some 1) {oldSlot with marker := .wire 1024 (some ⟨1,some old,1⟩)} = .claim old := by decide
theorem oversize_does_not_become_absence :
    classify current (some 1) {oldSlot with marker := .wire 1025 (some ⟨1,some old,1⟩)} = .invalid := by decide
theorem malformed_does_not_become_absence :
    classify current (some 1) {oldSlot with marker := .wire 120 none} = .invalid := by decide
theorem nonregular_directory_entry_refuses :
    classify current (some 1) {emptySlot with directory := false} = .invalid := by decide
theorem nonfollow_record_failure_refuses :
    classify current (some 1) {emptySlot with marker := .unreadable} = .invalid := by decide
theorem unrelated_bad_state_is_not_opened :
    evaluate (base [⟨"other",false,.unreadable,[]⟩]) = evaluate (base []) := by decide
theorem changed_root_refuses :
    evaluate {base [oldSlot] with root := .replaced} = refused := by decide
theorem missing_root_refuses :
    evaluate {base [oldSlot] with root := .missing} = refused := by decide
/-- The candidate changes writer coordination; the current reader still refuses
    an unassociated operation-lock prefix. Neither outcome grants a write. -/
theorem candidate_initializer_coordination_avoids_only_this_prefix_refusal :
    evaluate (base [{emptySlot with children := ["state.lock"]}]) = ⟨true,none,some false,some current⟩ ∧
    evaluate (base [{emptySlot with children := ["operation.lock"]}]) = refused := by decide

end ApplicationStudy.EmpackRootState
