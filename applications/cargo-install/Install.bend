import Base

# body 0 absent,1 v1,2 v2,3 owned manual script,4 untracked,5 directory.
# Owner0 absent,1/2 exact fixture package identities (source bound externally).
type Slot is Data:
  Slot{body: Nat, owner: Nat}
type State is Data:
  State{a: Slot,b: Slot,metadata: Bool}
type InstallResult is Data:
  InstallResult{state: State,exit: Nat}
def exists(s: Slot) -> Bool:
  match s:
    case Slot{body,_}: Bool.not(Nat.is_eq(body,0n))
def collision(s: Slot) -> Bool:
  match s:
    case Slot{body,owner}: Bool.and(Bool.not(Nat.is_eq(body,0n)),Nat.is_eq(owner,0n))
def is_dir(s: Slot) -> Bool:
  match s:
    case Slot{body,_}: Nat.is_eq(body,5n)
def published(+s: Slot,ok: Bool,+v: Nat) -> Slot:
  Bool.pick(Slot,ok,Slot{v,v},s)
def rolled(s: Slot,remove: Bool) -> Slot:
  match s:
    case Slot{body,owner}: Slot{Bool.pick(Nat,remove,0n,body),owner}
def publish(s: State,+v: Nat,+keep: Bool) -> InstallResult:
  match s:
    case State{+a,+b,_}:
      +na=Bool.not(exists(a))
      +nb=Bool.not(exists(b))
      +fa=is_dir(a)
      +fb=Bool.and(Bool.not(fa),is_dir(b))
      +failed=Bool.or(fa,fb)
      +rollback=Bool.and(failed,Bool.not(keep))
      anew=published(a,Bool.or(na,Bool.not(fa)),v)
      bnew=published(b,Bool.or(nb,Bool.and(Bool.not(fa),Bool.not(fb))),v)
      InstallResult{State{rolled(anew,Bool.and(rollback,na)),rolled(bnew,Bool.and(rollback,nb)),True{}},Bool.pick(Nat,failed,101n,0n)}
def install(s: State,force: Bool,compile_ok: Bool,v: Nat,keep: Bool) -> InstallResult:
  match s:
    case State{+a,+b,_}:
      denied=Bool.or(Bool.and(Bool.not(force),Bool.or(collision(a),collision(b))),Bool.not(compile_ok))
      +loaded : State = State{a,b,True{}}
      Bool.pick(InstallResult,denied,InstallResult{loaded,101n},publish(loaded,v,keep))
def missing_owned(s: Slot) -> Bool:
  match s:
    case Slot{body,owner}: Bool.and(Bool.not(Nat.is_eq(owner,0n)),Nat.is_eq(body,0n))
def remove_selected(s: Slot,selected: Bool) -> Slot:
  match s:
    case Slot{body,+owner}: Bool.pick(Slot,Bool.and(selected,Bool.not(Nat.is_eq(owner,0n))),Slot{0n,0n},Slot{body,owner})
def uninstall(s: State,sa: Bool,sb: Bool) -> InstallResult:
  match s:
    case State{+a,+b,+metadata}:
      denied=Bool.or(missing_owned(a),missing_owned(b))
      Bool.pick(InstallResult,denied,InstallResult{State{a,b,metadata},101n},InstallResult{State{remove_selected(a,sa),remove_selected(b,sb),metadata},0n})
def control(s: State,+action: Nat) -> InstallResult:
  match s:
    case State{Slot{ab,+ao},Slot{bb,+bo},metadata}:
      edit_a=Bool.or(Nat.is_eq(action,0n),Nat.is_eq(action,5n))
      newb=Bool.pick(Nat,Nat.is_eq(action,1n),5n,Bool.pick(Nat,Nat.is_eq(action,2n),1n,Bool.pick(Nat,Nat.is_eq(action,3n),0n,Bool.pick(Nat,Nat.is_eq(action,4n),2n,bb))))
      InstallResult{State{Slot{Bool.pick(Nat,edit_a,3n,ab),ao},Slot{newb,bo},metadata},0n}
def current(+kind: Nat,+s: State,+force: Bool,+compile_ok: Bool,+v: Nat,+sa: Bool,+sb: Bool,+action: Nat,+keep: Bool) -> InstallResult:
  Bool.pick(InstallResult,Nat.is_eq(kind,0n),install(s,force,compile_ok,v,keep),Bool.pick(InstallResult,Nat.is_eq(kind,1n),uninstall(s,sa,sb),Bool.pick(InstallResult,Nat.is_eq(kind,3n),control(s,action),InstallResult{s,0n})))
def render(r: InstallResult) -> String:
  match r:
    case InstallResult{State{Slot{ab,ao},Slot{bb,bo},m},e}:
      Nat.show(ab) ++ "/" ++ Nat.show(ao) ++ "/" ++ Nat.show(bb) ++ "/" ++ Nat.show(bo) ++ "/" ++ Bool.pick(String,m,"1","0") ++ "/" ++ Nat.show(e)

law early_refusal_can_create_tracking_files:
  {render(install(State{Slot{4n,0n},Slot{0n,0n},False{}},False{},True{},1n,False{})) == "4/0/0/0/1/101" : String}
def early_refusal_can_create_tracking_files(): {==}
law force_replaces_owned_untracked_fixture:
  {render(install(State{Slot{4n,0n},Slot{0n,0n},False{}},True{},True{},1n,False{})) == "1/1/1/1/1/0" : String}
def force_replaces_owned_untracked_fixture(): {==}
law path_reinstall_replaces_manual_bytes:
  {render(install(State{Slot{3n,1n},Slot{1n,1n},True{}},False{},True{},1n,False{})) == "1/1/1/1/1/0" : String}
def path_reinstall_replaces_manual_bytes(): {==}
law compile_failure_keeps_installed_bins:
  {render(install(State{Slot{1n,1n},Slot{1n,1n},True{}},False{},False{},1n,False{})) == "1/1/1/1/1/101" : String}
def compile_failure_keeps_installed_bins(): {==}
law failed_replacement_keeps_successful_existing_prefix:
  {render(install(State{Slot{1n,1n},Slot{5n,1n},True{}},False{},True{},2n,False{})) == "2/2/5/1/1/101" : String}
def failed_replacement_keeps_successful_existing_prefix(): {==}
law new_bin_rollback_leaves_saved_registration:
  {render(install(State{Slot{5n,0n},Slot{0n,0n},False{}},True{},True{},2n,False{})) == "5/0/0/2/1/101" : String}
def new_bin_rollback_leaves_saved_registration(): {==}
law missing_unselected_bin_blocks_uninstall:
  {render(uninstall(State{Slot{1n,1n},Slot{0n,1n},True{}},True{},False{})) == "1/1/0/1/1/101" : String}
def missing_unselected_bin_blocks_uninstall(): {==}
law registered_manual_bytes_are_removed:
  {render(uninstall(State{Slot{3n,1n},Slot{1n,1n},True{}},True{},False{})) == "0/0/1/1/1/0" : String}
def registered_manual_bytes_are_removed(): {==}
law proposed_keep_committed_new_bin_still_fails:
  {render(install(State{Slot{5n,0n},Slot{0n,0n},False{}},True{},True{},2n,True{})) == "5/0/2/2/1/101" : String}
def proposed_keep_committed_new_bin_still_fails(): {==}
