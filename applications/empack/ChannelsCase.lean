import Lean
import applications.empack.Channels
open Lean ApplicationStudy.EmpackChannels

private structure SigRow where
  key : Nat
  algorithmKnown : Bool
  canonical : Bool
  valid : Bool
  deriving FromJson

private structure BindingRow where
  pack : Nat
  origin : Nat
  channel : Nat
  deriving FromJson

private def BindingRow.value (r : BindingRow) : Binding := ⟨r.pack, r.origin, r.channel⟩

private structure FloorRow where
  binding : BindingRow
  sequence : Nat
  payload : Nat
  deriving FromJson

private structure Row where
  operation : String
  keys : List Nat
  enrollmentShape : Bool
  envelopeShape : Bool
  documentShape : Bool
  signatures : List SigRow
  expected : BindingRow
  document : BindingRow
  authoredBounds : Bool
  prereleaseAdmitted : Bool
  sequence : Nat
  payload : Nat
  floor : Option FloorRow
  deriving FromJson

private structure SavedRow where
  recordShape : Bool
  observed : Option Row
  stored : Option FloorRow
  selected : FloorRow
  deriving FromJson

private structure Input where
  schema : Nat
  cases : List Row
  saved : List SavedRow
  deriving FromJson

private def cause : TypedCause → String
  | .absent => "absent"
  | .publisherAuthentication => "publisher-authentication-failed"
  | .incompatibleEngine => "incompatible-engine"

private def validateBinding (b : BindingRow) (unavailable : Bool) : Except String Unit := do
  if b.pack == 0 || b.pack > 2 || b.channel == 0 || b.channel > 2 || b.origin > 3 then
    throw "Unsupported fixture binding."
  if b.origin == 0 && !unavailable then throw "An admitted origin needs a fixture identity."

private def floorValue (f : FloorRow) : Except String Floor := do
  validateBinding f.binding false
  if f.sequence == 0 || f.sequence > 18446744073709551615 || f.payload == 0 then
    throw "Unsupported retained floor witness."
  pure ⟨f.binding.value, f.sequence, f.payload⟩

private def request (r : Row) : Except String Request := do
  if r.keys.any (fun k => k == 0 || k > 2) then throw "Unknown fixture publisher key."
  if r.operation != "channel" then throw "Expected a channel request."
  validateBinding r.expected (!r.enrollmentShape)
  validateBinding r.document false
  if r.sequence == 0 || r.sequence > 18446744073709551615 || r.payload == 0 then
    throw "Unsupported fixture sequence/payload witness."
  if r.signatures.any (fun s => s.key == 0 || s.key > 2) then throw "Unknown signature key witness."
  let floor ← r.floor.mapM floorValue
  pure ⟨r.keys, r.enrollmentShape, r.envelopeShape, r.documentShape,
    r.signatures.map (fun s => ⟨s.key, s.algorithmKnown, s.canonical, s.valid⟩),
    r.expected.value, r.document.value, ⟨r.authoredBounds, r.prereleaseAdmitted⟩,
    r.sequence, r.payload, floor⟩

private def bit (b : Bool) : String := if b then "1" else "0"

private def evaluate (r : Row) : Except String String := do
  if r.keys.any (fun k => k == 0 || k > 2) then throw "Unknown fixture publisher key."
  if r.operation == "decode" then return bit r.documentShape ++ "/absent/decode/0/0/0/0/0"
  if r.operation == "sign" then return bit (signingAdmits r.documentShape r.keys) ++ "/absent/sign/0/0/0/0/0"
  let req ← request r
  let returned := if admitted req then
      let f := candidate req
      [toString f.binding.pack, toString f.binding.origin, toString f.binding.channel,
        toString f.sequence, toString f.payload]
    else ["0", "0", "0", "0", "0"]
  pure (String.intercalate "/" ([bit (admitted req), cause (typedCause req),
    if enrollmentAdmits r.keys r.enrollmentShape then "channel" else "enrollment"] ++ returned))

private def evaluateSaved (s : SavedRow) : Except String String := do
  if !s.recordShape then return "0/not-run/not-run/not-run/not-run/0"
  if s.stored.isSome != s.observed.isSome then throw "An admitted record needs paired observation/floor presence."
  let stored ← s.stored.mapM floorValue
  let selected ← floorValue s.selected
  let observed ← s.observed.mapM fun r => do
    let req ← request r
    if req.floor != stored then throw "Cached revalidation must use the record's actual saved floor."
    pure req
  let guard := stored == some selected
  let authenticated := observed.any (cachedCurrent true true)
  let exact := observed.any (cachedExact true true)
  pure (String.intercalate "/" ["1", bit guard, bit authenticated, bit exact,
    bit (guard && authenticated), bit (guard && exact)])

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one channel-model JSON path."; return 2
  let text ← IO.FS.readFile path
  match Json.parse text >>= fromJson? (α := Input) with
  | .error error => IO.eprintln error; return 2
  | .ok input =>
    if input.schema != 1 then IO.eprintln "Unsupported channel-model schema."; return 2
    match input.cases.mapM evaluate, input.saved.mapM evaluateSaved with
    | .error error, _ | _, .error error => IO.eprintln error; return 2
    | .ok values, .ok saved =>
      IO.println (Json.mkObj [("cases", toJson values), ("saved", toJson saved)]).compress
      return 0
