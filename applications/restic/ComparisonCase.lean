import Lean
import applications.restic.Comparison
open Lean ApplicationStudy.ResticComparison

private structure RawHandle where
  kind : String
  id : Nat
  deriving FromJson
private structure RawBlob where
  handle : RawHandle
  plain : Nat
  cipher : Nat
  uncompressedCipher : Nat
  compressed : Bool
  deriving FromJson
private structure RawNode where
  path : List String
  location : List String
  kind : String
  contentPresent : Bool
  content : List Nat
  metadataBasis : Nat
  subtree : Option Nat
  size : Nat
  deriving FromJson
private structure RawSnapshot where
  id : Nat
  root : Nat
  nodes : List RawNode
  deriving FromJson
private structure Row where
  kind : String
  mode : String
  selected : List Nat
  metadata : Bool
  fullClosure : Bool
  fixSearch : Bool
  availability : String
  query : String
  deriving FromJson
private structure Input where
  schema : Nat
  profile : String
  catalog : List RawBlob
  snapshots : List RawSnapshot
  rows : List Row
  deriving FromJson

private def boundedId (n : Nat) : Bool := n > 0 && n ≤ 4096
private def pathOk (p : SavedPath) : Bool :=
  !p.isEmpty && p.length ≤ 8 && p.all (fun s => !s.isEmpty && s.length ≤ 128 &&
    s != "." && s != ".." && !s.contains '/' && !s.contains '\\' && !s.contains '\x00')
private def handle (r : RawHandle) : Except String Handle := do
  unless boundedId r.id do throw "Opaque ID bound."
  let kind ← if r.kind == "data" then pure BlobKind.data else if r.kind == "tree" then pure .tree else throw "Unknown blob kind."
  pure ⟨kind,r.id⟩
private def blob (r : RawBlob) : Except String Blob := do
  let key ← handle r.handle
  if r.plain > 10000000 || r.cipher < 32 || r.cipher > 10000032 ||
      r.uncompressedCipher != r.plain+32 || (!r.compressed && r.cipher != r.uncompressedCipher) then
    throw "Unsupported index weight witness."
  pure ⟨key,r.plain,r.cipher,r.uncompressedCipher,r.compressed⟩
private def node (r : RawNode) : Except String Node := do
  unless pathOk r.path && r.location == r.path ++ r.path.getLast?.toList do
    throw "Saved path or source location-key witness."
  if !boundedId r.metadataBasis || r.content.length > 32 || !r.content.all boundedId ||
      r.size > 10000000 || (!r.contentPresent && !r.content.isEmpty) then
    throw "Node comparison bound."
  let kind ← if r.kind == "file" then pure NodeKind.file else if r.kind == "dir" then pure .directory else throw "Unadmitted node kind."
  if (kind == .file && r.subtree.isSome) ||
      (kind == .directory && (r.subtree.isNone || r.contentPresent || !r.content.isEmpty || r.size != 0)) ||
      !r.subtree.toList.all boundedId then throw "Node reference shape."
  pure ⟨r.path,r.location,kind,r.contentPresent,r.content,r.metadataBasis,r.subtree,r.size⟩
private def snapshot (r : RawSnapshot) : Except String Snapshot := do
  if !boundedId r.id || !boundedId r.root || r.nodes.length > 64 then throw "Snapshot comparison bound."
  let nodes ← r.nodes.mapM node
  let paths := nodes.map (·.path)
  unless paths.eraseDups.length == paths.length && paths == paths.foldr insertPath [] do
    throw "Duplicate or unordered saved paths."
  for n in nodes do
    if n.path.length > 1 then
      unless nodes.any (fun parent => parent.path == n.path.dropLast && parent.kind == .directory) do
        throw "Missing saved parent directory."
  pure ⟨r.id,r.root,nodes⟩
private def statsJson (s : Stats) : Json := toJson [s.size,s.countedEntries,s.blobCount,s.snapshots,
  s.uncompressed,s.compressedSize,s.compressedUncompressed]
