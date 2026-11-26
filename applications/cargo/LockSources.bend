import Base

# Selected owned fixture only. Selection0=none,1=path1,2=path2,
# 3=GitA,4=GitB,5=patched. Package keys3/4 deliberately differ from
# exact-selection IDs: GitA/GitB share key3;patched has key4.
type Cache is Data:
  Cache{head: Nat,has_a: Bool,has_b: Bool}
type Request is Data:
  Request{source: Nat,operation: Nat,locked: Bool,offline: Bool,path_v2: Bool,remote_b: Bool,old: Nat,cache: Cache}
type Outcome is Data:
  Outcome{code: Nat,after: Nat,cache: Cache,metadata: Nat,changed: Bool}
def package_key(+s: Nat) -> Nat:
  Bool.pick(Nat,Bool.or(Nat.is_eq(s,3n),Nat.is_eq(s,4n)),3n,Bool.pick(Nat,Nat.is_eq(s,5n),4n,s))
def revision(+s: Nat) -> Nat:
  Bool.pick(Nat,Nat.is_eq(s,3n),1n,Bool.pick(Nat,Nat.is_eq(s,4n),2n,0n))
def cached(c: Cache,+s: Nat) -> Bool:
  match c:
    case Cache{_,a,b}: Bool.or(Bool.and(Nat.is_eq(s,3n),a),Bool.and(Nat.is_eq(s,4n),b))
def mask(c: Cache) -> Nat:
  match c:
    case Cache{_,a,b}: Nat.add(Bool.pick(Nat,a,1n,0n),Bool.pick(Nat,b,2n,0n))
def cache_head(c: Cache) -> Nat:
  match c:
    case Cache{head,_,_}: head
def retain(c: Cache,+s: Nat) -> Cache:
  match c:
    case Cache{_,a,b}: Cache{revision(s),Bool.or(a,Nat.is_eq(s,3n)),Bool.or(b,Nat.is_eq(s,4n))}
def wanted(r: Request) -> Nat:
  match r:
    case Request{source,operation,_,offline,pv2,remote_b,+old,+cache}:
      match source:
        case 0n: Bool.pick(Nat,pv2,2n,1n)
        case 1n:
          Bool.pick(Nat,Bool.and(Nat.is_eq(operation,0n),Nat.is_gt(revision(old),0n)),old,Bool.pick(Nat,offline,Bool.pick(Nat,Nat.is_eq(cache_head(cache),0n),0n,Nat.add(cache_head(cache),2n)),Bool.pick(Nat,remote_b,4n,3n)))
        case _: 5n
def run(r: Request) -> Outcome:
  match r:
    case Request{+source,+operation,+locked,+offline,pv2,remote_b,+old,+cache}:
      +want=wanted(Request{source,operation,locked,offline,pv2,remote_b,old,cache})
      +needs_git=Nat.is_eq(source,1n)
      +available=Bool.and(Nat.is_ne(want,0n),Bool.or(Bool.not(needs_git),Bool.or(cached(cache,want),Bool.not(offline))))
      +next_cache=Bool.pick(Cache,Bool.and(needs_git,Bool.and(available,Bool.not(cached(cache,want)))),retain(cache,want),cache)
      Bool.pick(Outcome,Bool.not(available),Outcome{101n,old,cache,0n,False{}},Bool.pick(Outcome,Bool.and(locked,Nat.is_ne(old,want)),Outcome{101n,old,next_cache,0n,False{}},Outcome{0n,want,next_cache,Bool.pick(Nat,Nat.is_eq(operation,0n),want,0n),Nat.is_ne(old,want)}))
def render(o: Outcome) -> String:
  match o:
    case Outcome{code,after,+cache,+metadata,changed}:
      match cache:
        case Cache{head,_,_}: Nat.show(code) ++ "/" ++ Nat.show(after) ++ "/" ++ Nat.show(head) ++ "/" ++ Nat.show(mask(cache)) ++ "/" ++ Nat.show(metadata) ++ "/" ++ Nat.show(package_key(metadata)) ++ "/" ++ Bool.pick(String,changed,"1","0")

law logical_git_key_is_not_revision:
  {package_key(3n) == package_key(4n) : Nat}
def logical_git_key_is_not_revision(): {==}
law patch_has_different_origin:
  {Nat.is_ne(package_key(3n),package_key(5n)) == True{} : Bool}
def patch_has_different_origin(): {==}
law null_source_is_not_same_path_origin:
  {Nat.is_ne(package_key(1n),package_key(5n)) == True{} : Bool}
def null_source_is_not_same_path_origin(): {==}
law offline_path_creates_lock:
  {render(run(Request{0n,1n,False{},True{},False{},False{},0n,Cache{0n,False{},False{}}})) == "0/1/0/0/0/0/1" : String}
def offline_path_creates_lock(): {==}
law frozen_missing_lock_refuses:
  {render(run(Request{0n,0n,True{},True{},False{},False{},0n,Cache{0n,False{},False{}}})) == "101/0/0/0/0/0/0" : String}
def frozen_missing_lock_refuses(): {==}
law semantic_same_lock_keeps_selection:
  {render(run(Request{0n,0n,True{},True{},False{},False{},1n,Cache{0n,False{},False{}}})) == "0/1/0/0/1/1/0" : String}
def semantic_same_lock_keeps_selection(): {==}
law locked_changed_path_refuses:
  {render(run(Request{0n,0n,True{},True{},True{},False{},1n,Cache{0n,False{},False{}}})) == "101/1/0/0/0/0/0" : String}
def locked_changed_path_refuses(): {==}
law cold_offline_git_refuses:
  {render(run(Request{1n,0n,False{},True{},False{},False{},0n,Cache{0n,False{},False{}}})) == "101/0/0/0/0/0/0" : String}
def cold_offline_git_refuses(): {==}
law refusal_keeps_acquired_cache:
  {render(run(Request{1n,0n,True{},False{},False{},False{},0n,Cache{0n,False{},False{}}})) == "101/0/1/1/0/0/0" : String}
def refusal_keeps_acquired_cache(): {==}
law frozen_keeps_old_git_revision:
  {render(run(Request{1n,0n,True{},True{},False{},True{},3n,Cache{1n,True{},False{}}})) == "0/3/1/1/3/3/0" : String}
def frozen_keeps_old_git_revision(): {==}
law offline_update_uses_cached_head:
  {render(run(Request{1n,2n,False{},True{},False{},True{},3n,Cache{1n,True{},False{}}})) == "0/3/1/1/0/0/0" : String}
def offline_update_uses_cached_head(): {==}
law local_fetch_changes_precise_revision:
  {render(run(Request{1n,2n,False{},False{},False{},True{},3n,Cache{1n,True{},False{}}})) == "0/4/2/3/0/0/1" : String}
def local_fetch_changes_precise_revision(): {==}
law locked_patch_refuses_switch:
  {render(run(Request{2n,0n,True{},True{},False{},True{},4n,Cache{2n,True{},True{}}})) == "101/4/2/3/0/0/0" : String}
def locked_patch_refuses_switch(): {==}
law offline_patch_changes_origin:
  {render(run(Request{2n,0n,False{},True{},False{},True{},4n,Cache{2n,True{},True{}}})) == "0/5/2/3/5/4/1" : String}
def offline_patch_changes_origin(): {==}
