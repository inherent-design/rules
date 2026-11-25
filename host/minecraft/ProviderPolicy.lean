namespace Host.Minecraft.ProviderPolicy
/-- Selected metadata statuses:0 disabled,1 wrong side,2 missing,3 eligible,4 rejected.
    Only MODEL_ROTATIONS/ITEM_DEFINITIONS enabled;all unrelated features disabled. -/
def feature (enabled client : Bool) (modefite : Nat) : Nat :=
  if !enabled then 0 else if !client then 1 else if modefite == 0 then 2
  else if modefite == 1 then 3 else 4
def setting (value : Nat) : Bool := value != 0
/-- [returned/throw/not-invoked,rotation status,item status,candidate count,error feature].
    Status5 means no returned feature record;error feature2 means none.
    Peer presence is supplied metadata,not a runtime coexistence witness. -/
def evaluate (selected rotation items client : Bool) (modefite : Nat) (_polytone : Bool) : List Nat :=
  if !selected then [2,5,5,0,2]
  else
    let a := feature rotation client modefite
    let b := feature items client modefite
    if a == 4 || b == 4 then [1,5,5,0,if a == 4 then 0 else 1]
    else [0,a,b,(if a == 3 then 1 else 0)+(if b == 3 then 6 else 0),2]
theorem procedure_not_selected (r i c p : Bool) (v : Nat) :
    evaluate false r i c v p = [2,5,5,0,2] := rfl
theorem disabled_skips_dependency (c : Bool) (v : Nat) : feature false c v = 0 := rfl
theorem side_precedes_dependency (v : Nat) : feature true false v = 1 := rfl
theorem missing_is_inactive : feature true true 0 = 2 := rfl
theorem exact_metadata_is_eligible : feature true true 1 = 3 := rfl
theorem other_version_is_rejected : feature true true 2 = 4 := rfl
theorem polytone_presence_does_not_change_selected_eligibility (s r i c p q : Bool) (v : Nat) :
    evaluate s r i c v p = evaluate s r i c v q := rfl
theorem polytone_does_not_substitute_for_modefite :
    evaluate true true true true 0 true = [0,2,2,0,2] := rfl
theorem version_refusal_returns_no_feature_record :
    evaluate true true true true 2 false = [1,5,5,0,0] := rfl
theorem item_only_refusal_identifies_item_feature :
    evaluate true false true true 2 false = [1,5,5,0,1] := rfl
theorem disabled_features_do_not_reject_other_version (c p : Bool) :
    evaluate true false false c 2 p = [0,0,0,0,2] := rfl
theorem wrong_side_does_not_reject_other_version :
    evaluate true true true false 2 false = [0,1,1,0,2] := rfl
theorem omitted_selected_setting_is_enabled : setting 2 = true := rfl
theorem selected_candidates_are_one_plus_six :
    evaluate true true true true 1 false = [0,3,3,7,2] := rfl
end Host.Minecraft.ProviderPolicy
