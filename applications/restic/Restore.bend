import Base

type Policy is Data:
  Always{}
  IfChanged{}
  IfNewer{}
  Never{}

type Existing is Data:
  Missing{}
  Correct{}
  Different{}
  Symlink{}

type TimeOrder is Data:
  Older{}
  Equal{}
  Newer{}

type Action is Data:
  Skip{}
  MetadataOnly{}
  Rewrite{}

type FileRequest is Data:
  FileRequest{policy: Policy, existing: Existing, time: TimeOrder, same_size: Bool, selected: Bool, dry: Bool, verify: Bool, valid: Bool}

type Filter is Data:
  All{}
  ExcludeRoot{}
  ExcludeChild{}
  ExcludeDirectory{}
  IncludeAlpha{}

type ExtraState is Data:
  ExtraState{root: Bool, directory: Bool, child: Bool, other: Bool}

def older(time: TimeOrder) -> Bool:
  match time:
    case Older{}: True{}
    case Equal{}: False{}
    case Newer{}: False{}

def equal_time(time: TimeOrder) -> Bool:
  match time:
    case Older{}: False{}
    case Equal{}: True{}
    case Newer{}: False{}

def existing_eligible(p: Policy, time: TimeOrder) -> Bool:
  match p:
    case Always{}: True{}
    case IfChanged{}: True{}
    case IfNewer{}: older(time)
    case Never{}: False{}

def eligible(p: Policy, e: Existing, time: TimeOrder) -> Bool:
  match e:
    case Missing{}: True{}
    case Correct{}: existing_eligible(p,time)
    case Different{}: existing_eligible(p,time)
    case Symlink{}: existing_eligible(p,time)

def trust_mtime(p: Policy, time: TimeOrder, size: Bool) -> Bool:
  match p:
    case Always{}: False{}
    case IfChanged{}: Bool.and(equal_time(time),size)
    case IfNewer{}: False{}
    case Never{}: False{}

def matches(p: Policy, e: Existing, time: TimeOrder, size: Bool) -> Bool:
  match e:
    case Missing{}: False{}
    case Correct{}: True{}
    case Different{}: trust_mtime(p,time,size)
    case Symlink{}: False{}

def choose_action(allowed: Bool, matching: Bool) -> Action:
  match allowed:
    case False{}: Skip{}
    case True{}:
      match matching:
        case True{}: MetadataOnly{}
        case False{}: Rewrite{}

def action(r: FileRequest) -> Action:
  match r:
    case FileRequest{+policy,+existing,+time,same_size,selected,dry,verify,valid}:
      choose_action(Bool.and(valid,Bool.and(selected,eligible(policy,existing,time))),matches(policy,existing,time,same_size))

def rewritten(a: Action) -> Bool:
  match a:
    case Skip{}: False{}
    case MetadataOnly{}: False{}
    case Rewrite{}: True{}

def writes(+r: FileRequest) -> Bool:
  match r:
    case FileRequest{policy,existing,time,same_size,selected,dry,verify,valid}:
      Bool.and(Bool.not(dry),rewritten(action(r)))

def content(wrote: Bool, prior: Existing) -> Existing:
  match wrote:
    case True{}: Correct{}
    case False{}: prior

def after(+r: FileRequest) -> Existing:
  match r:
    case FileRequest{policy,existing,time,same_size,selected,dry,verify,valid}: content(writes(r),existing)

def verifies(+r: FileRequest) -> Bool:
  match r:
    case FileRequest{policy,existing,time,same_size,selected,dry,verify,valid}: Bool.and(verify,writes(r))

def root_selected(f: Filter) -> Bool:
  match f:
    case All{}: True{}
    case ExcludeRoot{}: False{}
    case ExcludeChild{}: True{}
    case ExcludeDirectory{}: True{}
    case IncludeAlpha{}: False{}

def directory_selected(f: Filter) -> Bool:
  match f:
    case All{}: True{}
    case ExcludeRoot{}: True{}
    case ExcludeChild{}: True{}
    case ExcludeDirectory{}: False{}
    case IncludeAlpha{}: False{}

