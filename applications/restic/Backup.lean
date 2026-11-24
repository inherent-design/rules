namespace ApplicationStudy.ResticBackup

/-- Equality witnesses from one regular file at one fixed path. Not a stat codec,
    a filesystem snapshot, or a claim that metadata equality proves byte equality. -/
structure Metadata where
  size : Bool
  mtime : Bool
  ctime : Bool
  inode : Bool
  deriving Repr

structure Capture where
  parent : Bool
  force : Bool
  ignoreCtime : Bool
  ignoreInode : Bool
  metadata : Metadata
  blobsIndexed : Bool
  readable : Bool
  priorContent : Nat
  liveContent : Nat
  deriving Repr

def metadataMatches (c : Capture) : Bool :=
  c.metadata.size && c.metadata.mtime &&
    (c.ignoreCtime || c.ignoreInode || c.metadata.ctime) &&
    (c.ignoreInode || c.metadata.inode)

def reuse (c : Capture) : Bool := c.parent && !c.force && metadataMatches c && c.blobsIndexed

def needsRead (c : Capture) : Bool := !reuse c

def captured (c : Capture) : Option Nat :=
  if reuse c then some c.priorContent
  else if c.readable then some c.liveContent else none

/-- Source/host witnesses for a completed local attempt. Same-tree means exact
    root-tree equality after capture, not only equality of live file contents. -/
structure Publication where
  rootAvailable : Bool
  fatal : Bool
  dryRun : Bool
  skipUnchanged : Bool
  sameTree : Bool
  itemErrors : Bool
  deriving Repr

inductive Effect | refused | planned | unchanged | published
  deriving BEq, DecidableEq, Repr

def effect (p : Publication) : Effect :=
  if !p.rootAvailable || p.fatal then .refused
  else if p.skipUnchanged && p.sameTree then .unchanged
  else if p.dryRun then .planned else .published

def exitCode (p : Publication) : Nat :=
  if !p.rootAvailable || p.fatal then 1 else if p.itemErrors then 3 else 0

/-- A returned ID may be only a dry-backend result; it does not prove a saved
    snapshot. Real publication needs an independently observed repository entry. -/
def hasReportedId (p : Publication) : Bool :=
  effect p == .planned || effect p == .published

def savedReference (p : Publication) : Bool := effect p == .published

def baseline : Capture := ⟨true, false, false, false, ⟨true,true,true,true⟩,true,true,1,2⟩
def normal : Publication := ⟨true,false,false,false,false,false⟩

theorem force_requires_read (c : Capture) : needsRead {c with force := true} = true := by
  simp [needsRead, reuse]

theorem missing_parent_requires_read (c : Capture) : needsRead {c with parent := false} = true := by
  simp [needsRead, reuse]

theorem missing_index_disables_reuse (c : Capture) : reuse {c with blobsIndexed := false} = false := by
  simp [reuse]

theorem changed_size_requires_read (c : Capture) :
    needsRead {c with metadata := {c.metadata with size := false}} = true := by
  simp [needsRead, reuse, metadataMatches]

theorem changed_mtime_requires_read (c : Capture) :
    needsRead {c with metadata := {c.metadata with mtime := false}} = true := by
  simp [needsRead, reuse, metadataMatches]

theorem ignore_inode_also_ignores_ctime (c : Capture) :
    metadataMatches {c with ignoreInode := true} = (c.metadata.size && c.metadata.mtime) := by
  simp [metadataMatches]

theorem ignore_ctime_keeps_inode_check :
    reuse {baseline with ignoreCtime := true, metadata := ⟨true,true,false,false⟩} = false := by decide

theorem metadata_reuse_does_not_prove_live_bytes : captured baseline = some 1 ∧ baseline.liveContent = 2 := by decide

theorem changed_ctime_default_reads :
    captured {baseline with metadata := ⟨true,true,false,true⟩} = some 2 := by decide

theorem ignored_ctime_can_reuse_prior_bytes :
    captured {baseline with ignoreCtime := true, metadata := ⟨true,true,false,true⟩} = some 1 := by decide

theorem unreadable_read_has_no_file :
    captured {baseline with force := true, readable := false} = none := by decide

theorem partial_read_failure_can_publish :
    effect {normal with itemErrors := true} = .published ∧ exitCode {normal with itemErrors := true} = 3 := by decide

theorem zero_status_need_not_create_snapshot :
    exitCode {normal with skipUnchanged := true, sameTree := true} = 0 ∧
    savedReference {normal with skipUnchanged := true, sameTree := true} = false := by decide

theorem reported_id_is_not_saved_evidence :
    hasReportedId {normal with dryRun := true} = true ∧
    savedReference {normal with dryRun := true} = false := by decide

theorem fatal_does_not_publish (p : Publication) : effect {p with fatal := true} = .refused := by
  simp [effect]

theorem ordinary_unchanged_still_publishes : effect {normal with sameTree := true} = .published := by decide

theorem skip_requires_exact_tree :
    effect {normal with skipUnchanged := true, sameTree := false} = .published := by decide

theorem unchanged_skip_does_not_invent_error :
    exitCode {normal with skipUnchanged := true, sameTree := true} = exitCode normal := rfl

end ApplicationStudy.ResticBackup
