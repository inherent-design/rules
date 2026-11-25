namespace ApplicationStudy.ResticKeys

/-- Three exact fixture wrapper identities. A/B share credential1; C uses2.
    Credential labels are admitted native witnesses, not a cryptographic model. -/
structure State where
  a : Bool
  b : Bool
  c : Bool
  backing : Nat -- captured non-key repository byte image, not master-key bytes
  deriving BEq, DecidableEq, Repr
structure Result where
  state : State
  exitCode : Nat
  current : Nat -- key used for this process; not a persistent active-key setting
  deriving Repr
def present (s : State) (id : Nat) : Bool :=
  match id with | 1 => s.a | 2 => s.b | 3 => s.c | _ => false
def accepts (s : State) (id password : Nat) : Bool :=
  present s id && (if id == 3 then password == 2 else password == 1)
def access (s : State) (password hint : Nat) : Nat :=
  if accepts s hint password then hint else
  if accepts s 1 password then 1 else if accepts s 2 password then 2 else
  if accepts s 3 password then 3 else 0
def without (s : State) (id : Nat) : State :=
  match id with
  | 1 => {s with a := false}
  | 2 => {s with b := false}
  | 3 => {s with c := false}
  | _ => s
/-- Successful add/verify and replacement operations under their native profile.
    No save, verification, removal, crypto, or concurrent backend failure model. -/
def run (s : State) (kind password hint target : Nat) : Result :=
  let current := access s password hint
  if current == 0 then ⟨s,12,0⟩ else
  match kind with
  | 1 => ⟨{s with b := true},0,2⟩ -- add wrapper under same credential
  | 2 => ⟨{(without s current) with c := true},0,3⟩ -- verified new wrapper, remove old
  | 3 => if target == current || !present s target then ⟨s,1,current⟩
         else ⟨without s target,0,current⟩
  | 4 => ⟨s,1,current⟩ -- empty new password refused before adding a wrapper
  | _ => ⟨s,0,current⟩ -- list/access/dump; not a content-integrity guarantee
def initial : State := ⟨true,false,false,1⟩
def duplicate : State := ⟨true,true,false,1⟩
def changed : State := ⟨false,true,true,1⟩

theorem access_is_not_a_persistent_current_setting :
    (run duplicate 0 1 1 0).current = 1 ∧ (run duplicate 0 1 2 0).current = 2 := by decide
theorem add_same_password_keeps_both_wrappers :
    (run initial 1 1 1 0).state = duplicate := by decide
theorem another_wrapper_does_not_allow_removing_current :
    (run duplicate 3 1 1 1).exitCode = 1 ∧ (run duplicate 3 1 1 1).state = duplicate := by decide
theorem password_change_replaces_only_the_used_wrapper :
    (run duplicate 2 1 1 0).state = changed := by decide
theorem old_password_still_opens_its_other_wrapper :
    (run changed 0 1 2 0).exitCode = 0 ∧ (run changed 0 1 2 0).current = 2 := by decide
theorem new_password_opens_the_new_wrapper :
    (run changed 0 2 3 0).current = 3 := by decide
theorem wrong_password_cannot_add :
    (run changed 1 3 0 0).state = changed ∧ (run changed 1 3 0 0).exitCode = 12 := by decide
theorem empty_new_password_does_not_add :
    (run changed 4 2 3 0).state = changed ∧ (run changed 4 2 3 0).exitCode = 1 := by decide
theorem removal_can_revoke_another_wrappers_local_access :
    (run (run changed 3 1 2 3).state 0 2 3 0).exitCode = 12 := by decide
theorem remaining_current_wrapper_cannot_be_removed :
    (run (without changed 3) 3 1 2 2).exitCode = 1 := by decide
theorem unknown_wrapper_removal_is_a_refusal :
    (run changed 3 1 2 4).state = changed ∧ (run changed 3 1 2 4).exitCode = 1 := by decide
theorem backing_image_is_preserved (s : State) (k p h t : Nat) :
    (run s k p h t).state.backing = s.backing := by
  simp only [run]; split
  · rfl
  · split <;> try rfl
    · simp [without]; split <;> rfl
    · split
      · rfl
      · simp [without]; split <;> rfl

end ApplicationStudy.ResticKeys
