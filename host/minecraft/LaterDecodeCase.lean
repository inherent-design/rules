import Lean
import host.minecraft.LaterDecode
open Lean MinecraftHost.LaterDecode MinecraftHost.ArtifactVersions

private structure NumberRow where
  negative : Bool
  whole : Nat
  fraction : Nat
  deriving FromJson
private structure FormatRow where
  top : Bool
  tokens : List NumberRow
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
private structure ShadeRow where
  present : Bool
  direction : Nat
  deriving FromJson
private structure VersionRow where
  major : Nat
  minor : Nat
  deriving FromJson
private structure PackRow where
  threshold : Nat
  lower : Option VersionRow
  upper : Option VersionRow
  main : Option Nat
  old : Option (Nat × Nat)
  deriving FromJson
private structure Row where
  kind : String
  data : Json
  deriving FromJson
private structure Input where
  schema : Nat
  cases : List Row
  deriving FromJson

private def version (v : Version) : String := s!"{v.major}.{v.minor}"
private def evaluate (row : Row) : Except String String := do
  match row.kind with
  | "format" =>
    let r ← fromJson? (α := FormatRow) row.data
    if r.tokens.any (fun n => n.whole > 1000 || n.fraction > 9 || (n.negative && n.fraction != 0)) then throw "Unsupported decimal-number profile."
    let result := decodeFormat r.top (r.tokens.map (fun n => ⟨n.negative,n.whole,n.fraction⟩))
    pure ((result.map (fun v => "ok:" ++ version v)).getD "refused")
  | "rotation" =>
    let r ← fromJson? (α := RotationRow) row.data
    if r.axis > 3 || r.angle > 360 || r.x > 360 || r.y > 360 || r.z > 360 then throw "Unsupported bounded angle/axis profile."
    let result := decodeRotation ⟨r.present,r.originValid,r.axisPresent,r.anglePresent,r.xyzPresent,r.axis,r.angle,r.x,r.y,r.z,r.rescale⟩
    pure ((result.map (fun v => s!"ok:{v.mode}/{v.axis}/{v.angle}/{v.x}/{v.y}/{v.z}/{if v.rescale then 1 else 0}")).getD "refused")
  | "shade" =>
    let r ← fromJson? (α := ShadeRow) row.data
    if r.direction > 6 then throw "Unknown direction token."
    pure (((decodeShade r.present r.direction).map (fun v => s!"ok:shade/{v}")).getD "refused")
  | "pack" =>
    let r ← fromJson? (α := PackRow) row.data
    if r.threshold != 64 && r.threshold != 81 then throw "Unselected pack-type threshold."
    if [r.lower,r.upper].any (fun v => v.any (fun x => x.major > 1000 || x.minor > 2147483647)) then throw "Unsupported format bound."
    if r.main.any (· > 1000) || r.old.any (fun x => x.1 > 1000 || x.2 > 1000) then throw "Unsupported legacy profile."
    let cv := fun (v : VersionRow) => Version.mk v.major v.minor
    let result := decodePack ⟨r.threshold,r.lower.map cv,r.upper.map cv,r.main,r.old⟩
    pure ((result.map (fun v => "ok:" ++ version v.lower ++ "-" ++ version v.upper)).getD "refused")
  | _ => throw "Unsupported action."

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one later-codec model input path."; return 2
  let text ← IO.FS.readFile path
  match Json.parse text >>= fromJson? (α := Input) with
  | .error error => IO.eprintln error; return 2
  | .ok input =>
    if input.schema != 1 then IO.eprintln "Unsupported schema."; return 2
    match input.cases.mapM evaluate with
    | .error error => IO.eprintln error; return 2
    | .ok values => IO.println (toJson values).compress; return 0
