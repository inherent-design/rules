import Lean
import applications.empack.Archives
open Lean ApplicationStudy.EmpackArchives

private structure PathRow where
  id : String
  commonUnsafe : Bool
  drivePrefix : Bool
  portableOnlyUnsafe : Bool
  deriving FromJson
private structure RecordRow where
  headerReadable : Option Bool
  signature : Option Bool
  nameReadable : Option Bool
  utf8Declaration : Option Bool
  rawUnique : Option Bool
  spanWithin : Option Bool
  deriving FromJson
private structure MetadataRow where
  id : String
  endValid : Option Bool
  singleDisk : Option Bool
  zip64Shape : Option Bool
  entries : Option Nat
  entryLimit : Nat
  metadataBytes : Option Nat
  noDirectoryOverflow : Option Bool
  directoryWithin : Option Bool
  records : List RecordRow
  cancelAfter : Option Nat
  finalCount : Option Bool
  deriving FromJson
private structure ImportRow where
  id : String
  metadata : Bool
  paths : Bool
  tree : Bool
  regular : Bool
  payload : Bool
  deriving FromJson
private structure Input where
  schema : Nat
  paths : List PathRow
  metadata : List MetadataRow
  imports : List ImportRow
  deriving FromJson
private structure PathOutput where
  id : String
  opaqueAllowed : Bool
  portableAllowed : Bool
  deriving ToJson
private structure MetadataOutput where
  id : String
  code : Nat
  checks : Nat
  deriving ToJson
private structure ImportOutput where
  id : String
  published : Bool
  deriving ToJson
private structure Output where
  paths : List PathOutput
  metadata : List MetadataOutput
  imports : List ImportOutput
  deriving ToJson

private def metadataResult (r : MetadataRow) : Except String MetadataOutput := do
  if r.endValid == some true && r.singleDisk == some true && r.zip64Shape == some true &&
      r.entries.any (fun n => n ≤ r.entryLimit) && r.metadataBytes.any (fun n => n ≤ metadataLimit) &&
      r.noDirectoryOverflow == some true && r.directoryWithin == some true then
    if r.records.length != r.entries.getD 0 then
      throw s!"Archive record witness count differs from declaration: {r.id}"
  let records := r.records.map fun x => RecordFacts.mk x.headerReadable x.signature x.nameReadable
    x.utf8Declaration x.rawUnique x.spanWithin
  let m : MetadataFacts := ⟨r.endValid, r.singleDisk, r.zip64Shape, r.entries, r.entryLimit,
    r.metadataBytes, r.noDirectoryOverflow, r.directoryWithin, records, r.cancelAfter, r.finalCount⟩
  let some result := metadataDecision m | throw s!"Needed archive fact is unknown: {r.id}"
  return ⟨r.id, result.code, result.checks⟩

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one archive study input JSON path."; return 2
  let text ← IO.FS.readFile path
  match Json.parse text >>= fromJson? (α := Input) with
  | .error error => IO.eprintln error; return 2
  | .ok input =>
    if input.schema != 1 then
      IO.eprintln "Unsupported archive study schema."
      return 2
    match input.metadata.mapM metadataResult with
    | .error error => IO.eprintln error; return 2
    | .ok metadata =>
      let output : Output := ⟨
        input.paths.map (fun r =>
          let p : PathFacts := ⟨r.commonUnsafe, r.drivePrefix, r.portableOnlyUnsafe⟩
          ⟨r.id, opaqueName p, portableName p⟩), metadata,
        input.imports.map (fun r => ⟨r.id, mayPublishAuthor r.metadata r.paths r.tree r.regular r.payload⟩)⟩
      IO.println (toJson output).compress
      return 0
