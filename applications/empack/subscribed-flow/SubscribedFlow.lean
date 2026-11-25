import applications.empack.Channels
namespace ApplicationStudy.SubscribedFlow

/-- One local signed-input fixture. Labels distinguish channel payload, release,
    and physical file observations; the observer binds their actual hashes. -/
structure State where
  subscription : EmpackChannels.Recipient := ⟨[],none,0⟩
  payload : Nat := 0
  seed : Nat := 0
  note : Bool := false
  deriving DecidableEq, Repr

inductive Op where
  | enroll | previewA | observeA | installA | playerEdit | previewB | observeB
  | previewInstallB | missingInputB | installB | checkB | ensureOld | rollbackA
  | staleA | badSignature | checkRollback
  deriving DecidableEq, Repr

def request (s : State) (sequence payload : Nat) (valid : Bool) : EmpackChannels.Request :=
  ⟨s.subscription.keys,true,true,true,[⟨1,true,true,valid⟩],EmpackChannels.binding,EmpackChannels.binding,
   ⟨true,true⟩,sequence,payload,s.subscription.floor⟩

def observe (s : State) (sequence payload : Nat) (valid : Bool) : State :=
  let r := request s sequence payload valid
  if h : EmpackChannels.admitted r = true then
    {s with subscription := EmpackChannels.persist s.subscription ⟨r,h⟩ true true}
  else s

/-- Successful commits and selected explicit refusals. Caller/root/byte/current
    authority is a fixture premise; this is not a durable publication protocol. -/
def step (s : State) : Op → State
  | .enroll => {s with subscription := EmpackChannels.replaceKeys s.subscription [1]}
  | .observeA => observe s 1 1 true
  | .observeB => observe s 2 2 true
  | .installA => {s with subscription := {s.subscription with installed := 1},payload := 1,seed := 1}
  | .playerEdit => {s with seed := 2,note := true}
  | .installB => {s with subscription := {s.subscription with installed := 2},payload := 2}
  | .rollbackA => {s with subscription := EmpackChannels.rollback s.subscription 1,payload := 1}
  | .staleA => observe s 1 1 true
  | .badSignature => observe s 2 2 false
  | _ => s

def exit (s : State) : Op → Nat
  | .missingInputB => 1
  | .staleA => if EmpackChannels.admitted (request s 1 1 true) then 0 else 1
  | .badSignature => if EmpackChannels.admitted (request s 2 2 false) then 0 else 1
  | _ => 0

def view (s : State) : List Nat :=
  [if s.subscription.keys.isEmpty then 0 else 1,
   s.subscription.floor.map (·.sequence) |>.getD 0,
   s.subscription.floor.map (·.payload) |>.getD 0,
   s.subscription.installed,s.payload,s.seed,if s.note then 1 else 0]

def trace (s : State) : List Op → List (List Nat)
  | [] => []
  | op::ops => let after := step s op; (view after ++ [exit s op]) :: trace after ops

def sequence : List Op := [.enroll,.previewA,.observeA,.installA,.playerEdit,.previewB,
  .observeB,.previewInstallB,.missingInputB,.installB,.checkB,.ensureOld,.rollbackA,
  .staleA,.badSignature,.checkRollback]
def enrolled : State := step {} .enroll
def installedA : State := step (step enrolled .observeA) .installA
def floorBInstalledA : State := step (step installedA .playerEdit) .observeB
def installedB : State := step floorBInstalledA .installB

theorem enrollment_does_not_install : enrolled.subscription.installed = 0 := by rfl
theorem enrollment_does_not_observe : enrolled.subscription.floor = none := by rfl
theorem offer_preview_does_not_publish (s : State) : step s .previewB = s := by rfl
theorem local_install_preview_does_not_publish (s : State) : step s .previewInstallB = s := by rfl
theorem observed_offer_does_not_install : (step enrolled .observeA).subscription.installed = 0 := by decide
theorem first_signed_install : view installedA = [1,1,1,1,1,1,0] := by decide
theorem second_offer_keeps_old_install : view floorBInstalledA = [1,2,2,1,1,2,1] := by decide
theorem explicit_missing_input_refuses : exit floorBInstalledA .missingInputB = 1 := by rfl
theorem missing_input_keeps_offer (s : State) : step s .missingInputB = s := by rfl
theorem apply_does_not_replace_floor (s : State) : (step s .installB).subscription.floor = s.subscription.floor := by rfl
theorem apply_keeps_player_seed (s : State) : (step s .installB).seed = s.seed := by rfl
theorem apply_keeps_unowned_note (s : State) : (step s .installB).note = s.note := by rfl
theorem second_signed_install : view installedB = [1,2,2,2,2,2,1] := by decide
theorem old_consumer_retains_completed_release (s : State) : step s .ensureOld = s := by rfl
theorem rollback_does_not_lower_floor (s : State) : (step s .rollbackA).subscription.floor = s.subscription.floor := by rfl
theorem rollback_restores_payload : view (step installedB .rollbackA) = [1,2,2,1,1,2,1] := by decide
theorem stale_offer_refused : exit (step installedB .rollbackA) .staleA = 1 := by decide
theorem stale_offer_keeps_floor : step (step installedB .rollbackA) .staleA = step installedB .rollbackA := by decide
theorem bad_signature_refused : exit installedB .badSignature = 1 := by decide
theorem bad_signature_keeps_install : step installedB .badSignature = installedB := by decide
theorem unsigned_unenrolled_offer_refused : (observe {} 1 1 true).subscription.floor = none := by decide

end ApplicationStudy.SubscribedFlow
