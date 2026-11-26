import Lean
import applications.«js-sbom».Sbom
open Lean ApplicationStudy.JsSbom
private structure RawRequest where
  operation : String
  format : String
  lockOnly : Bool
  runtimeOnly : Bool
  deriving FromJson
private structure RawRow where
  profile : String
  declaredName : String
  directoryName : String
  prodDigest : String
  devDigest : String
  optionalDigest : String
  requests : List RawRequest
  deriving FromJson
private structure Input where
  schema : Nat
  profile : String
  rows : List RawRow
  deriving FromJson
private def digest (s : String) : Bool :=
  s.length == 128 && s.toList.all (fun c => (c ≥ '0' && c ≤ '9') || (c ≥ 'a' && c ≤ 'f'))
private def name (s : String) : Bool :=
  !s.isEmpty && s.length ≤ 128 && s.toList.all (fun c => c.toNat < 128 && (c.isAlphanum || c == '-'))
private def evaluate (raw : RawRow) : Except String (List String) := do
  let profile ← match raw.profile with
    | "npm" => pure Profile.npm | "pnpm" => pure .pnpm | _ => throw "Unknown SBOM application."
  unless name raw.declaredName && name raw.directoryName do throw "Unadmitted package or placement name."
  unless [raw.prodDigest,raw.devDigest,raw.optionalDigest].all digest do throw "Canonical archive SHA512 required."
  unless raw.requests.length > 0 && raw.requests.length ≤ 24 do throw "Request bound."
  let requests ← raw.requests.mapM fun r => do
    let operation ← match r.operation with
      | "install" => pure Operation.install | "query" => pure .query | "report" => pure .report
      | "replace-code" => pure .replaceCode | "hold-entry" => pure .holdEntry
      | "restore-entry" => pure .restoreEntry | "hold-lock" => pure .holdLock
      | _ => throw "Unknown request."
    let format ← match r.format with
      | "cyclonedx" => pure Format.cyclonedx | "spdx" => pure .spdx | "missing" => pure .missing
      | _ => throw "Outside the selected SBOM formats."
    unless operation == .report || (!r.lockOnly && !r.runtimeOnly && format == .cyclonedx) do
      throw "Report options on a non-report operation."
    unless !r.lockOnly || (format == .cyclonedx && !r.runtimeOnly) do
      throw "Unqualified lock-only format/filter combination."
    pure (Request.mk operation format r.lockOnly r.runtimeOnly)
  unless requests.head?.map (·.operation) == some .install do throw "The qualified successful seed event is required first."
  unless (requests.filter (fun r => r.operation == .install)).length == 1 do throw "Only the initial successful installation is selected."
  let context : Context := ⟨profile,raw.declaredName,raw.directoryName,raw.prodDigest,raw.devDigest,raw.optionalDigest⟩
  let _ ← requests.foldlM (init := ({} : State)) fun s r => do
    match r.operation with
    | .replaceCode => unless s.installed && s.entry do throw "Code replacement needs its installed entry."
    | .holdEntry => unless s.installed && s.entry do throw "No entry to hold."
    | .restoreEntry => unless s.installed && !s.entry do throw "No held entry to restore."
    | .holdLock => unless s.lock do throw "No lock to hold."
    | .query => unless s.installed do throw "No qualified installed seed."
    | _ => pure ()
    pure (step context s r).after
  pure ((trace context {} requests).map text)
def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one SBOM research input."; return 2
  match Json.parse (← IO.FS.readFile path) >>= fromJson? (α := Input) with
  | .error e => IO.eprintln e; return 2
  | .ok input =>
    if input.schema != 1 || input.profile != "three-direct-local-archives" || input.rows.isEmpty || input.rows.length > 8 then
      IO.eprintln "Unsupported SBOM research schema,profile or count."; return 2
    match input.rows.mapM evaluate with
    | .error e => IO.eprintln e; return 2
    | .ok values => IO.println (toJson values).compress; return 0
