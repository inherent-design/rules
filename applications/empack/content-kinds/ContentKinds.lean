namespace ApplicationStudy.ContentKinds

inductive Kind where
  | mod | resource | shader | data | world
  deriving DecidableEq, Repr

def choose (explicit : Option Kind) (jar : Bool) : Option Kind :=
  explicit.orElse (fun _ => if jar then some .mod else none)

def defaultFolder : Kind → Option String
  | .mod => some "mods"
  | .resource => some "resourcepacks"
  | .shader => some "shaderpacks"
  | _ => none

def folder (kind : Kind) (override : Option String) : Option String :=
  override.orElse (fun _ => defaultFolder kind)

def canonical : Kind → String
  | .mod => "mod"
  | .resource => "resource-pack"
  | .shader => "shader-pack"
  | .data => "data-pack"
  | .world => "world"

structure Markers where
  module : Bool
  pack : Bool
  assets : Bool
  data : Bool
  shaders : Bool
  projectRoot : Bool
  worldRoot : Bool
  deriving Repr

/-- Marker presence only; no semantic metadata/game/loader validation. -/
def recognized (kind : Kind) (m : Markers) : Bool :=
  match kind with
  | .mod => m.module
  | .resource => m.pack && (m.assets || !m.data)
  | .shader => m.shaders
  | .data => m.pack && m.data
  | .world => false

structure Request where
  explicit : Option Kind
  jar : Bool
  override : Option String
  validArchive : Bool
  markers : Markers
  acceptUnknown : Bool
  dryRun : Bool
  worldRoots : Nat
  worldNonempty : Option Bool
  worldInside : Option Bool
  worldMembers : Nat
  deriving Repr

/-- Research reasons:0 admitted;1 choose type;2 no folder;3 invalid archive;
    4 use project/world interpretation;5 unknown layout;6 world root;7 outside.
    These are not production error codes. Path/byte-budget/decoder admission is
    an external premise, not reimplemented by this policy projection. -/
def reason (r : Request) : Nat :=
  match choose r.explicit r.jar with
  | none => 1
  | some k =>
    if (folder k r.override).isNone then 2
    else if !r.validArchive then 3
    else if k == .world then
      if r.worldRoots != 1 || r.worldNonempty != some true then 6
      else if r.worldInside != some true then 7
      else 0
    else if r.markers.projectRoot || r.markers.worldRoot then 4
    else if recognized k r.markers || r.acceptUnknown then 0
    else 5

def admitted (r : Request) : Bool := reason r == 0
def materialized (r : Request) : Bool := admitted r && !r.dryRun
def outputs (r : Request) : Nat :=
  if !materialized r then 0
  else if choose r.explicit r.jar == some .world then r.worldMembers else 1

/-- CLI defaults in the selected profile, not a constraint on authored overrides. -/
def cliServerRequired (kind : Kind) : Bool := kind != .resource && kind != .shader

def destinations (kind : Kind) (base filename key : String) (members : List String) : List String :=
  if kind == .world then members.map (fun member => base ++ "/" ++ key ++ "/" ++ member)
  else [base ++ "/" ++ filename]

def placement (automatic : Bool) (fixed base filename : String) : String :=
  if automatic then base ++ "/" ++ filename else fixed

/-- Static projection of the selected vanilla detector's regular-file branch;
    symlink handling, directory metadata, and complete pack acceptance excluded. -/
def vanillaRegularFileCandidate (regular : Bool) (filename : String) : Bool :=
  regular && (match filename.toList.reverse with
    | 'p' :: 'i' :: 'z' :: '.' :: _ => true
    | _ => false)

/-- Proposed evidence reporting, not a game validator or a production API.
    Known layout and declared runtime agreement cannot fill absent checks. -/
def canClaimCompatible (layout : Bool) (format loader : Option Bool) : Bool :=
  layout && format == some true && loader == some true

private def empty : Markers := ⟨false,false,false,false,false,false,false⟩
private def modRequest : Request := ⟨some .mod,false,none,true,empty,false,false,0,none,none,0⟩

theorem jar_selects_mod : choose none true = some .mod := by rfl
theorem zip_needs_choice : choose none false = none := by rfl
theorem explicit_resource_overrides_extension : choose (some .resource) true = some .resource := by rfl
theorem data_has_no_default_folder : defaultFolder .data = none := by rfl
theorem world_has_no_default_folder : defaultFolder .world = none := by rfl
theorem override_preserved (k : Kind) (p : String) : folder k (some p) = some p := by rfl
theorem mixed_resource_recognized : recognized .resource ⟨false,true,true,true,false,false,false⟩ = true := by rfl
theorem mixed_data_recognized : recognized .data ⟨false,true,true,true,false,false,false⟩ = true := by rfl
theorem empty_pack_is_resource_shape : recognized .resource ⟨false,true,false,false,false,false,false⟩ = true := by rfl
theorem unknown_mod_refused : reason modRequest = 5 := by decide
theorem authored_acceptance_is_separate : reason {modRequest with acceptUnknown := true} = 0 := by decide
theorem acceptance_does_not_override_import :
    reason {modRequest with acceptUnknown := true, markers := {empty with projectRoot := true}} = 4 := by decide
theorem acceptance_does_not_override_world_marker :
    reason {modRequest with acceptUnknown := true, markers := {empty with worldRoot := true}} = 4 := by decide
theorem acceptance_does_not_override_structure : reason {modRequest with acceptUnknown := true, validArchive := false} = 3 := by decide
theorem dry_run_does_not_materialize (r : Request) : materialized {r with dryRun := true} = false := by simp [materialized]
theorem resource_client_only : cliServerRequired .resource = false := by rfl
theorem shader_client_only : cliServerRequired .shader = false := by rfl
theorem mod_both_sides : cliServerRequired .mod = true := by rfl
theorem world_both_sides : cliServerRequired .world = true := by rfl
theorem two_roots_refused : reason {modRequest with explicit := some .world, override := some "saves", worldRoots := 2} = 6 := by decide
theorem world_members_not_container :
    destinations .world "saves" "world.zip" "world" ["level.dat"] = ["saves/world/level.dat"] := by rfl
theorem opaque_name_preserved : destinations .resource "resourcepacks" "pack.JAR" "pack" [] = ["resourcepacks/pack.JAR"] := by rfl
theorem fixed_placement_ignores_layout (fixed base filename : String) : placement false fixed base filename = fixed := by rfl
theorem automatic_placement_uses_layout (fixed base filename : String) : placement true fixed base filename = base ++ "/" ++ filename := by rfl
theorem regular_jar_not_vanilla_candidate : vanillaRegularFileCandidate true "pack.jar" = false := by decide
theorem uppercase_zip_not_vanilla_candidate : vanillaRegularFileCandidate true "pack.ZIP" = false := by decide
theorem lowercase_zip_candidate : vanillaRegularFileCandidate true "pack.zip" = true := by decide
theorem missing_format_stays_unverified : canClaimCompatible true none (some true) = false := by decide
theorem missing_loader_stays_unverified : canClaimCompatible true (some true) none = false := by decide

end ApplicationStudy.ContentKinds
