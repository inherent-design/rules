import Lean
import applications.empack.selection.SelectionPolicy
open Lean ApplicationStudy.SelectionPolicy
private def preference (s : String) : Except String Preference :=
  match s with
  | "stable-only" => .ok .stableOnly
  | "prefer-stable" => .ok .preferStable
  | "any" => .ok .any
  | _ => .error "Unsupported research preference."
private def key (s : String) : Except String Key :=
  match s with
  | "a" => .ok .a
  | "b" => .ok .b
  | "c" => .ok .c
  | "d" => .ok .d
  | _ => .error "Unsupported research key."
private def spelling : Preference → String
  | .stableOnly => "stable-only" | .preferStable => "prefer-stable" | .any => "any"
private structure PreferenceWire where
  id : String
  project : String
  root : Option String
  operation : Option String
  rootApplies : Bool
  deriving FromJson
private structure PreferenceOut where
  id : String
  actual : String
  deriving ToJson
private structure AdmissionWire where
  id : String
  pinned : Bool
  preferencePresent : Bool
  deriving FromJson
private structure AdmissionOut where
  id : String
  accepted : Bool
  deriving ToJson
private structure PinWire where
  key : String
  version : Nat
  deriving FromJson
private structure UpdateWire where
  id : String
  key : String
  held : Bool
  version : Nat
  request : Option PinWire
  runtimeMismatch : Bool
  foreignIdentity : Bool
  evidenceMatches : Bool
  deriving FromJson
private structure UpdateOut where
  id : String
  accepted : Bool
  failure : Option String
  afterAuthorPin : Option String
  afterPreference : Option String
  selected : Option Nat
  changed : Option (List String)
  existing : Option (List String)
  afterRoots : Option (List String)
  inputUnchanged : Bool
  otherIntentPreserved : Option Bool
  deriving ToJson
private def pref (r : PreferenceWire) : Except String PreferenceOut := do
  let p ← preference r.project
  let root ← r.root.mapM preference
  let operation ← r.operation.mapM preference
  return ⟨r.id,spelling (effective p root operation r.rootApplies)⟩
private def update (r : UpdateWire) : Except String UpdateOut := do
  let k ← key r.key
  if k == .b || !(r.version == 1 || r.version == 2) then throw "Outside research fixture profile."
  let requested ← r.request.mapM fun p => do
    let k ← key p.key
    if p.version < 1 || p.version > 3 then throw "Outside research exact-request profile."
    return (⟨k,p.version⟩ : ExactRequest)
  if r.evidenceMatches && !(k == .a && r.version == 1) then throw "Unsupported research evidence-control profile."
  let value : Update := ⟨k,r.held,r.version,requested,r.runtimeMismatch,r.foreignIdentity,r.evidenceMatches⟩
  let ok := accepted value
  return ⟨r.id,ok,failure value,if ok then some (authorPin value) else none,
    if ok then some (authorPreference value) else none,if ok then some r.version else none,
    if ok then some (changed value) else none,if ok then some [keyName k] else none,
    if ok then some (authorRoots value) else none,
    true,if ok then some true else none⟩
private structure Input where
  schema : Nat
  preferences : List PreferenceWire
  admissions : List AdmissionWire
  updates : List UpdateWire
  deriving FromJson
private structure Output where
  preferences : List PreferenceOut
  admissions : List AdmissionOut
  updates : List UpdateOut
  deriving ToJson
private def admission (r : AdmissionWire) : AdmissionOut :=
  ⟨r.id,validPinPreference r.pinned r.preferencePresent⟩
def main (args : List String) : IO UInt32 := do
  let path ← match args with | [p] => pure p | _ => throw (IO.userError "Supply one selection research packet.")
  let raw ← IO.FS.readFile path
  let result := do
    let j ← Json.parse raw
    let input ← fromJson? (α := Input) j
    if input.schema != 1 then throw "Unsupported selection research schema."
    let preferences ← input.preferences.mapM pref
    let updates ← input.updates.mapM update
    return (⟨preferences,input.admissions.map admission,updates⟩ : Output)
  match result with
  | .error message => (← IO.getStderr).putStrLn message; return 2
  | .ok result => (← IO.getStdout).putStrLn ((toJson result).compress); return 0
