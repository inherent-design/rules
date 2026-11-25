import Lean
import host.minecraft.ProviderAdaptation
open Lean Host.Minecraft.ProviderAdaptation
private structure RawElement where
  kind : Option Nat
  scale : Option Nat
  cull : Option Bool
  origin : Option Nat
  numeric : Option Bool
  deriving FromJson
private structure Row where
  ready : Option Bool
  elements : Option (List RawElement)
  deriving FromJson
private structure Request where
  schema : Nat
  contract : String
  rows : List Row
  deriving FromJson
private def need {α : Type} (x : Option α) : Except String α :=
  match x with
  | some v => .ok v
  | none => .error "Required adaptation evidence is unknown."
private def shape (r : RawElement) : Except String Element := do
  let kind ← need r.kind
  if kind > 2 then throw "Outside selected element kinds."
  pure {kind := kind}
private def body (r : RawElement) (e : Element) : Except String Element := do
  if e.kind != 2 then return e
  let scale ← need r.scale
  if scale > 3 then throw "Outside selected rescale forms."
  if scale == 2 || scale == 3 then return {e with scale := scale}
  let cull ← need r.cull
  if cull then return {e with scale := scale,cull := true}
  let origin ← need r.origin
  if origin > 2 then throw "Outside selected origin forms."
  if origin != 2 then return {e with scale := scale,origin := origin}
  pure {e with scale := scale,origin := origin,numeric := (← need r.numeric)}
private def admitPrefix : List RawElement → List Element → Except String (List Element)
  | [],[] => pure []
  | r::rs,e::es => do
    let value ← body r e
    if check value != 0 then return value::es
    pure (value::(← admitPrefix rs es))
  | _,_ => .error "Mismatched adaptation projection."
private def admit (r : Row) : Except String (List Nat) := do
  let ready ← need r.ready
  if !ready then return evaluate false []
  let raw ← need r.elements
  if raw.length > 132 then throw "Outside selected research element batch."
  let shapes ← raw.mapM shape
  if !(shapes.any (fun e => e.kind == 2)) || shapes.length > 128 then return evaluate true shapes
  pure (evaluate true (← admitPrefix raw shapes))
def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one adaptation request.";return 2
  match Json.parse (← IO.FS.readFile path) >>= fromJson? (α := Request) with
  | .error e => IO.eprintln e;return 2
  | .ok r =>
    if r.schema != 1 || r.contract != "bounded-compat-euler-adaptation-v1" || r.rows.length > 64 then
      IO.eprintln "Unselected adaptation schema,contract or batch.";return 2
    match r.rows.mapM admit with
    | .error e => IO.eprintln e;return 2
    | .ok values => IO.println (toJson values).compress;return 0
