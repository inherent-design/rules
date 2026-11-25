namespace ApplicationStudy.ResticComparison

inductive BlobKind where | data | tree deriving BEq, DecidableEq, Repr
structure Handle where
  kind : BlobKind
  id : Nat -- finite opaque ID label, not a persistent or numeric hash
  deriving BEq, DecidableEq, Repr
structure Blob where
  handle : Handle
  plain : Nat
  cipher : Nat
  uncompressedCipher : Nat
  compressed : Bool
  deriving BEq, DecidableEq, Repr
inductive NodeKind where | file | directory deriving BEq, DecidableEq, Repr
abbrev SavedPath := List String -- admitted tree components, not host path strings
structure Node where
  path : SavedPath
  location : SavedPath -- actual per-file accumulator key; separate from content
  kind : NodeKind
  contentPresent : Bool
  content : List Nat
  metadataBasis : Nat -- exact finite equality witness excluding Content
  subtree : Option Nat
  size : Nat
  deriving BEq, DecidableEq, Repr
structure Snapshot where
  id : Nat
  root : Nat
  nodes : List Node -- admitted source-tree preorder, no virtual root node
  deriving BEq, DecidableEq, Repr

def nodeRefs (n : Node) : List Handle := match n.kind with
  | .file => n.content.map (fun id => ⟨.data,id⟩)
  | .directory => n.subtree.toList.map (fun id => ⟨.tree,id⟩)
def closure (s : Snapshot) : List Handle :=
  (⟨.tree,s.root⟩ :: s.nodes.flatMap nodeRefs).eraseDups
def lookup (catalog : List Blob) (h : Handle) : Option Blob := catalog.find? (fun b => b.handle == h)
def weights (catalog : List Blob) (handles : List Handle) : Option (List Blob) := handles.mapM (lookup catalog)
def total (rows : List Blob) (measure : Blob → Nat) : Nat := rows.foldl (fun n b => n + measure b) 0

structure Stats where
  size : Nat := 0
  countedEntries : Nat := 0 -- meaning depends on the selected mode
  blobCount : Nat := 0
  snapshots : Nat := 0
  uncompressed : Nat := 0
  compressedSize : Nat := 0
  compressedUncompressed : Nat := 0
  deriving BEq, DecidableEq, Repr
def restoreStats (ss : List Snapshot) : Stats :=
  let nodes := ss.flatMap (·.nodes)
  -- Selected native profile: regular files with one link, plus directories.
  -- General hardlink/device policy is an explicit external obligation.
  ⟨nodes.foldl (fun n r => n+r.size) 0,nodes.length,0,ss.length,0,0,0⟩
structure ContentState where
  seen : List (List Nat) := []
  size : Nat := 0
  count : Nat := 0
  deriving BEq, DecidableEq, Repr
def visitContent (s : ContentState) (n : Node) : ContentState :=
  if s.seen.contains n.content then s else ⟨n.content::s.seen,s.size+n.size,s.count+1⟩
def contentStats (ss : List Snapshot) : Stats :=
  let state := (ss.flatMap (·.nodes)).foldl visitContent {}
  -- Nil/empty Content share a sequence fingerprint here. This is intentionally
  -- different from Node.sameContent's presence-sensitive diff comparison.
  ⟨state.size,state.count,0,ss.length,0,0,0⟩
structure RefState where
  seenContent : List (List Nat) := []
  refs : List (SavedPath × Nat) := []
  locations : List SavedPath := []
  deriving BEq, DecidableEq, Repr
def visitReferences (contentGate : Bool) (s : RefState) (n : Node) : RefState :=
  if contentGate && s.seenContent.contains n.content then s else
  let refs := (n.content.map (fun id => (n.location,id)) ++ s.refs).eraseDups
  let locations := if n.content.isEmpty then s.locations else (n.location::s.locations).eraseDups
  ⟨n.content::s.seenContent,refs,locations⟩
def referenceStats (catalog : List Blob) (ss : List Snapshot) (contentGate : Bool) : Option Stats := do
  let state := (ss.flatMap (·.nodes)).foldl (visitReferences contentGate) {}
  let rows ← weights catalog (state.refs.map (fun r => ⟨.data,r.2⟩))
  pure ⟨total rows (·.plain),state.locations.length,state.refs.length,ss.length,0,0,0⟩
