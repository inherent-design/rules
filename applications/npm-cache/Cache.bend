import Base

# Selected referenced-object and installed-fixture projections,not cache/lock
# codecs. Body0/1/2=absent/verified/corrupt;installation0/1/2=absent/original/edit.
type CState is Data:
  CState{backing: Nat, installed: Nat, author: Nat}
type CResult is Data:
  CResult{state: CState, exit: Nat, requests: Nat}
def verify(s: CState,referenced: Bool) -> CResult:
  match s:
    case CState{backing,installed,author}:
      CResult{CState{Bool.pick(Nat,Bool.and(referenced,Nat.is_eq(backing,1n)),1n,0n),installed,author},0n,0n}
def admitted(s: CState,index: Bool,+origin: Bool) -> CResult:
  match s:
    case CState{+backing,_,+author}:
      +hit=Bool.and(index,Nat.is_eq(backing,1n))
      Bool.pick(CResult,Bool.or(hit,origin),CResult{CState{1n,1n,author},0n,Bool.pick(Nat,hit,0n,1n)},CResult{CState{backing,0n,author},1n,0n})
def clean_install(+s: CState,lock: Bool,index: Bool,origin: Bool) -> CResult:
  Bool.pick(CResult,lock,admitted(s,index,origin),CResult{s,1n,0n})
def corrupt_backing(s: CState) -> CResult:
  match s:
    case CState{_,installed,author}: CResult{CState{2n,installed,author},0n,0n}
def edit_installed(s: CState) -> CResult:
  match s:
    case CState{backing,_,author}: CResult{CState{backing,2n,author},0n,0n}
def observe(s: CState) -> CResult:
  CResult{s,0n,0n}
def current(+kind: Nat,+s: CState,referenced: Bool,lock: Bool,index: Bool,origin: Bool) -> CResult:
  Bool.pick(CResult,Nat.is_eq(kind,0n),verify(s,referenced),Bool.pick(CResult,Nat.is_eq(kind,1n),clean_install(s,lock,index,origin),Bool.pick(CResult,Nat.is_eq(kind,2n),corrupt_backing(s),Bool.pick(CResult,Nat.is_eq(kind,3n),edit_installed(s),observe(s)))))
def available(s: CState) -> Bool:
  match s:
    case CState{_,installed,_}: Bool.not(Nat.is_eq(installed,0n))
def preflight(s: CState,+lock: Bool,+index: Bool,+origin: Bool) -> CResult:
  match s:
    case CState{+backing,+installed,+author}:
      absent=Bool.not(Bool.or(Bool.and(index,Nat.is_eq(backing,1n)),origin))
      Bool.pick(CResult,Bool.and(lock,absent),CResult{CState{backing,installed,author},1n,0n},clean_install(CState{backing,installed,author},lock,index,origin))
def render(r: CResult) -> String:
  match r:
    case CResult{CState{backing,installed,author},exit,n}:
      Nat.show(backing) ++ "/" ++ Nat.show(installed) ++ "/" ++ Nat.show(author) ++ "/" ++ Nat.show(exit) ++ "/" ++ Nat.show(n)

law verify_removes_corruption_without_clearing_installation:
  {render(verify(CState{2n,1n,1n},True{})) == "0/1/1/0/0" : String}
def verify_removes_corruption_without_clearing_installation():
  {==}
law cache_verify_preserves_edited_installation:
  {render(verify(CState{1n,2n,1n},True{})) == "1/2/1/0/0" : String}
def cache_verify_preserves_edited_installation():
  {==}
law clean_offline_failure_can_clear_old_installation:
  {render(clean_install(CState{0n,1n,1n},True{},False{},False{})) == "0/0/1/1/0" : String}
def clean_offline_failure_can_clear_old_installation():
  {==}
law matching_cache_restores_original_without_origin:
  {render(clean_install(CState{1n,2n,1n},True{},True{},False{})) == "1/1/1/0/0" : String}
def matching_cache_restores_original_without_origin():
  {==}
law origin_recovery_is_distinct_from_cache_hit:
  {render(clean_install(CState{0n,0n,1n},True{},False{},True{})) == "1/1/1/0/1" : String}
def origin_recovery_is_distinct_from_cache_hit():
  {==}
law file_without_matching_index_is_not_a_cache_hit:
  {render(clean_install(CState{1n,1n,1n},True{},False{},False{})) == "1/0/1/1/0" : String}
def file_without_matching_index_is_not_a_cache_hit():
  {==}
law unreferenced_bytes_are_evictable:
  {render(verify(CState{1n,1n,1n},False{})) == "0/1/1/0/0" : String}
def unreferenced_bytes_are_evictable():
  {==}
law proposed_preflight_keeps_old_installation_on_known_miss:
  {render(preflight(CState{0n,1n,1n},True{},False{},False{})) == "0/1/1/1/0" : String}
def proposed_preflight_keeps_old_installation_on_known_miss():
  {==}
