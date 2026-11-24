namespace ApplicationStudy.Mo2Routing

/-- Exact name identities are opaque; the reserved name is a separate source
    classification. Neither field is a priority, path, or permission proof. -/
structure Mod where
  identity : Nat
  reserved : Bool
  regular : Bool
  deriving BEq, ReflBEq, LawfulBEq, DecidableEq, Repr
inductive Origin | mod (identity : Nat) | overwrite | saves (profile : Nat) | plugin (identity : Nat)
  deriving BEq, ReflBEq, LawfulBEq, DecidableEq, Repr
structure Row where
  origin : Origin
  destination : Nat
  directory : Bool
  createTarget : Bool
  deriving BEq, ReflBEq, LawfulBEq, DecidableEq, Repr
structure Plugin where
  enabled : Bool
  rows : List Row
  deriving BEq, ReflBEq, LawfulBEq, DecidableEq, Repr
structure Request where
  active : List Mod
  dataPaths : List Nat
  custom : Nat
  requestedProfile : Nat
  currentProfile : Nat
  currentLocal : Bool
  requestedLocal : Bool
  localFeature : Bool
  plugins : List Plugin
  deriving Repr
structure Result where
  mappings : Option (List Row)
  localWarning : Bool
  deriving BEq, ReflBEq, LawfulBEq, DecidableEq, Repr

def nameMatches (custom : Nat) (m : Mod) : Bool := !m.reserved && m.identity == custom

def currentTarget (r : Request) : Bool := r.custom == 0 || r.active.any (nameMatches r.custom)

def eligibleTarget (r : Request) : Bool :=
  r.custom == 0 || r.active.any (fun m => nameMatches r.custom m && m.regular)

def ordinary (r : Request) : List Row := r.active.flatMap fun m =>
  if !m.reserved && m.regular then
    r.dataPaths.map fun destination => ⟨.mod m.identity,destination,true,r.custom == m.identity⟩
  else []

/-- The fixture game feature returns one row for the supplied profile path.
    This does not implement arbitrary game-plugin save mapping semantics. -/
def saves (profile : Nat) : List Row := [⟨.saves profile,3,true,true⟩]

def overwrite (r : Request) : List Row :=
  r.dataPaths.map fun destination => ⟨.overwrite,destination,true,r.custom == 0⟩

def pluginRows (plugins : List Plugin) : List Row :=
  plugins.flatMap fun p => if p.enabled then p.rows else []

def assemble (r : Request) (profile : Nat) (saveEnabled : Bool) : List Row :=
  ordinary r ++ (if saveEnabled && r.localFeature then saves profile else []) ++ overwrite r ++ pluginRows r.plugins

def planCurrent (r : Request) : Result :=
  if currentTarget r then ⟨some (assemble r r.currentProfile r.currentLocal),r.currentLocal && !r.localFeature⟩
  else ⟨none,false⟩

/-- Design alternative only: regular custom target and selected-profile save
    context. Normal caller reachability and intended override policy need review. -/
def planProposed (r : Request) : Result :=
  if eligibleTarget r then ⟨some (assemble r r.requestedProfile r.requestedLocal),r.requestedLocal && !r.localFeature⟩
  else ⟨none,false⟩

def flagCount (destination : Nat) (rows : List Row) : Nat :=
  (rows.filter fun r => r.destination == destination && r.createTarget).length

def base : Request := ⟨[⟨5,true,false⟩,⟨1,false,true⟩,⟨2,false,false⟩],[1],0,1,1,false,false,true,[]⟩
def plugin : Plugin := ⟨true,[⟨.plugin 1,1,true,true⟩]⟩

theorem default_needs_no_active_mod : (planCurrent {base with active := []}).mappings = some [⟨.overwrite,1,true,true⟩] := by decide

theorem missing_custom_refuses : (planCurrent {base with custom := 4}).mappings = none := by decide

theorem exact_name_is_not_case_rank : (planCurrent {base with custom := 3}).mappings = none := by decide

theorem reserved_custom_is_not_active_target : currentTarget {base with custom := 5} = false := by decide

theorem regular_custom_receives_flag :
    (planCurrent {base with custom := 1}).mappings = some [⟨.mod 1,1,true,true⟩,⟨.overwrite,1,true,false⟩] := by decide

theorem active_nonregular_can_have_no_flagged_data_row :
    (planCurrent {base with custom := 2}).mappings = some [⟨.mod 1,1,true,false⟩,⟨.overwrite,1,true,false⟩] := by decide

theorem stronger_target_refuses_nonregular : (planProposed {base with custom := 2}).mappings = none := by decide

theorem eligible_target_implies_current (r : Request) (h : eligibleTarget r = true) : currentTarget r = true := by
  simp only [eligibleTarget,Bool.or_eq_true,List.any_eq_true,Bool.and_eq_true] at h
  simp only [currentTarget,Bool.or_eq_true,List.any_eq_true]
  rcases h with h | ⟨m,mem,matchName,_⟩
  · exact Or.inl h
  · exact Or.inr ⟨m,mem,matchName⟩

theorem requested_local_flag_does_not_change_current (r : Request) (enabled : Bool) :
    planCurrent {r with requestedLocal := enabled} = planCurrent r := rfl

/-- Active entries are already supplied from the selected profile. This is a
    label-only comparison holding that view fixed, not a real profile reload. -/
theorem requested_label_alone_keeps_supplied_view (r : Request) (profile : Nat) :
    planCurrent {r with requestedProfile := profile} = planCurrent r := rfl

theorem current_profile_controls_save_rows :
    (planCurrent {base with requestedProfile := 2,currentLocal := true}).mappings =
      some [⟨.mod 1,1,true,false⟩,⟨.saves 1,3,true,true⟩,⟨.overwrite,1,true,true⟩] := by decide

theorem proposed_profile_policy_is_different :
    (planProposed {base with requestedProfile := 2,currentLocal := true}).mappings =
      some [⟨.mod 1,1,true,false⟩,⟨.overwrite,1,true,true⟩] := by decide

theorem proposed_selected_save_source :
    (planProposed {base with requestedProfile := 2,requestedLocal := true}).mappings =
      some [⟨.mod 1,1,true,false⟩,⟨.saves 2,3,true,true⟩,⟨.overwrite,1,true,true⟩] := by decide

theorem unavailable_local_feature_warns_without_refusing :
    planCurrent {base with currentLocal := true,requestedLocal := true,localFeature := false} =
      ⟨some [⟨.mod 1,1,true,false⟩,⟨.overwrite,1,true,true⟩],true⟩ := by decide

theorem disabled_plugin_contributes_nothing (rows : List Row) : pluginRows [⟨false,rows⟩] = [] := rfl

theorem plugin_rows_preserve_order (rows : List Row) : pluginRows [⟨true,rows⟩] = rows := by simp [pluginRows]

theorem plugin_can_add_second_flag_at_same_path :
    flagCount 1 (assemble {base with plugins := [plugin]} 1 false) = 2 := by decide

theorem per_path_occurrences_are_preserved :
    (overwrite {base with dataPaths := [1,2]}).map Row.destination = [1,2] := rfl

theorem ordinary_filters_reserved_and_nonregular : (ordinary base).length = 1 := by decide

theorem refused_result_has_no_local_warning :
    planCurrent {base with custom := 4,currentLocal := true,requestedLocal := true,localFeature := false} = ⟨none,false⟩ := by decide

end ApplicationStudy.Mo2Routing
