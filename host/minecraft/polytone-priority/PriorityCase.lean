import Lean
import host.minecraft.«polytone-priority».Priority
open Lean MinecraftHost.Polytone.Priority

private structure InputEntry where
  key : Nat
  enabled : Bool
  rank : Nat
  marker : Nat
  deriving FromJson
private structure Row where
  entries : List InputEntry
  deriving FromJson
private structure Input where
  schema : Nat
  cases : List Row
  deriving FromJson

private def item (e : Entry) : String :=
  s!"{e.key}:{if e.enabled then 1 else 0}:{e.rank}:{e.marker}"
private def render (entries : List Entry) : String := String.intercalate "," (entries.map item)
private def evaluate (row : Row) : Except String String := do
  if row.entries.any (fun e => e.rank > 4294967295) then throw "Priority outside Java int32 projection."
  let result := run (row.entries.map (fun e => Entry.mk e.key e.enabled e.rank e.marker))
  let zero := ((result.entries.find? (fun e => e.key == 0)).map (fun e => toString e.marker)).getD "none"
  pure s!"{result.entries.length}/{result.warnings}/{zero}/{render result.entries}/{render (ordered result.entries)}"

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one priority fixture input path."; return 2
  let text ← IO.FS.readFile path
  match Json.parse text >>= fromJson? (α := Input) with
  | .error error => IO.eprintln error; return 2
  | .ok input =>
    if input.schema != 1 then IO.eprintln "Unsupported schema."; return 2
    match input.cases.mapM evaluate with
    | .error error => IO.eprintln error; return 2
    | .ok values => IO.println (toJson values).compress; return 0
