namespace ApplicationStudy.EmpackRemoval

/-- Opaque exact record text is compared/retained, never used as a path or ID. -/
structure Node where
  key : Nat
  record : String
  coverage : Nat
  edgesPresent : Bool
  edges : List Nat
  deriving BEq, ReflBEq, LawfulBEq, DecidableEq, Repr
structure State where
  roots : List Nat
  nodes : List Node
  deriving BEq, ReflBEq, LawfulBEq, DecidableEq, Repr
inductive Mode | forget | content
  deriving BEq, DecidableEq, Repr
structure Failure where
  kind : String
  keys : List Nat
  deriving BEq, ReflBEq, LawfulBEq, DecidableEq, Repr
structure Removed where
  selected : List Nat
  removed : List Nat
  incomplete : List Nat
  after : State
  deriving BEq, ReflBEq, LawfulBEq, DecidableEq, Repr

def lookup (s : State) (k : Nat) : Option Node := s.nodes.find? (·.key == k)
def canonical (keys : List Nat) : List Nat := [1,2,3,4].filter keys.contains

def selectionFailure (s : State) (mode : Mode) : List Nat → List Nat → Option Failure
  | [],_ => none
  | k::rest,seen =>
    if (lookup s k).isNone then some ⟨"unknown",[k]⟩
    else if seen.contains k then some ⟨"duplicate",[k]⟩
    else if mode == .forget && !s.roots.contains k then some ⟨"not-root",[k]⟩
    else selectionFailure s mode rest (k::seen)

def dependents (s : State) (selected : List Nat) : List Nat :=
  (s.nodes.filter fun n => !selected.contains n.key && n.edges.any selected.contains).map (·.key)
def incomplete (s : State) (selected : List Nat) : List Nat :=
  (s.nodes.filter fun n => !selected.contains n.key && n.coverage != 0).map (·.key)

def finish (s : State) (selected : List Nat) (mode : Mode) (unknown : List Nat) : Removed :=
  ⟨selected,if mode == .content then selected else [],unknown,
    ⟨s.roots.filter (!selected.contains ·),if mode == .content then s.nodes.filter (!selected.contains ·.key) else s.nodes⟩⟩

/-- Fixed-key research projection. The decoder bounds states to admitted keys,
    ordered maps, coherent roots/edges, and known coverage variants. -/
def remove (s : State) (selection : List Nat) (mode : Mode) (ack : Bool) : Except Failure Removed :=
  match selectionFailure s mode selection [] with
  | some failure => .error failure
  | none =>
    let selected := canonical selection
    if mode == .forget then .ok (finish s selected mode [])
    else
      let required := dependents s selected
      let unknown := incomplete s selected
      if !required.isEmpty then .error ⟨"required",required⟩
      else if !unknown.isEmpty && !ack then .error ⟨"incomplete",unknown⟩
      else .ok (finish s selected mode unknown)

structure Readded where
  existing : List Nat
  changed : List Nat
  rejectExistingWouldAllow : Bool
  after : State
  deriving BEq, ReflBEq, LawfulBEq, DecidableEq, Repr

/-- Only the exact A→B request with identical records and retained B is modeled.
    Canonical aliases, version changes and general addition policies are excluded.
    The boolean is the inspected engine gate, not executed engine admission. -/
def readd (s : State) (request : State) (operation : String) : Except String Readded :=
  let existing := (lookup s 1).isSome
  if operation == "update" && !existing then .error "update-missing"
  else
    let roots := if operation == "add" || (operation == "adopt" && !existing) then [1] else s.roots
    let nodes := if existing then s.nodes else request.nodes.filter (·.key == 1) ++ s.nodes
    .ok ⟨if existing then [1] else [],if existing then [] else [1],!existing,⟨roots,nodes⟩⟩

def a : Node := ⟨1,"A",0,true,[2]⟩
def b : Node := ⟨2,"B",0,false,[]⟩
def c : Node := ⟨3,"C",0,false,[]⟩
def base : State := ⟨[1],[a,b,c]⟩
def request : State := ⟨[1],[a,b]⟩
def forgotten : State := ⟨[],[a,b,c]⟩
def deleted : State := ⟨[],[b,c]⟩

theorem content_does_not_collect_orphans :
    remove base [1] .content false = .ok ⟨[1],[1],[],deleted⟩ := by rfl
theorem demotion_preserves_all_records :
    remove base [1] .forget false = .ok ⟨[1],[],[],forgotten⟩ := by rfl
theorem transitive_is_not_a_demotable_root :
    remove base [2] .forget false = .error ⟨"not-root",[2]⟩ := by rfl
theorem mixed_demotion_returns_no_partial_candidate :
    remove base [1,2] .forget false = .error ⟨"not-root",[2]⟩ := by rfl
theorem acknowledge_cannot_override_known_edges :
    remove base [2] .content true = .error ⟨"required",[1]⟩ := by rfl
theorem known_edges_precede_unknown :
    remove ⟨[1],[a,b,{c with coverage := 2}]⟩ [2] .content false = .error ⟨"required",[1]⟩ := by rfl
theorem unrelated_partial_still_prevents_deletion :
    remove ⟨[1],[a,b,{c with coverage := 1}]⟩ [1] .content false = .error ⟨"incomplete",[3]⟩ := by rfl
theorem acknowledgement_retains_uncertainty :
    (remove ⟨[1],[a,b,{c with coverage := 1}]⟩ [1] .content true).map Removed.incomplete = .ok [3] := by rfl
theorem forget_ignores_coverage_without_deletion :
    (remove ⟨[1],[a,b,{c with coverage := 2}]⟩ [1] .forget false).map Removed.removed = .ok [] := by rfl
theorem selected_unknown_is_not_a_retained_dependent :
    (remove ⟨[1],[{a with coverage := 2},b,c]⟩ [1] .content false).map Removed.removed = .ok [1] := by rfl
theorem entire_cycle_can_be_selected :
    (remove ⟨[1],[a,{b with edgesPresent := true,edges := [1]},c]⟩ [1,2] .content false).map (·.after.nodes) = .ok [c] := by rfl
theorem duplicate_selection_is_an_error :
    remove base [1,1] .content false = .error ⟨"duplicate",[1]⟩ := by rfl
theorem unknown_batch_key_returns_no_candidate :
    remove base [1,4] .content false = .error ⟨"unknown",[4]⟩ := by rfl
theorem unlisted_record_is_explicitly_removable :
    (remove base [3] .content false).map (·.after.roots) = .ok [1] := by rfl
theorem successful_forget_keeps_nodes (s : State) (selected : List Nat) :
    (finish s selected .forget []).after.nodes = s.nodes := rfl
theorem readding_retained_record_can_change_only_roots :
    readd forgotten request "add" = .ok ⟨[1],[],false,base⟩ := by rfl
theorem adoption_does_not_repromote_retained_record :
    readd forgotten request "adopt" = .ok ⟨[1],[],false,forgotten⟩ := by rfl
theorem update_does_not_repromote_retained_record :
    readd forgotten request "update" = .ok ⟨[1],[],false,forgotten⟩ := by rfl
theorem adoption_adds_previously_missing_root :
    readd deleted request "adopt" = .ok ⟨[],[1],true,base⟩ := by rfl
theorem update_is_not_installation :
    readd deleted request "update" = .error "update-missing" := by rfl

end ApplicationStudy.EmpackRemoval