private def deltaJson (d : Delta) : Json := toJson [d.files,d.directories,d.dataBlobs,d.treeBlobs,d.bytes]
private def diffJson (d : Diff) : Json := Json.mkObj [
  ("events",toJson (d.events.map (fun e => "/" ++ String.intercalate "/" e.path ++
    (if e.directory then "/" else "") ++ "|" ++ e.modifier))),
  ("changedFiles",toJson d.changedFiles),("added",deltaJson d.added),("removed",deltaJson d.removed)]
private def outcomeJson (r : ReadOutcome) : Json := Json.mkObj [
  ("exitCode",toJson r.exitCode),("protocolValid",toJson r.protocolValid),
  ("complete",toJson r.complete),("valueAvailable",toJson r.valueAvailable)]
private def evaluate (catalog : List Blob) (ss : List Snapshot) (r : Row) : Except String Json := do
  if r.selected.length > 8 || r.selected.eraseDups.length != r.selected.length then throw "Selection bound."
  let selected ← r.selected.mapM fun id => match ss.find? (fun s => s.id == id) with
    | some s => pure s | none => throw "Unknown snapshot selection."
  if r.kind == "stats" then
    unless !selected.isEmpty && !r.metadata && !r.fullClosure && !r.fixSearch && r.availability == "present" && r.query.isEmpty do
      throw "Irrelevant statistics fields."
    let result ← if r.mode == "restore-size" then pure (some (restoreStats selected))
      else if r.mode == "files-by-contents" then pure (some (contentStats selected))
      else if r.mode == "blobs-per-file" then pure (referenceStats catalog selected true)
      else if r.mode == "path-references-proposal" then pure (referenceStats catalog selected false)
      else if r.mode == "raw-data" then pure (rawStats catalog selected)
      else throw "Unknown counting mode."
    pure (result.map statsJson |>.getD Json.null)
  else if r.kind == "diff" then
    unless r.mode.isEmpty && !r.fixSearch && r.availability == "present" && r.query.isEmpty do throw "Irrelevant diff fields."
    let [a,b] := selected | throw "A diff requires two distinct snapshots."
    pure ((diff catalog r.metadata r.fullClosure a b).map diffJson |>.getD Json.null)
  else if r.kind == "read" then
    unless r.mode.isEmpty && selected.isEmpty && !r.metadata && !r.fullClosure do throw "Irrelevant query fields."
    let query ← match r.query with
      | "listing" => pure Query.listing | "search" => pure .search
      | "statistics" => pure .statistics | "payload" => pure .payload
      | _ => throw "Unknown read scope."
    let availability ← match r.availability with
      | "present" => pure Availability.present | "missingData" => pure .missingData
      | "missingRootTree" => pure .missingRootTree | _ => throw "Unknown availability."
    pure (outcomeJson (readOutcome r.fixSearch query availability))
  else throw "Unknown comparison operation."

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one research comparison input."; return 2
  match Json.parse (← IO.FS.readFile path) >>= fromJson? (α := Input) with
  | .error e => IO.eprintln e; return 2
  | .ok input =>
    let result : Except String (List Json) := do
      if input.schema != 1 || input.profile != "restic-regular-saved-trees" ||
          input.rows.isEmpty || input.rows.length > 128 || input.catalog.length > 256 ||
          input.snapshots.isEmpty || input.snapshots.length > 8 then throw "Unsupported research schema, profile, or count."
      let catalog ← input.catalog.mapM blob
      let ss ← input.snapshots.mapM snapshot
      unless (catalog.map (·.handle)).eraseDups.length == catalog.length &&
          (ss.map (·.id)).eraseDups.length == ss.length do throw "Duplicate catalog or snapshot identity."
      input.rows.mapM (evaluate catalog ss)
    match result with
    | .error e => IO.eprintln e; return 2
    | .ok rows => IO.println (toJson rows).compress; return 0
