namespace Host.Minecraft.ProviderAdaptation
set_option maxRecDepth 2048
/-- kind0 non-object,1 non-Euler,2 selected Euler. Scale0 absent,1 false,2 true,3 wrong type.
    Origin0 wrong shape,1 bad numeric component,2 selected finite coordinates.
    Numeric means selected bounded angle inputs with finite matrix construction. -/
structure Element where
  kind : Nat
  scale : Nat := 0
  cull : Bool := false
  origin : Nat := 0
  numeric : Bool := false
  deriving Repr
/-- Errors3 element,4 scale type,5 rescale,6 cull,7 origin,8 finite numbers. -/
def check (e : Element) : Nat :=
  if e.kind == 0 then 3 else if e.kind != 2 then 0
  else if e.scale == 3 then 4 else if e.scale == 2 then 5
  else if e.cull then 6 else if e.origin == 0 then 7
  else if e.origin == 1 || !e.numeric then 8 else 0
def audit : List Element → Nat
  | [] => 0
  | e :: es => let code := check e; if code != 0 then code else audit es
/-- [decision,rotated children,legacy elements];counts apply only to decision1 rewrite.
    Decision0 is unchanged by this helper,not validated;2 is its conversion limit. -/
def evaluate (ready : Bool) (es : List Element) : List Nat :=
  if !ready || !(es.any (fun e => e.kind == 2)) then [0,0,0]
  else if es.length > 128 then [2,0,0]
  else let error := audit es
       if error != 0 then [error,0,0]
       else [1,(es.filter (fun e => e.kind == 2)).length,(es.filter (fun e => e.kind == 1)).length]
def good : Element := ⟨2,0,false,2,true⟩
def legacy : Element := ⟨1,0,false,0,false⟩
theorem outer_gate_returns_unchanged (es : List Element) : evaluate false es = [0,0,0] := rfl
theorem no_euler_does_not_validate_nonobject : evaluate true [{kind := 0}] = [0,0,0] := by decide
theorem selected_euler_rewrites : evaluate true [good] = [1,1,0] := by decide
theorem mixed_retains_legacy_count : evaluate true [good,legacy] = [1,1,1] := by decide
theorem modern_branch_checks_sibling : evaluate true [{kind := 0},good] = [3,0,0] := by decide
theorem scale_type_precedes_other_errors (c : Bool) (o : Nat) (n : Bool) :
    check ⟨2,3,c,o,n⟩ = 4 := rfl
theorem rescale_precedes_cull (c : Bool) (o : Nat) (n : Bool) : check ⟨2,2,c,o,n⟩ = 5 := rfl
theorem cull_precedes_origin (o : Nat) (n : Bool) : check ⟨2,0,true,o,n⟩ = 6 := rfl
theorem origin_shape_refuses : check ⟨2,0,false,0,true⟩ = 7 := rfl
theorem bad_origin_numeric_refuses : check ⟨2,0,false,1,true⟩ = 8 := rfl
theorem nonfinite_angle_refuses : check ⟨2,0,false,2,false⟩ = 8 := rfl
theorem first_error_preserved (e : Element) (es : List Element) (h : check e ≠ 0) :
    audit (e::es) = check e := by simp [audit,h]
theorem oversized_legacy_is_unchanged : evaluate true (List.replicate 129 legacy) = [0,0,0] := by decide
theorem oversized_modern_refuses_before_origin :
    evaluate true (List.replicate 129 {kind := 2}) = [2,0,0] := by decide
end Host.Minecraft.ProviderAdaptation
