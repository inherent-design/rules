import Lean
import applications.«js-patches».Patches
open Lean ApplicationStudy.JSPatches
private structure ImageRow where
  recipe : Nat
  lock : Nat
  live : Nat
  payload : Nat
  patchFile : Bool
  deriving FromJson
private structure CaseRow where
  profile : String
  image : ImageRow
  action : String
  importExisting : Bool
  frozen : Bool
  force : Bool
  keyMatches : Bool
  draft : Nat
  deriving FromJson
private structure Request where
  schema : Nat
  cases : List CaseRow
  deriving FromJson
private def checked (r : CaseRow) : Except String (Profile × Image × Action) := do
  let p ← match r.profile with
    | "pnpm" => pure Profile.pnpm | "yarn" => pure Profile.yarn
    | _ => throw "Unknown patch research profile."
  let s := r.image
  if s.recipe > 2 || s.lock > 3 || s.live > 3 || s.payload > 2 ||
      (s.recipe != 0 && !s.patchFile) || ((s.live == 0) != (s.payload == 0)) ||
      (p == .yarn && s.live > 1) then throw "Unsupported recipe/lock/live/payload witness."
  if (r.action != "prepare" && r.importExisting) ||
      (r.action != "install" && (r.frozen || r.force)) ||
      (r.action != "remove" && r.keyMatches) ||
      (r.action != "commit" && r.draft != 0) then throw "Unrelated action fields."
  let a ← match r.action with
    | "observe" => pure Action.observe
    | "prepare" =>
      if s.recipe == 2 || s.payload == 0 then throw "Preparation outside the captured profile."
      pure (.prepare r.importExisting)
    | "commit" =>
      if r.draft != 2 then throw "Only the captured modified text draft is modeled."
      pure .commit
    | "install" =>
      if r.frozen && r.force then throw "Combined frozen/force profile is not qualified."
      pure (.install r.frozen r.force)
    | "remove" =>
      if p != .pnpm then throw "No Yarn remove command is modeled."
      pure (.remove r.keyMatches)
    | "unplug" =>
      if p != .yarn then throw "No pnpm unplug command is modeled."
      pure .unplug
    | _ => throw "Unknown action."
  pure (p,⟨s.recipe,s.lock,s.live,s.payload,s.patchFile⟩,a)
private def output (r : Outcome) : Json := Json.mkObj [
  ("status",toJson r.status),("prepared",toJson r.prepared),("image",Json.mkObj [
    ("recipe",toJson r.image.recipe),("lock",toJson r.image.lock),("live",toJson r.image.live),
    ("payload",toJson r.image.payload),("patchFile",toJson r.image.patchFile)])]
def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one patch research input."; return 2
  match Json.parse (← IO.FS.readFile path) >>= fromJson? (α := Request) with
  | .error error => IO.eprintln error; return 2
  | .ok request =>
    if request.schema != 1 then IO.eprintln "Unsupported patch research schema."; return 2
    match request.cases.mapM checked with
    | .error error => IO.eprintln error; return 2
    | .ok inputs =>
      IO.println (Json.mkObj [("current",toJson (inputs.map fun (p,s,a) => output (run p s a))),
        ("proposed",toJson (inputs.map fun (p,s,a) => output (run p s a true)))]).compress
      return 0
