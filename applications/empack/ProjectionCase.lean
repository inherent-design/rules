import Lean
import applications.empack.Projection
open Lean ApplicationStudy.EmpackProjection

private structure InputRow where
  owner : Nat
  layer : Nat
  destination : Nat
  client : Nat
  server : Nat
  representation : Nat
  asset : Nat
  deriving FromJson
private structure Row where
  target : Nat
  policy : Nat
  inputs : List InputRow
  deriving FromJson
private structure Input where
  schema : Nat
  cases : List Row
  deriving FromJson
private structure Output where
  status : String
  entries : List String
  precedence : List String
  choices : List String
  deriving ToJson

private def decodeRequirement : Nat → Except String Requirement
  | 0 => .ok .unsupported | 1 => .ok .required
  | 2 => .ok (.optional false) | 3 => .ok (.optional true)
  | _ => .error "Unknown requirement code."
private def decodeEntry (row : InputRow) : Except String Entry := do
  if row.owner > 255 || row.asset > 255 || row.destination > 1 then
    throw "Identity/destination outside the captured profile."
  let layer ← match row.layer with
    | 0 => pure Layer.common | 1 => pure Layer.sharedOverride
    | 2 => pure Layer.client | 3 => pure Layer.server
    | _ => throw "Unknown layer code."
  let client ← decodeRequirement row.client
  let server ← decodeRequirement row.server
  let representation ← match row.representation with
    | 0 => pure (Representation.embedded row.asset)
    | 1 => pure Representation.unacquired
    | 2 => pure (Representation.download (some row.asset) true)
    | 3 => pure (Representation.download none true)
    | 4 => pure (Representation.download (some row.asset) false)
    | _ => throw "Unknown representation code."
  pure ⟨row.owner, layer, row.destination, client, server, representation⟩
private def decodeView : Nat → Except String View
  | 0 => .ok (.flat .client true) | 1 => .ok (.flat .server true)
  | 2 | 7 => .ok (.flat .client false)
  | 3 | 4 => .ok (.layers .both false)
  | 5 => .ok (.layers .both true)
  | 6 => .ok (.layers .client false)
  | _ => .error "Unknown recipe profile."
private def decodePolicy : Nat → Except String Policy
  | 0 => .ok .preserve | 1 => .ok .unresolved | 2 => .ok .enable
  | 3 => .ok .disable | 4 => .ok .defaults | 5 => .ok .unknown
  | _ => .error "Unknown choice policy."
private def errorLabel : Error → String
  | .duplicate => "duplicate" | .invalidEnvironment => "invalid-environment"
  | .conflictingChoice => "conflicting-choice" | .unknownChoice => "unknown-choice"
  | .preserveRequired => "preserve-required" | .overlayNeedsChoice => "overlay-needs-choice"
  | .choiceRequired => "choice-required" | .invalidReference => "invalid-reference"
  | .materialization => "materialization"
private def requirementCode : Requirement → Nat
  | .unsupported => 0 | .required => 1 | .optional false => 2 | .optional true => 3
private def path (destination : Nat) := s!"config/p{destination}.cfg"
private def entryLabel (entry : Entry) : String :=
  let (representation, asset) := match entry.representation with
    | .embedded asset => (0, asset)
    | .unacquired => (1, 0)
    | .download none _ => (3, 0)
    | .download (some asset) _ => (2, asset)
  s!"s{entry.owner}:{layerRank entry.layer}:{path entry.destination}:{requirementCode entry.client}:{requirementCode entry.server}:{representation}:{asset}"
private def bit (b : Bool) : String := if b then "true" else "false"
private def present (status : String) (plan : Plan) (completed : Bool) : Output :=
  ⟨status, (plan.entries.map entryLabel).mergeSort,
    if completed then (plan.precedence.map fun p => s!"s{p.replacement}>s{p.replaced}@{path p.destination}").mergeSort else [],
    if completed then (match plan.choice with | none => [] | some c => [s!"extra:{bit c.enabled}:{bit c.usedDefault}"]) else []⟩
private def evaluate (row : Row) : Except String Output := do
  let inputs ← row.inputs.mapM decodeEntry
  let view ← decodeView row.target
  let policy ← decodePolicy row.policy
  match select inputs view policy with
  | .error error => pure ⟨"select/" ++ errorLabel error, [], [], []⟩
  | .ok selected => match finish view selected with
    | .error error => pure (present ("finish/" ++ errorLabel error) selected false)
    | .ok done => pure (present "ok" done true)

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one projection input path."; return 2
  let text ← IO.FS.readFile path
  match Json.parse text >>= fromJson? (α := Input) with
  | .error error => IO.eprintln error; return 2
  | .ok input =>
    if input.schema != 1 then
      IO.eprintln "Unsupported projection schema."
      return 2
    match input.cases.mapM evaluate with
    | .error error => IO.eprintln error; return 2
    | .ok result => IO.println (toJson result).compress; return 0
