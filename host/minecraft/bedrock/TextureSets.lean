namespace MinecraftHost.Bedrock.TextureSets

/-- Resolved, unavailable, and unmeasured backing are different research states. -/
inductive Backing where
  | resolved | unavailable | unknown
  deriving DecidableEq, Repr
structure Input where
  color : Bool
  normal : Bool
  height : Bool
  mer : Bool
  mers : Bool
  backing : Backing
  vibrant : Bool
  textureObject : Bool
  uniformMersVariation : Bool
  deriving DecidableEq, Repr

/-- Independent issue bits; ordering and diagnostic wording are not an engine contract.
    Unknown backing is a research hold, not a documented invalidity. -/
def issues (i : Input) : Nat :=
  (if !i.color then 1 else 0) +
  (if i.normal && i.height then 2 else 0) +
  (if i.mer && i.mers then 4 else 0) +
  (if i.backing == .unavailable then 8 else 0) +
  (if i.backing == .unknown then 16 else 0) +
  (if i.vibrant && i.textureObject && i.height then 32 else 0) +
  (if i.vibrant && i.mers && i.uniformMersVariation then 64 else 0)

/-- Selected documented channel declarations only; no image/hex/JSON decoding.
    layer: color=0, normal=1, height=2, MER=3, MERS=4. -/
def channels (layer : Nat) (image : Bool) (count : Nat) : Bool :=
  if image then
    if layer == 2 then count == 1
    else if layer == 4 then count == 4
    else (layer == 0 || layer == 1 || layer == 3) && (count == 3 || count == 4)
  else
    (layer == 0 && count == 4) || (layer == 2 && count == 1) ||
    (layer == 3 && count == 3) || (layer == 4 && count == 4)

structure Image where
  pack : Nat
  name : Nat
  extension : Nat
  contentToken : Nat
  deriving DecidableEq, Repr
/-- ext 0/1/2/3 means tga/png/jpg/jpeg. Unique physical candidates are a premise. -/
def imageAt (pack name ext : Nat) (images : List Image) : Option Nat :=
  (images.find? (fun i => i.pack == pack && i.name == name && i.extension == ext)).map (·.contentToken)
def resolveImage (pack name : Nat) (images : List Image) : Option Nat :=
  imageAt pack name 0 images <|> imageAt pack name 1 images <|>
  imageAt pack name 2 images <|> imageAt pack name 3 images

structure Definition where
  name : Nat
  pack : Nat
  layers : Nat
  deriving DecidableEq, Repr
/-- Already eligible candidates, highest priority first. Invalid-candidate fallback is open. -/
def selectDefinition (name : Nat) (eligible : List Definition) : Option Definition :=
  eligible.find? (fun d => d.name == name)

/-- The documented PBR authoring route, not overall pack admission. -/
def pbrAuthoringDeclaration (pbr : Bool) (major minor patch : Nat) : Bool :=
  pbr && (major > 1 || (major == 1 && (minor > 21 || (minor == 21 && patch ≥ 120))))
/-- The raytraced alternative is retained independently. Neither flag qualifies a device. -/
def declarationEvidence (pbr raytraced : Bool) (major minor patch : Nat) : Nat × Nat :=
  (if pbrAuthoringDeclaration pbr major minor patch then 1 else 0,
   if raytraced then 1 else 0)
/-- Selected documented MERS competition, after interpreting bounded channel values. -/
def predominant (metal subsurface : Nat) : Nat × Nat :=
  if metal > subsurface then (metal,0) else (0,subsurface)

def baseline : Input := ⟨true,false,false,false,false,.resolved,false,false,false⟩
theorem ordinary_has_no_selected_issue : issues baseline = 0 := by decide
theorem absent_color_is_issue : issues {baseline with color := false} = 1 := by decide
theorem normal_height_conflict : issues {baseline with normal := true,height := true} = 2 := by decide
theorem mer_mers_conflict : issues {baseline with mer := true,mers := true} = 4 := by decide
theorem missing_backing_is_issue : issues {baseline with backing := .unavailable} = 8 := by decide
theorem unknown_is_not_missing : issues {baseline with backing := .unknown} = 16 := by decide
theorem independent_issues_accumulate : issues {baseline with color := false,normal := true,height := true,backing := .unknown} = 19 := by decide
theorem texture_object_height_restricted : issues {baseline with vibrant := true,textureObject := true,height := true} = 32 := by decide
theorem height_on_block_has_no_object_issue : issues {baseline with vibrant := true,height := true} = 0 := by decide
theorem uniform_mers_variation_is_separate : issues {baseline with vibrant := true,mers := true,uniformMersVariation := true} = 64 := by decide
theorem rgb_color_image_is_declared : channels 0 true 3 = true := by decide
theorem rgb_uniform_color_is_not_declared : channels 0 false 3 = false := by decide
theorem fourth_normal_channel_accepted : channels 1 true 4 = true := by decide
theorem mers_requires_four : channels 4 true 3 = false := by decide
theorem height_is_single_channel : channels 2 true 1 = true ∧ channels 2 true 4 = false := by decide
theorem foreign_pack_does_not_supply_backing : resolveImage 1 9 [⟨2,9,0,123⟩] = none := by decide
theorem extension_priority_within_pack : resolveImage 1 9 [⟨1,9,1,11⟩,⟨2,9,0,22⟩,⟨1,9,0,33⟩] = some 33 := by decide
theorem local_png_beats_foreign_tga : resolveImage 1 9 [⟨2,9,0,22⟩,⟨1,9,1,11⟩] = some 11 := by decide
theorem definitions_do_not_merge : selectDefinition 9 [⟨9,2,1⟩,⟨9,1,14⟩] = some ⟨9,2,1⟩ := by decide
theorem unrelated_definition_not_selected : selectDefinition 9 [⟨8,2,15⟩] = none := by decide
theorem capability_does_not_bypass_floor : pbrAuthoringDeclaration true 1 21 119 = false := by decide
theorem raytraced_alternative_is_independent : declarationEvidence false true 1 16 100 = (0,1) := by decide
theorem version_does_not_supply_capability : pbrAuthoringDeclaration false 1 26 30 = false := by decide
theorem tie_favors_subsurface (n : Nat) : predominant n n = (0,n) := by simp [predominant]
theorem greater_metal_suppresses_subsurface : predominant 255 64 = (255,0) := by decide
theorem greater_subsurface_suppresses_metal : predominant 64 128 = (0,128) := by decide

end MinecraftHost.Bedrock.TextureSets
