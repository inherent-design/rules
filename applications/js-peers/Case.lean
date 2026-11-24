import Lean
import applications.«js-peers».Contexts
open Lean ApplicationStudy.JsPeers

private structure Input where
  schema : Nat
  profile : String
  content : String
  direct : String
  hoisted : String
  declared : String
  locked : String
  lockBytes : String
  installed : String
  deriving FromJson

private structure Output where
  content : String
  peer : String
  refused : Bool
  declarationAfter : String
  lockAfter : String
  installedAfter : String
  deriving ToJson

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one peer-context projection JSON path."; return 2
  let text ← IO.FS.readFile path
  match Json.parse text >>= fromJson? (α := Input) with
  | .error e => IO.eprintln e; return 2
  | .ok i =>
    if i.schema != 1 then
      IO.eprintln "Unsupported peer-context projection schema."
      return 2
    let profile? : Option FixtureProfile := match i.profile with
      | "npm" => some .npmHoisted
      | "pnpm" => some .pnpmIsolated
      | "yarn" => some .yarnNodeModules
      | _ => none
    let some profile := profile? | do
      IO.eprintln "Unsupported fixture profile."
      return 2
    let selected := instantiate profile i.content i.direct i.hoisted
    let admission := frozenAdmission ⟨i.declared, i.locked, i.lockBytes, i.installed⟩
    let out : Output := ⟨selected.content, selected.peerProvider, admission.refused,
      admission.state.declaredBasis, admission.state.lockBytes, admission.state.installedBindingEvidence⟩
    IO.println (toJson out).compress
    return 0