def rawStats (catalog : List Blob) (ss : List Snapshot) : Option Stats := do
  let refs := (ss.flatMap closure).eraseDups
  let rows ← weights catalog refs
  let compressed := rows.filter (·.compressed)
  pure ⟨total rows (·.cipher),0,refs.length,ss.length,total rows (·.uncompressedCipher),
    total compressed (·.cipher),total compressed (·.uncompressedCipher)⟩

def byPath (nodes : List Node) (path : SavedPath) : Option Node := nodes.find? (fun n => n.path == path)
def contentEqual (a b : Node) : Bool := a.contentPresent == b.contentPresent && a.content == b.content
def fullEqual (a b : Node) : Bool := a.kind == b.kind && a.metadataBasis == b.metadataBasis && contentEqual a b
def below (root path : SavedPath) : Bool := root.length < path.length && root.isPrefixOf path
def typeBoundaries (a b : Snapshot) : List SavedPath := a.nodes.filterMap fun n => do
  let other ← byPath b.nodes n.path
  if n.kind != other.kind then some n.path else none
def observableNodes (a b : Snapshot) (nodes : List Node) : List Node :=
  nodes.filter (fun n => !(typeBoundaries a b).any (fun p => below p n.path))
def insertPath (path : SavedPath) : List SavedPath → List SavedPath
  | [] => [path]
  | head::tail => if compare path head != .gt then path::head::tail else head::insertPath path tail
def pairedPaths (a b : Snapshot) : List SavedPath :=
  -- Structural insertion sort is a specification implementation. Component
  -- order preserves tree preorder; a plain full-path string sort does not.
  ((a.nodes.map (·.path)) ++ b.nodes.map (·.path)).eraseDups.foldr insertPath []
structure Change where
  path : SavedPath
  directory : Bool -- the wire renderer adds the source's trailing slash
  modifier : String
  deriving BEq, DecidableEq, Repr
def change (metadata : Bool) (path : SavedPath) (before after : Option Node) : Option Change :=
  match before,after with
  | none,none => none
  | none,some b => some ⟨path,b.kind == .directory,"+"⟩
  | some a,none => some ⟨path,a.kind == .directory,"-"⟩
  | some a,some b =>
    let typeFlag := if a.kind != b.kind then "T" else ""
    let mod := if a.kind == .file && b.kind == .file && !contentEqual a b then
        "M" ++ (if a.metadataBasis == b.metadataBasis then "?" else "")
      else if metadata && !fullEqual a b then "U" else ""
    if (typeFlag++mod).isEmpty then none else some ⟨path,b.kind == .directory,typeFlag++mod⟩
def changes (metadata : Bool) (a b : Snapshot) : List Change :=
  let roots := typeBoundaries a b
  (pairedPaths a b).filterMap fun path =>
    if roots.any (fun root => below root path) then none
    else change metadata path (byPath a.nodes path) (byPath b.nodes path)
structure Delta where
  files : Nat
  directories : Nat
  dataBlobs : Nat
  treeBlobs : Nat
  bytes : Nat
  deriving BEq, DecidableEq, Repr
def delta (catalog : List Blob) (nodes : List Node) (refs : List Handle) : Option Delta := do
  let rows ← weights catalog refs
  pure ⟨(nodes.filter (fun n => n.kind == .file)).length,(nodes.filter (fun n => n.kind == .directory)).length,
    (refs.filter (fun h => h.kind == .data)).length,(refs.filter (fun h => h.kind == .tree)).length,total rows (·.plain)⟩
structure Diff where
  events : List Change
  changedFiles : Nat
  added : Delta
  removed : Delta
  deriving BEq, DecidableEq, Repr
/-- Full closure is the proposed counter policy. It does not change the source
    event policy (a type change is one event, not a recursive list of additions). -/
