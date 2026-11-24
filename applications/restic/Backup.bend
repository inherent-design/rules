import Base

type Metadata is Data:
  Metadata { size: Bool, mtime: Bool, ctime: Bool, inode: Bool }

type Capture is Data:
  Capture { parent: Bool, force: Bool, ignore_ctime: Bool, ignore_inode: Bool, metadata: Metadata, blobs_indexed: Bool, readable: Bool, prior: Nat, live: Nat }

type Publication is Data:
  Publication { root: Bool, fatal: Bool, dry: Bool, skip: Bool, same_tree: Bool, item_errors: Bool }

type Effect is Data:
  Refused{}
  Planned{}
  Unchanged{}
  Published{}

def matches(ignore_ctime: Bool, +ignore_inode: Bool, m: Metadata) -> Bool:
  match m:
    case Metadata{size,mtime,ctime,inode}:
      Bool.and(size,Bool.and(mtime,Bool.and(Bool.or(ignore_ctime,Bool.or(ignore_inode,ctime)),Bool.or(ignore_inode,inode))))

def reuse(c: Capture) -> Bool:
  match c:
    case Capture{parent,force,ignore_ctime,ignore_inode,metadata,blobs_indexed,readable,prior,live}:
      Bool.and(parent,Bool.and(Bool.not(force),Bool.and(matches(ignore_ctime,ignore_inode,metadata),blobs_indexed)))

def captured(+c: Capture) -> Nat:
  match c:
    case Capture{parent,force,ignore_ctime,ignore_inode,metadata,blobs_indexed,readable,prior,live}:
      Bool.pick(Nat,reuse(c),prior,Bool.pick(Nat,readable,live,0n))

def effect(p: Publication) -> Effect:
  match p:
    case Publication{root,fatal,dry,skip,same_tree,item_errors}:
      Bool.pick(Effect,Bool.or(Bool.not(root),fatal),Refused{},Bool.pick(Effect,Bool.and(skip,same_tree),Unchanged{},Bool.pick(Effect,dry,Planned{},Published{})))

def exit_code(p: Publication) -> Nat:
  match p:
    case Publication{root,fatal,dry,skip,same_tree,item_errors}:
      Bool.pick(Nat,Bool.or(Bool.not(root),fatal),1n,Bool.pick(Nat,item_errors,3n,0n))

def effect_has_id(e: Effect) -> Bool:
  match e:
    case Refused{}: False{}
    case Planned{}: True{}
    case Unchanged{}: False{}
    case Published{}: True{}

def has_reported_id(p: Publication) -> Bool:
  effect_has_id(effect(p))

def baseline() -> Capture:
  Capture{True{},False{},False{},False{},Metadata{True{},True{},True{},True{}},True{},True{},1n,2n}

def effect_name(e: Effect) -> String:
  match e:
    case Refused{}: "refused"
    case Planned{}: "planned"
    case Unchanged{}: "unchanged"
    case Published{}: "published"

law equal_metadata_can_reuse_different_live_bytes:
  {captured(baseline()) == 1n : Nat}
def equal_metadata_can_reuse_different_live_bytes():
  {==}

law ignored_ctime_can_reuse_prior_content:
  {captured(Capture{True{},False{},True{},False{},Metadata{True{},True{},False{},True{}},True{},True{},1n,2n}) == 1n : Nat}
def ignored_ctime_can_reuse_prior_content():
  {==}

law default_ctime_change_reads_live:
  {captured(Capture{True{},False{},False{},False{},Metadata{True{},True{},False{},True{}},True{},True{},1n,2n}) == 2n : Nat}
def default_ctime_change_reads_live():
  {==}

law force_reads_despite_equal_metadata:
  {captured(Capture{True{},True{},False{},False{},Metadata{True{},True{},True{},True{}},True{},True{},1n,2n}) == 2n : Nat}
def force_reads_despite_equal_metadata():
  {==}

law ignored_inode_still_requires_mtime:
  {reuse(Capture{True{},False{},False{},True{},Metadata{True{},False{},False{},False{}},True{},True{},1n,2n}) == False{} : Bool}
def ignored_inode_still_requires_mtime():
  {==}

law partial_source_failure_keeps_publication:
  {effect(Publication{True{},False{},False{},False{},False{},True{}}) == Published{} : Effect}
def partial_source_failure_keeps_publication():
  {==}

law partial_source_failure_returns_three:
  {exit_code(Publication{True{},False{},False{},False{},False{},True{}}) == 3n : Nat}
def partial_source_failure_returns_three():
  {==}

law dry_mode_can_report_id:
  {has_reported_id(Publication{True{},False{},True{},False{},False{},False{}}) == True{} : Bool}
def dry_mode_can_report_id():
  {==}

law dry_mode_is_planned:
  {effect(Publication{True{},False{},True{},False{},False{},False{}}) == Planned{} : Effect}
def dry_mode_is_planned():
  {==}
