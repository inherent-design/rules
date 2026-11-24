import Lean
import applications.prism.Components
open Lean ApplicationStudy.PrismComponents

private structure ReqInput where
  uid : String
  exact : String
  hint : String
  deriving FromJson

private structure ComponentInput where
  uid : String
  version : String
  dependencyOnly : Bool
  volatile : Bool
  custom : Bool
  disabled : Bool
  important : Bool
  requirements : List ReqInput
  deriving FromJson

private structure CaseInput where
  id : String
  components : List ComponentInput
  deriving FromJson

private structure CacheInput where
  id : String
  volatile : Bool
  deriving FromJson

private structure RemovalInput where
  id : String
  important : Bool
  patchWritable : Bool
  localJar : Bool
  jarWritable : Bool
  deriving FromJson

private structure Input where
  schema : Nat
  profile : String
  components : List CaseInput
  caches : List CacheInput
  removals : List RemovalInput
  deriving FromJson

private def ids : List String := ["net.minecraft", "fixture.loader", "fixture.other", "fixture.left", "fixture.right", "fixture.library"]

private def hint (text : String) : Except String (Option Hint) :=
  match text with
  | "" => pure none
  | "1.2" | "1.2+left" | "1.2+right" => pure (some ⟨text, 1⟩)
  | "1.10" => pure (some ⟨text, 2⟩)
  | "1.20.1" => pure (some ⟨text, 3⟩)
  | "1.22" => pure (some ⟨text, 4⟩)
  | _ => throw "Unadmitted suggestion rank; not a general FlexVer decoder."

private def req (r : ReqInput) : Except String Requirement := do
  if !ids.contains r.uid then throw "Unsupported fixture requirement UID."
  if !["", "1.20.1", "1.21.1", "1.02", "1.2", "3"].contains r.exact then throw "Unsupported fixture exact string."
  pure ⟨r.uid, if r.exact.isEmpty then none else some r.exact, ← hint r.hint, 0⟩

private def component (c : ComponentInput) : Except String Component := do
  if !ids.contains c.uid then throw "Unsupported fixture component UID."
  if !["", "1", "1.0", "1.20.1", "1.21.1"].contains c.version then throw "Unsupported fixture component version."
  let reqIds := c.requirements.map (·.uid)
  if reqIds.eraseDups.length != reqIds.length then throw "Duplicate requirement UID in fixture component."
  pure ⟨c.uid, c.version, c.dependencyOnly, c.volatile, c.custom, c.disabled, c.important,
    ← c.requirements.mapM req⟩

private def reqJson (r : Requirement) : Json := Json.mkObj
  [("uid", toJson r.uid), ("equals", toJson (r.exact.getD "")),
   ("suggests", toJson (r.hint.map (·.text) |>.getD "")), ("firstDependee", toJson r.first)]

private def reqsJson (rs : List Requirement) : Json := toJson (rs.map reqJson)

private def evaluate (row : CaseInput) : Except String Json := do
  let components ← row.components.mapM component
  let componentIds := components.map (·.uid)
  if componentIds.eraseDups.length != componentIds.length then throw "Duplicate fixture component UID."
  let p := plan components
  pure (Json.mkObj [("id", toJson row.id), ("gatherOK", toJson p.gathered.ok),
    ("requirements", reqsJson p.gathered.requirements), ("proposedRemovals", toJson p.removals),
    ("changePlanOK", toJson p.ok), ("proposedAdditions", reqsJson p.additions), ("proposedChanges", reqsJson p.changes),
    ("componentStates", toJson (components.map fun c => Json.mkObj [
      ("uid", toJson c.uid), ("enabled", toJson (enabled c)), ("canDisable", toJson (canDisable c)),
      ("custom", toJson c.custom), ("version", toJson c.version)]))])

private def cacheJson (c : Cache) : Json := Json.mkObj
  [("volatile", toJson c.volatile), ("requiredExact", toJson (c.requiredExact.getD "")),
   ("requires", toJson (if c.requiredExact.isSome then (1 : Nat) else 0)),
   ("conflicts", toJson (if c.hasConflict then (1 : Nat) else 0)), ("notifications", toJson c.notifications)]

private def evaluateCache (r : CacheInput) : Json :=
  let decoded := currentRoundtrip r.volatile
  let missing := missingMetadata decoded
  let loaded := loadedMetadata missing r.volatile "1"
  let repeated := loadedMetadata loaded r.volatile "1"
  let changed := loadedMetadata repeated r.volatile "3"
  Json.mkObj [("id", toJson r.id), ("decoded", cacheJson decoded), ("missingMetadata", cacheJson missing),
    ("loadedMetadata", cacheJson loaded), ("repeatedMetadata", cacheJson repeated), ("changedExactSameUid", cacheJson changed)]

private def evaluateRemoval (r : RemovalInput) : Json :=
  let initial : RemovalFiles := ⟨true, true, r.localJar⟩
  let first := removalAttempt initial r.important r.patchWritable r.jarWritable
  let final := repeatedRemoval 3 initial r.important r.patchWritable r.jarWritable
  let ok := first.2
  Json.mkObj [("id", toJson r.id), ("pendingAfterThree", toJson final.record),
    ("patchPresent", toJson final.patch), ("jarPresent", toJson final.jar),
    ("currentResult", toJson (if currentResult true ok == .retry then "retry" else "prefix-complete")),
    ("proposedResult", toJson (if proposedResult true ok == .failedRemoval then "failed-removal" else "prefix-complete")),
    ("proposedPending", toJson first.1.record), ("proposedPatchPresent", toJson first.1.patch),
    ("proposedJarPresent", toJson first.1.jar)]

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one component comparison input JSON path."; return 2
  let text ← IO.FS.readFile path
  match Json.parse text >>= fromJson? (α := Input) with
  | .error error => IO.eprintln error; return 2
  | .ok input =>
    if input.schema != 1 || input.profile != "cached-components-v1" then
      IO.eprintln "Unsupported component comparison schema/profile."
      return 2
    match input.components.mapM evaluate with
    | .error error => IO.eprintln error; return 2
    | .ok cases =>
      IO.println (Json.mkObj [("components", toJson cases), ("caches", toJson (input.caches.map evaluateCache)),
        ("removals", toJson (input.removals.map evaluateRemoval))]).compress
      return 0