def diff (catalog : List Blob) (metadata fullClosure : Bool) (a b : Snapshot) : Option Diff := do
  let av := observableNodes a b a.nodes
  let bv := observableNodes a b b.nodes
  let refs (s : Snapshot) (visible : List Node) :=
    if fullClosure then closure s else (⟨.tree,s.root⟩::visible.flatMap nodeRefs).eraseDups
  let ar := refs a av
  let br := refs b bv
  let addedRefs := br.filter (fun h => !ar.contains h)
  let removedRefs := ar.filter (fun h => !br.contains h)
  let addedNodes := bv.filter (fun n => (byPath a.nodes n.path).isNone)
  let removedNodes := av.filter (fun n => (byPath b.nodes n.path).isNone)
  let events := changes metadata a b
  let changed := (av.filter fun n => match byPath b.nodes n.path with
    | none => false
    | some other => n.kind == .file && other.kind == .file && !contentEqual n other).length
  pure ⟨events,changed,← delta catalog addedNodes addedRefs,← delta catalog removedNodes removedRefs⟩

inductive Availability where | present | missingData | missingRootTree deriving BEq, DecidableEq, Repr
inductive Query where | listing | search | statistics | payload deriving BEq, DecidableEq, Repr
structure ReadOutcome where
  exitCode : Nat
  protocolValid : Bool
  complete : Bool -- completeness of this query's declared reads, not restore proof
  valueAvailable : Bool -- may be partial (for example a listing's snapshot header)
  deriving BEq, DecidableEq, Repr
/-- Selected root-load cases after argument admission. This is not the parser,
    a guarantee for nested/ID-search faults, or a payload-integrity verdict. -/
def readOutcome (fixSearch : Bool) (query : Query) (availability : Availability) : ReadOutcome :=
  match availability with
  | .present => ⟨0,true,true,true⟩
  | .missingData => if query == .payload then ⟨1,true,false,false⟩ else ⟨0,true,true,true⟩
  | .missingRootTree =>
    if query == .search then
      if fixSearch then ⟨1,true,false,true⟩ else ⟨0,false,false,false⟩
    else if query == .listing then ⟨1,true,false,true⟩ else ⟨1,true,false,false⟩

def exampleBlob (kind : BlobKind) (id size : Nat) : Blob := ⟨⟨kind,id⟩,size,size+2,size+2,false⟩
def exampleFile (path : SavedPath) (content : List Nat) (size : Nat := 1) : Node :=
  ⟨path,path++path.getLast?.toList,.file,true,content,0,none,size⟩
def exampleDir (path : SavedPath) (subtree : Nat) : Node :=
  ⟨path,path++path.getLast?.toList,.directory,false,[],1,some subtree,0⟩
def smallCatalog : List Blob := [exampleBlob .tree 10 1,exampleBlob .tree 11 1,exampleBlob .tree 12 1,
  exampleBlob .data 0 1,exampleBlob .data 1 1,exampleBlob .data 2 1]
def equalCopies : Snapshot := ⟨0,10,[exampleFile ["a"] [0,1] 2,exampleFile ["b"] [0,1] 2]⟩
def editedCopy : Snapshot := ⟨1,11,[exampleFile ["a"] [0,2] 2,exampleFile ["b"] [0,1] 2]⟩

theorem metadata_query_does_not_establish_payload_availability :
    readOutcome false .listing .missingData = ⟨0,true,true,true⟩ ∧
    readOutcome false .payload .missingData = ⟨1,true,false,false⟩ := by decide
theorem successful_exit_does_not_establish_valid_search_json :
    readOutcome false .search .missingRootTree = ⟨0,false,false,false⟩ := by decide
theorem proposed_search_retains_failure_and_protocol :
    readOutcome true .search .missingRootTree = ⟨1,true,false,true⟩ := by decide
theorem listing_failure_can_retain_a_snapshot_header :
    readOutcome false .listing .missingRootTree = ⟨1,true,false,true⟩ := by decide
theorem different_blob_namespaces_do_not_alias :
    (⟨BlobKind.data,1⟩ : Handle) != ⟨BlobKind.tree,1⟩ := by decide
theorem missing_weight_is_not_zero : weights [] [⟨.data,1⟩] = none := by decide
theorem content_count_merges_equal_bytes_at_distinct_paths :
    (contentStats [equalCopies]).size = 2 ∧ (restoreStats [equalCopies]).size = 4 := by decide
theorem source_reference_gate_can_discard_coexisting_locations :
    (referenceStats smallCatalog [equalCopies] true).map (·.size) = some 2 ∧
    (referenceStats smallCatalog [equalCopies] false).map (·.size) = some 4 := by decide
theorem source_reference_gate_can_depend_on_snapshot_order :
    (referenceStats smallCatalog [equalCopies,editedCopy] true).map (·.size) = some 3 ∧
    (referenceStats smallCatalog [editedCopy,equalCopies] true).map (·.size) = some 4 := by decide
theorem path_reference_alternative_preserves_both_orders :
    (referenceStats smallCatalog [equalCopies,editedCopy] false).map (·.size) = some 5 ∧
    (referenceStats smallCatalog [editedCopy,equalCopies] false).map (·.size) = some 5 := by decide

def beforeTypeChange : Snapshot := ⟨0,10,[exampleFile ["shape"] [0]]⟩
def afterTypeChange : Snapshot := ⟨1,11,[exampleDir ["shape"] 12,exampleFile ["shape","child"] [1]]⟩
theorem source_type_event_does_not_list_the_new_child :
    changes false beforeTypeChange afterTypeChange = [⟨["shape"],true,"T"⟩] := by decide
theorem source_type_boundary_omits_a_new_data_reference :
    (diff smallCatalog false false beforeTypeChange afterTypeChange).map (fun r => r.added.dataBlobs) = some 0 ∧
    (diff smallCatalog false true beforeTypeChange afterTypeChange).map (fun r => r.added.dataBlobs) = some 1 := by decide
theorem closure_correction_preserves_type_event :
    (diff smallCatalog false false beforeTypeChange afterTypeChange).map (·.events) =
    (diff smallCatalog false true beforeTypeChange afterTypeChange).map (·.events) := by decide
def reusedAfterTypeChange : Snapshot := ⟨2,10,[exampleFile ["shape"] [2],exampleFile ["reused"] [1]]⟩
theorem opaque_type_boundary_can_also_falsely_count_a_reused_blob_as_new :
    (diff smallCatalog false false afterTypeChange reusedAfterTypeChange).map (fun r => r.added.dataBlobs) = some 2 ∧
    (diff smallCatalog false true afterTypeChange reusedAfterTypeChange).map (fun r => r.added.dataBlobs) = some 1 := by decide
theorem same_data_moved_to_a_different_path_is_not_new_data :
    (diff smallCatalog false true ⟨0,10,[exampleFile ["old"] [0]]⟩
      ⟨1,11,[exampleFile ["new"] [0]]⟩).map (fun r => r.added.dataBlobs) = some 0 := by decide
theorem equal_metadata_content_change_has_suspect_marker :
    change false ["a"] (some (exampleFile ["a"] [0])) (some (exampleFile ["a"] [1])) =
      some ⟨["a"],false,"M?"⟩ := by decide
theorem content_presence_is_distinct_for_diff_but_not_content_stats :
    contentEqual (exampleFile ["empty"] [] 0) {exampleFile ["empty"] [] 0 with contentPresent := false} = false ∧
    (contentStats [⟨0,10,[exampleFile ["empty"] [] 0,
      {exampleFile ["empty"] [] 0 with contentPresent := false}]⟩]).countedEntries = 1 := by decide
theorem repeated_tree_is_one_raw_reference_set_but_two_restore_images :
    (rawStats smallCatalog [equalCopies,{equalCopies with id := 2}]).map (·.size) =
      (rawStats smallCatalog [equalCopies]).map (·.size) ∧
    (restoreStats [equalCopies,{equalCopies with id := 2}]).size = 8 := by decide
theorem restored_entry_count_includes_directories :
    restoreStats [⟨0,10,[exampleDir ["empty"] 12]⟩] = ⟨0,1,0,1,0,0,0⟩ := by decide
theorem raw_weight_preserves_same_label_in_two_blob_namespaces :
    rawStats [exampleBlob .tree 0 2,exampleBlob .data 0 1]
      [⟨0,0,[exampleFile ["a"] [0]]⟩] = some ⟨7,0,2,1,7,0,0⟩ := by decide

end ApplicationStudy.ResticComparison
