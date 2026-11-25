import Lean
import applications.empack.«content-kinds».ContentKinds
open Lean ApplicationStudy.ContentKinds
private structure MarkersWire where
  module : Bool
  pack : Bool
  assets : Bool
  data : Bool
  shaders : Bool
  projectRoot : Bool
  worldRoot : Bool
  deriving FromJson
private def markers (r : MarkersWire) : Markers := ⟨r.module,r.pack,r.assets,r.data,r.shaders,r.projectRoot,r.worldRoot⟩
private def kind (n : Nat) : Except String Kind :=
  match n with
  | 0 => .ok .mod
  | 1 => .ok .resource
  | 2 => .ok .shader
  | 3 => .ok .data
  | 4 => .ok .world
  | _ => .error "Unsupported content-kind research value."
private structure Admission where
  id : String
  explicit : Option Nat
  jar : Bool
  override : Option String
  validArchive : Bool
  markers : MarkersWire
  acceptUnknown : Bool
  dryRun : Bool
  worldRoots : Nat
  worldNonempty : Option Bool
  worldInside : Option Bool
  worldMembers : Nat
  deriving FromJson
private structure AdmissionOut where
  id : String
  admitted : Bool
  reason : Nat
  materialized : Bool
  outputs : Nat
  deriving ToJson
private def admission (r : Admission) : Except String AdmissionOut := do
  let explicit ← r.explicit.mapM kind
  let chosen := choose explicit r.jar
  if chosen == some .world && (folder .world r.override).isSome && r.validArchive && r.worldRoots == 1 then
    if r.worldNonempty.isNone || (r.worldNonempty == some true && r.worldInside.isNone) then
      throw "Unavailable needed world-root research observation."
    if r.worldNonempty == some true && r.worldInside == some true && r.worldMembers == 0 then
      throw "Inconsistent world-member research observation."
  let request : Request := ⟨explicit,r.jar,r.override,r.validArchive,markers r.markers,r.acceptUnknown,r.dryRun,
                            r.worldRoots,r.worldNonempty,r.worldInside,r.worldMembers⟩
  return ⟨r.id,admitted request,reason request,materialized request,outputs request⟩
private structure Metadata where
  id : String
  kind : Nat
  base : String
  filename : String
  key : String
  members : List String
  deriving FromJson
private structure MetadataOut where
  id : String
  content : String
  serverRequired : Bool
  sourceKind : String
  destinations : List String
  deriving ToJson
private def metadata (r : Metadata) : Except String MetadataOut := do
  let k ← kind r.kind
  return ⟨r.id,canonical k,cliServerRequired k,if k == .world then "local-files" else "local",
    destinations k r.base r.filename r.key r.members⟩
private structure Placement where
  id : String
  automatic : Bool
  fixed : String
  base : String
  filename : String
  deriving FromJson
private structure PlacementOut where
  id : String
  destination : String
  deriving ToJson
private structure Suffix where
  id : String
  regular : Bool
  filename : String
  deriving FromJson
private structure SuffixOut where
  id : String
  candidate : Bool
  deriving ToJson
private structure Input where
  schema : Nat
  admissions : List Admission
  metadata : List Metadata
  placements : List Placement
  suffixes : List Suffix
  deriving FromJson
private structure Output where
  admissions : List AdmissionOut
  metadata : List MetadataOut
  placements : List PlacementOut
  suffixes : List SuffixOut
  deriving ToJson
private def placementOut (r : Placement) : PlacementOut := ⟨r.id,placement r.automatic r.fixed r.base r.filename⟩
private def suffixOut (r : Suffix) : SuffixOut := ⟨r.id,vanillaRegularFileCandidate r.regular r.filename⟩
def main (args : List String) : IO UInt32 := do
  let path ← match args with
    | [p] => pure p
    | _ => throw (IO.userError "Supply one typed-content research packet.")
  let raw ← IO.FS.readFile path
  let result := do
    let j ← Json.parse raw
    let input ← fromJson? (α := Input) j
    if input.schema != 1 then throw "Unsupported typed-content research schema."
    let admissions ← input.admissions.mapM admission
    let metadata ← input.metadata.mapM metadata
    return (⟨admissions,metadata,input.placements.map placementOut,input.suffixes.map suffixOut⟩ : Output)
  match result with
  | .error message => (← IO.getStderr).putStrLn message; return 2
  | .ok result => (← IO.getStdout).putStrLn ((toJson result).compress); return 0
