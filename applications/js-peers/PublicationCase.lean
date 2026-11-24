import Lean
import applications.«js-peers».Publication
open Lean ApplicationStudy.JsPublication

private structure Row where
  profile : String
  dry : Bool
  recordPresent : Bool
  rejected : Bool
  loss : String
  hooks : Bool
  hookFailure : String
  deriving FromJson

private structure Input where
  schema : Nat
  cases : List Row
  deriving FromJson

private def evaluate (r : Row) : Except String String := do
  let p ← match r.profile with
    | "npm" => pure Profile.npm | "pnpm" => pure Profile.pnpm | "yarn" => pure Profile.yarn
    | _ => throw "Unsupported publication profile."
  let loss ← match r.loss with
    | "none" => pure Loss.none | "before" => pure Loss.beforeAcceptance | "after" => pure Loss.afterAcceptance
    | _ => throw "Unsupported fixture loss boundary."
  let hook ← match r.hookFailure with
    | "none" => pure HookFailure.none | "before" => pure HookFailure.beforeUpload | "after" => pure HookFailure.afterUpload
    | _ => throw "Unsupported fixture hook boundary."
  if !r.hooks && hook != .none then throw "A hook failure needs declared fixture hooks."
  if r.dry && (r.rejected || loss != .none || r.recordPresent) then throw "Unsupported dry-run combination."
  if hook != .none && (r.dry || r.recordPresent || r.rejected || loss != .none) then throw "Unsupported hook/loss combination."
  if r.rejected && (r.recordPresent || loss != .none) then throw "Unsupported fixture rejection combination."
  if r.recordPresent && loss != .none then throw "Loss controls start without a version."
  let request : Request := ⟨r.dry, r.recordPresent, r.rejected, loss, r.hooks, hook⟩
  let o := publish p request
  pure (String.intercalate "/" [if o.sent then "1" else "0", if o.acceptedHere then "1" else "0",
    if o.remotePresent then "1" else "0", if o.acknowledged then "1" else "0",
    if o.localHookEffects then "1" else "0", toString o.exitCode])

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one publication JSON path."; return 2
  let text ← IO.FS.readFile path
  match Json.parse text >>= fromJson? (α := Input) with
  | .error error => IO.eprintln error; return 2
  | .ok input =>
    if input.schema != 1 then IO.eprintln "Unsupported publication schema."; return 2
    match input.cases.mapM evaluate with
    | .error error => IO.eprintln error; return 2
    | .ok values => IO.println (toJson values).compress; return 0
