import Lean
import host.minecraft.Elements
open Lean MinecraftHost.Elements MinecraftHost.LaterDecode

private structure FaceRow where
  known : Bool
  isNull : Bool
  texture : Bool
  uv : Bool
  quadrant : Bool
  cull : Bool
  deriving FromJson
private structure RotationRow where
  present : Bool
  originValid : Bool
  axisPresent : Bool
  anglePresent : Bool
  xyzPresent : Bool
  axis : Nat
  angle : Nat
  x : Nat
  y : Nat
  z : Nat
  rescale : Bool
  deriving FromJson
private structure ElementRow where
  vectors : Bool
  shadeValid : Bool
  shade : Bool
  lightNumeric : Bool
  lightNegative : Bool
  lightWhole : Nat
  lightFraction : Nat
  facesPresent : Bool
  faces : List FaceRow
  rotation : RotationRow
  deriving FromJson
private structure ConsumerRow where
  axis : Nat
  dx : Bool
  dy : Bool
  dz : Bool
  isNull : Bool
  deriving FromJson
private structure Row where
  kind : String
  data : Json
  deriving FromJson
private structure Request where
  schema : Nat
  profile : String
  cases : List Row
  deriving FromJson

private def bit (b : Bool) : Nat := if b then 1 else 0
private def render (v : Output) : String :=
  s!"ok:{bit v.shade}/{v.light}/{v.faces}/{v.nulls}/{v.culls}|{v.rotation.mode}/{v.rotation.axis}/{v.rotation.angle}/{v.rotation.x}/{v.rotation.y}/{v.rotation.z}/{bit v.rotation.rescale}"
private def evaluate (row : Row) : Except String String := do
  match row.kind with
  | "element" =>
    let r ← fromJson? (α := ElementRow) row.data
    if r.lightWhole > 1000 || r.lightFraction > 9 || r.faces.length > 6 then throw "Unsupported light/face profile."
    let t := r.rotation
    if t.axis > 3 || t.angle > 360 || t.x > 360 || t.y > 360 || t.z > 360 then throw "Unsupported rotation profile."
    let input : Input := ⟨r.vectors,r.shadeValid,r.shade,r.lightNumeric,r.lightNegative,r.lightWhole,r.lightFraction,r.facesPresent,
      r.faces.map (fun f => ⟨f.known,f.isNull,f.texture,f.uv,f.quadrant,f.cull⟩),
      ⟨t.present,t.originValid,t.axisPresent,t.anglePresent,t.xyzPresent,t.axis,t.angle,t.x,t.y,t.z,t.rescale⟩⟩
    pure (((decode input).map render).getD "refused")
  | "consumer" =>
    let r ← fromJson? (α := ConsumerRow) row.data
    if r.axis > 2 then throw "Unselected face axis."
    pure (match consume r.axis r.dx r.dy r.dz r.isNull with
      | 0 => "0:"
      | 1 => "1:sprites"
      | _ => "2:sprites,resolveSlot")
  | _ => throw "Unsupported action."

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one element model request."; return 2
  let text ← IO.FS.readFile path
  match Json.parse text >>= fromJson? (α := Request) with
  | .error e => IO.eprintln e; return 2
  | .ok request =>
    if request.schema != 1 || request.profile != "java-1.21.11-vanilla" then IO.eprintln "Unselected schema/profile."; return 2
    match request.cases.mapM evaluate with
    | .error e => IO.eprintln e; return 2
    | .ok values => IO.println (toJson values).compress; return 0