def child_selected(f: Filter) -> Bool:
  match f:
    case All{}: True{}
    case ExcludeRoot{}: True{}
    case ExcludeChild{}: False{}
    case ExcludeDirectory{}: False{}
    case IncludeAlpha{}: False{}

def remove_current(root_removed: Bool, +directory_removed: Bool, s: ExtraState) -> ExtraState:
  match s:
    case ExtraState{root,directory,child,other}:
      ExtraState{Bool.and(root,Bool.not(root_removed)),Bool.and(directory,Bool.not(directory_removed)),Bool.and(child,Bool.not(directory_removed)),Bool.and(other,Bool.not(directory_removed))}

def deletion_allowed(remove: Bool, dry: Bool, valid: Bool) -> Bool:
  Bool.and(remove,Bool.and(Bool.not(dry),valid))

def current_allowed(+allowed: Bool, +f: Filter, s: ExtraState) -> ExtraState:
  remove_current(Bool.and(allowed,root_selected(f)),Bool.and(allowed,directory_selected(f)),s)

def delete_current(remove: Bool, dry: Bool, valid: Bool, f: Filter, s: ExtraState) -> ExtraState:
  current_allowed(deletion_allowed(remove,dry,valid),f,s)

def proposed_final(root: Bool, directory: Bool, +child: Bool, +other: Bool, parent_removed: Bool) -> ExtraState:
  ExtraState{root,Bool.and(directory,Bool.or(Bool.not(parent_removed),Bool.or(child,other))),child,other}

def proposed_allowed(+allowed: Bool, +f: Filter, s: ExtraState) -> ExtraState:
  match s:
    case ExtraState{root,directory,child,other}:
      proposed_final(Bool.and(root,Bool.not(Bool.and(allowed,root_selected(f)))),directory,Bool.and(child,Bool.not(Bool.and(allowed,Bool.and(directory_selected(f),child_selected(f))))),Bool.and(other,Bool.not(Bool.and(allowed,directory_selected(f)))),Bool.and(allowed,directory_selected(f)))

def delete_proposed(remove: Bool, dry: Bool, valid: Bool, f: Filter, s: ExtraState) -> ExtraState:
  proposed_allowed(deletion_allowed(remove,dry,valid),f,s)

law never_can_create_missing_file:
  {after(FileRequest{Never{},Missing{},Equal{},False{},True{},False{},True{},True{}}) == Correct{} : Existing}
def never_can_create_missing_file():
  {==}

law matching_metadata_can_retain_wrong_bytes:
  {after(FileRequest{IfChanged{},Different{},Equal{},True{},True{},False{},True{},True{}}) == Different{} : Existing}
def matching_metadata_can_retain_wrong_bytes():
  {==}

law verify_excludes_metadata_only:
  {verifies(FileRequest{IfChanged{},Different{},Equal{},True{},True{},False{},True{},True{}}) == False{} : Bool}
def verify_excludes_metadata_only():
  {==}

law always_restores_changed_content:
  {after(FileRequest{Always{},Different{},Equal{},True{},True{},False{},True{},True{}}) == Correct{} : Existing}
def always_restores_changed_content():
  {==}

law equal_mtime_is_not_newer:
  {after(FileRequest{IfNewer{},Different{},Equal{},True{},True{},False{},True{},True{}}) == Different{} : Existing}
def equal_mtime_is_not_newer():
  {==}

law dry_does_not_replace_file:
  {after(FileRequest{Always{},Different{},Equal{},True{},True{},True{},False{},True{}}) == Different{} : Existing}
def dry_does_not_replace_file():
  {==}

law current_deletes_excluded_child_with_parent:
  {delete_current(True{},False{},True{},ExcludeChild{},ExtraState{True{},True{},True{},True{}}) == ExtraState{False{},False{},False{},False{}} : ExtraState}
def current_deletes_excluded_child_with_parent():
  {==}

law proposed_retains_child_and_parent:
  {delete_proposed(True{},False{},True{},ExcludeChild{},ExtraState{True{},True{},True{},True{}}) == ExtraState{False{},True{},True{},False{}} : ExtraState}
def proposed_retains_child_and_parent():
  {==}

def main() -> IO(Unit):
  IO.print("Restore overwrite, verification scope, and subtree deletion are distinct policies.")
