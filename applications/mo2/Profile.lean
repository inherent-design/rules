namespace ApplicationStudy.Mo2Profile

inductive Policy | free | alwaysOn | alwaysOff deriving BEq, DecidableEq, Repr

/-- Indices are from a fixed, admitted catalog. Codecs require contiguous IDs;
    this is not a stable mod identity across catalog refreshes. -/
structure Entry where
  id : Nat
  policy : Policy
  enabled : Bool
  deriving DecidableEq, Repr

def singleValue : Policy → Bool → Bool
  | .free, wanted => wanted
  | .alwaysOn, _ => true
  | .alwaysOff, _ => false

def batchValue (entry : Entry) (wanted : Bool) : Bool :=
  if wanted then if entry.policy == .alwaysOff then entry.enabled else true
  else if entry.policy == .alwaysOn then entry.enabled else false

def findEntry (id : Nat) : List Entry → Option Entry
  | [] => none
  | entry :: tail => if entry.id == id then some entry else findEntry id tail

def setEnabled (id : Nat) (enabled : Bool) : List Entry → List Entry
  | [] => []
  | entry :: tail =>
    if entry.id == id then { entry with enabled } :: tail
    else entry :: setEnabled id enabled tail

structure Work where
  entries : List Entry
  dirty : List Nat := []
  errors : Nat := 0
  deriving Repr

def request (batch : Bool) (id : Nat) (wanted : Bool) (work : Work) : Work :=
  match findEntry id work.entries with
  | none => { work with errors := work.errors + 1 }
  | some entry =>
    let value := if batch then batchValue entry wanted else singleValue entry.policy wanted
    if entry.enabled == value then work
    else { work with entries := setEnabled id value work.entries, dirty := work.dirty ++ [id] }

def pass (wanted : Bool) (ids : List Nat) (work : Work) : Work :=
  ids.foldl (fun next id => request true id wanted next) work

structure Result where
  entries : List Entry
  signals : List (List Nat)
  loggedErrors : Nat
  threw : Bool
  deriving Repr

def notifications (dirty : List Nat) : List (List Nat) := if dirty.isEmpty then [] else [dirty]

def single (entries : List Entry) (id : Nat) (wanted : Bool) : Result :=
  let work := request false id wanted ⟨entries, [], 0⟩
  ⟨work.entries, notifications work.dirty, 0, work.errors != 0⟩

def batch (entries : List Entry) (enable disable : List Nat) : Result :=
  let work := pass false disable (pass true enable ⟨entries, [], 0⟩)
  ⟨work.entries, notifications work.dirty, work.errors, false⟩

theorem single_forces_on (wanted : Bool) : singleValue .alwaysOn wanted = true := rfl
theorem single_forces_off (wanted : Bool) : singleValue .alwaysOff wanted = false := rfl
theorem single_free_uses_request (wanted : Bool) : singleValue .free wanted = wanted := rfl

theorem setting_retains_catalog_length (id : Nat) (enabled : Bool) (entries : List Entry) :
    (setEnabled id enabled entries).length = entries.length := by
  induction entries with
  | nil => rfl
  | cons entry tail ih =>
    simp only [setEnabled]
    split <;> simp_all

theorem valid_always_on_survives_batch (id : Nat) (wanted : Bool) :
    batchValue ⟨id, .alwaysOn, true⟩ wanted = true := by cases wanted <;> rfl

theorem valid_always_off_survives_batch (id : Nat) (wanted : Bool) :
    batchValue ⟨id, .alwaysOff, false⟩ wanted = false := by cases wanted <;> rfl

theorem batch_does_not_repair_inconsistent_forced_state :
    batchValue ⟨0, .alwaysOn, false⟩ false = false := rfl

theorem duplicate_notification_can_have_no_net_edit :
    (batch [⟨0, .free, false⟩] [0] [0]).signals = [[0, 0]] ∧
    (batch [⟨0, .free, false⟩] [0] [0]).entries = [⟨0, .free, false⟩] := ⟨rfl, rfl⟩

theorem invalid_single_preserves_state :
    (single [⟨0, .free, false⟩] 9 true).entries = [⟨0, .free, false⟩] ∧
    (single [⟨0, .free, false⟩] 9 true).threw = true := ⟨rfl, rfl⟩

/-- Proposed completion evidence, not an existing MO2 receipt. Signal delivery
    does not construct it. Environment includes the remaining admitted input
    image, such as game files, archive activation, and plugin/configuration
    rules. Input discovery and stability are premises, not inferred from IDs.
    Profile file persistence remains independent. -/
structure ViewReceipt where
  profileImage : Nat
  catalogImage : Nat
  environmentImage : Nat
  completed : Bool

def viewReady (profile catalog environment : Nat) (receipt : Option ViewReceipt) : Bool :=
  match receipt with
  | none => false
  | some r => r.completed && r.profileImage == profile && r.catalogImage == catalog && r.environmentImage == environment

theorem no_receipt_is_not_ready (profile catalog environment : Nat) : viewReady profile catalog environment none = false := rfl
theorem matching_completed_view_is_ready (profile catalog environment : Nat) :
    viewReady profile catalog environment (some ⟨profile, catalog, environment, true⟩) = true := by simp [viewReady]

theorem stale_profile_view_is_not_ready (profile old catalog environment : Nat) (h : old ≠ profile) :
    viewReady profile catalog environment (some ⟨old, catalog, environment, true⟩) = false := by simp [viewReady, h]

theorem stale_catalog_view_is_not_ready (profile old catalog environment : Nat) (h : old ≠ catalog) :
    viewReady profile catalog environment (some ⟨profile, old, environment, true⟩) = false := by simp [viewReady, h]

theorem stale_environment_view_is_not_ready (profile catalog old environment : Nat) (h : old ≠ environment) :
    viewReady profile catalog environment (some ⟨profile, catalog, old, true⟩) = false := by simp [viewReady, h]

end ApplicationStudy.Mo2Profile
