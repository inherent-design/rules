namespace MinecraftHost.Bedrock.SchemaContracts

/-- Exact schema declarations, not runtime capabilities. The source compiler verifies
    required fields, types, enums, local references, and open additional properties. -/
structure CullingSchema where
  conditionDeclared : Bool
  opaqueDeclared : Bool
  opaqueDefaultAnnotation : Bool
  deriving DecidableEq, Repr
structure Rule where
  object : Bool
  direction : Bool
  geometry : Bool
  bone : Bool
  cube : Bool
  face : Bool
  condition : Nat
  opaqueState : Nat
  deriving DecidableEq, Repr
structure Culling where
  object : Bool
  description : Bool
  identifier : Bool
  rulesArray : Bool
  rules : List Rule
  deriving DecidableEq, Repr

/-- condition: absent=0, selected enum member=1, other=2.
    opaqueState: absent=0, true=1, false=2, other=3. Unknown properties stay unconstrained. -/
def validRule (s : CullingSchema) (r : Rule) : Bool :=
  r.object && r.direction && r.geometry && r.bone && r.cube && r.face &&
  (!s.conditionDeclared || r.condition < 2) && (!s.opaqueDeclared || r.opaqueState < 3)
def validCulling (s : CullingSchema) (r : Culling) : Bool :=
  r.object && r.description && r.identifier && r.rulesArray && r.rules.all (validRule s)
/-- Only the selected required-string component grammar, not identifier resolution. -/
def validBiomeIdentifier (object requiredString : Bool) : Bool := object && requiredString

def legacy : CullingSchema := ⟨false,false,false⟩
def newer : CullingSchema := ⟨true,true,false⟩
def annotated : CullingSchema := ⟨true,true,true⟩
def ordinaryRule : Rule := ⟨true,true,true,true,true,true,0,0⟩
def ordinary : Culling := ⟨true,true,true,true,[ordinaryRule]⟩

theorem ordinary_admitted : validCulling newer ordinary = true := by decide
theorem root_object_required : validCulling newer {ordinary with object := false} = false := by decide
theorem description_required : validCulling newer {ordinary with description := false} = false := by decide
theorem identifier_required : validCulling newer {ordinary with identifier := false} = false := by decide
theorem rules_array_required : validCulling newer {ordinary with rulesArray := false} = false := by decide
theorem empty_rule_list_admitted : validCulling newer {ordinary with rules := []} = true := by decide
theorem direction_required : validRule newer {ordinaryRule with direction := false} = false := by decide
theorem geometry_required : validRule newer {ordinaryRule with geometry := false} = false := by decide
theorem bone_required : validRule newer {ordinaryRule with bone := false} = false := by decide
theorem negative_cube_refuses : validRule newer {ordinaryRule with cube := false} = false := by decide
theorem unknown_face_refuses : validRule newer {ordinaryRule with face := false} = false := by decide
theorem absent_condition_admitted : validRule newer ordinaryRule = true := by decide
theorem known_bad_condition_refuses : validRule newer {ordinaryRule with condition := 2} = false := by decide
theorem undeclared_condition_not_constrained : validRule legacy {ordinaryRule with condition := 2} = true := by decide
theorem known_bad_opaque_refuses : validRule newer {ordinaryRule with opaqueState := 3} = false := by decide
theorem undeclared_opaque_not_constrained : validRule legacy {ordinaryRule with opaqueState := 3} = true := by decide
theorem default_annotation_not_a_validation_assertion (s : CullingSchema) (r : Rule) :
    validRule {s with opaqueDefaultAnnotation := !s.opaqueDefaultAnnotation} r = validRule s r := rfl
theorem default_annotation_not_a_container_assertion (s : CullingSchema) (r : Culling) :
    validCulling {s with opaqueDefaultAnnotation := !s.opaqueDefaultAnnotation} r = validCulling s r := rfl
theorem explicit_false_remains_admitted : validRule annotated {ordinaryRule with opaqueState := 2} = true := by decide
theorem annotated_absence_remains_admitted : validRule annotated ordinaryRule = true := by decide
theorem multiple_rules_all_checked : validCulling newer {ordinary with rules := [ordinaryRule,{ordinaryRule with direction := false}]} = false := by decide
theorem duplicate_rules_not_rejected : validCulling newer {ordinary with rules := [ordinaryRule,ordinaryRule]} = true := by decide
theorem component_object_required : validBiomeIdentifier false true = false := rfl
theorem present_component_requires_string : validBiomeIdentifier true false = false := rfl
theorem string_admission_separate_from_resolution : validBiomeIdentifier true true = true := rfl

end MinecraftHost.Bedrock.SchemaContracts
