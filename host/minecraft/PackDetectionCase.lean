import Lean
import host.minecraft.PackDetection

open Lean Host.Minecraft.PackDetection

private structure RawNode where
  kind : Nat
  identity : Option Nat
  zipSuffix : Option Bool
  metadataRegular : Option Bool
  nestedLinks : Option Nat
  deriving FromJson

private structure Row where
  id : Nat
  release : String
  entry : RawNode
  rawTarget : Option RawNode
  parentTarget : Option RawNode
  targetAbsolute : Option Bool
  allowLinks : Bool
  factoryMode : Nat
  deriving FromJson

private structure Request where
  schema : Nat
  contract : String
  callbackProfile : String
  policy : Nat
  rows : List Row
  deriving FromJson

private structure Result where
  id : Nat
  error : Nat
  value : Nat
  factory : Nat
  binding : Nat
  issues : Nat
  matcherCalls : Nat
  deriving ToJson

private def known (name : String) (value : Option α) : Except String α :=
  match value with
  | some value => .ok value
  | none => .error ("Needed fixture evidence is unknown: " ++ name)

private def binding (raw : RawNode) : Except String Nat := do
  let value ← known "factory path binding" raw.identity
  if value == 0 || value > 3 then throw "Outside case-local nonzero binding domain."
  return value

private def node (allow : Bool) (raw : RawNode) : Except String Node := do
  match raw.kind with
  | 0 => return { kind := .missing }
  | 1 =>
    let suffix ← known "regular-file suffix" raw.zipSuffix
    let identity ← if suffix then binding raw else pure 0
    return { kind := .regular, zipSuffix := suffix, identity := identity }
  | 2 =>
    let links ← known "directory link count" raw.nestedLinks
    if links > 1 then throw "Outside selected zero/one-link directory profile."
    if !allow && links > 0 then return { kind := .directory, nestedLinks := links }
    let metadata ← known "regular metadata entry" raw.metadataRegular
    let identity ← if metadata then binding raw else pure 0
    return { kind := .directory, nestedLinks := links, metadataRegular := metadata, identity := identity }
  | 3 => return { kind := .link }
  | 4 => return { kind := .other }
  | _ => throw "Unselected file kind."

private def row (policy : Nat) (raw : Row) : Except String Result := do
  if raw.id > 127 || !["1.21.1", "1.21.4", "1.21.5", "1.21.11", "26.3"].contains raw.release || raw.factoryMode > 2 then
    throw "Unselected row, source release or factory profile."
  let mode := match raw.factoryMode with | 0 => FactoryMode.returned | 1 => .nullValue | _ => .failed
  let entry ← node raw.allowLinks raw.entry
  let mut rawTarget : Node := { kind := .missing }
  let mut parentTarget : Node := { kind := .missing }
  let mut absolute := true
  if entry.kind = .link && raw.allowLinks then
    if policy == 1 then absolute ← known "link target absolute/relative" raw.targetAbsolute
    if absolute then rawTarget ← node true (← known "raw-target attributes" raw.rawTarget)
    else parentTarget ← node true (← known "parent-target attributes" raw.parentTarget)
  let input : Input := ⟨entry, rawTarget, parentTarget, absolute, raw.allowLinks, mode⟩
  -- Only needed target slots are parsed. Placeholder missing nodes in dead slots
  -- are not observations that those paths are absent.
  let output := if policy == 0 then run input else parentAnchored input
  return ⟨raw.id, output.error, output.value, output.factory, output.binding, output.issues, output.matcherCalls⟩

private def decode (input : Json) : Except String Json := do
  let request ← fromJson? (α := Request) input
  if request.schema != 1 || request.contract != "original-pack-detector-v1" ||
      request.callbackProfile != "authored-matcher-factories-v1" || request.policy > 1 || request.rows.length > 128 then
    throw "Unsupported research schema, callback or policy."
  if (request.rows.map (·.id)).eraseDups.length != request.rows.length then throw "Repeated case identity."
  return toJson (← request.rows.mapM (row request.policy))

def main (args : List String) : IO UInt32 := do
  let out ← IO.getStdout
  let err ← IO.getStderr
  let (batch, path) ← match args with
    | [path] => pure (false, path)
    | ["--batch", path] => pure (true, path)
    | _ => err.putStrLn "Expected request path or --batch packet-array path."; return 2
  try
    match Json.parse (← IO.FS.readFile path) with
    | .error message => err.putStrLn message; return 2
    | .ok input =>
      if batch then
        match fromJson? (α := List Json) input with
        | .error message => err.putStrLn message; return 2
        | .ok packets =>
          if packets.length > 64 then err.putStrLn "Too many research packets."; return 2
          out.putStrLn (toJson (packets.map (fun packet => match decode packet with | .ok _ => (0 : Nat) | .error _ => 2))).compress
          return 0
      else
        match decode input with
        | .ok value => out.putStrLn value.compress; return 0
        | .error message => err.putStrLn message; return 2
  catch error => err.putStrLn error.toString; return 2
