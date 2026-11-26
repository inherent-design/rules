import Base

# Host codes: 0 unavailable, 1 local process, 2 local worker, 3 remote.
# Preference codes: 0 none, 1 local development, 2 remote development.
def preference(+local: Bool,+remote: Bool) -> Nat:
  Bool.pick(Nat,Bool.and(local,Bool.not(remote)),1n,Bool.pick(Nat,Bool.and(remote,Bool.not(local)),2n,0n))
def effective(+local: Bool,+local_kinds: List<&2,String>,+remote_kinds: List<&2,String>) -> List<&2,String>:
  Bool.pick(List<&2,String>,local,local_kinds,remote_kinds)
def host(+kind: String,+browser: Bool,+local: Bool,+remote: Bool,+remote_host: Bool,+worker: Bool) -> Nat:
  Bool.pick(Nat,browser,
    Bool.pick(Nat,String.eq(kind,"web"),Bool.pick(Nat,Bool.or(local,remote),2n,0n),Bool.pick(Nat,remote,3n,0n)),
    Bool.pick(Nat,String.eq(kind,"ui"),Bool.pick(Nat,local,1n,0n),
      Bool.pick(Nat,String.eq(kind,"workspace"),Bool.pick(Nat,remote,3n,Bool.pick(Nat,Bool.not(remote_host),1n,0n)),Bool.pick(Nat,Bool.and(local,worker),2n,0n))))
def tier(+kind: String,+browser: Bool,+pref: Nat,+target: Nat) -> Nat:
  match pref:
    case 0n: Bool.pick(Nat,Bool.and(browser,String.eq(kind,"ui")),2n,0n)
    case 1n: Bool.pick(Nat,Bool.and(browser,String.eq(kind,"ui")),2n,Bool.pick(Nat,Nat.is_eq(target,3n),1n,0n))
    case _: Bool.pick(Nat,Nat.is_eq(target,3n),0n,1n)
def first(+kinds: List<&2,String>,+browser: Bool,+local: Bool,+remote: Bool,+remote_host: Bool,+worker: Bool,+pref: Nat,+rank: Nat) -> Nat:
  match kinds:
    case Nil{}: 0n
    case Con{+kind,tail}:
      +value=host(kind,browser,local,remote,remote_host,worker)
      Bool.pick(Nat,Bool.and(Bool.not(Nat.is_eq(value,0n)),Nat.is_eq(tier(kind,browser,pref,value),rank)),value,first(tail,browser,local,remote,remote_host,worker,pref,rank))
def nonzero(+first_value: Nat,+fallback: Nat) -> Nat:
  Bool.pick(Nat,Nat.is_eq(first_value,0n),fallback,first_value)
def select(+kinds: List<&2,String>,+browser: Bool,+local: Bool,+remote: Bool,+remote_host: Bool,+worker: Bool,+pref: Nat) -> Nat:
  nonzero(first(kinds,browser,local,remote,remote_host,worker,pref,0n),nonzero(first(kinds,browser,local,remote,remote_host,worker,pref,1n),first(kinds,browser,local,remote,remote_host,worker,pref,2n)))

# Operations: 0 query, 1 install, 2 uninstall. Versions: absent0, fixture1/2/3.
def manage(+operation: Nat,+registered: Nat,+requested: Nat,+compatible: Bool) -> String:
  match operation:
    case 0n: "listed/0/" ++ Nat.show(registered)
    case 1n:
      Bool.pick(String,Bool.and(Nat.is_eq(registered,2n),Nat.is_eq(requested,1n)),"skipped/0/2",Bool.pick(String,compatible,"installed/0/" ++ Nat.show(requested),"refused/1/" ++ Nat.show(registered)))
    case _: Bool.pick(String,Nat.is_eq(registered,0n),"absent/1/0","removed/0/0")

law local_kinds_win:
  {effective(True{},["ui"],["workspace"]) == ["ui"] : List<&2,String>}
def local_kinds_win(): {==}
law both_development_no_preference:
  {preference(True{},True{}) == 0n : Nat}
def both_development_no_preference(): {==}
law local_workspace_process:
  {select(["workspace"],False{},True{},False{},False{},False{},0n) == 1n : Nat}
def local_workspace_process(): {==}
law local_install_not_remote_placement:
  {select(["workspace"],False{},True{},False{},True{},True{},0n) == 0n : Nat}
def local_install_not_remote_placement(): {==}
law browser_no_local_workspace_process:
  {select(["workspace"],True{},True{},False{},False{},True{},0n) == 0n : Nat}
def browser_no_local_workspace_process(): {==}
law worker_disabled:
  {select(["web"],False{},True{},False{},False{},False{},0n) == 0n : Nat}
def worker_disabled(): {==}
law worker_enabled:
  {select(["web"],False{},True{},False{},False{},True{},0n) == 2n : Nat}
def worker_enabled(): {==}
law browser_ui_reserve:
  {select(["ui","web"],True{},True{},True{},True{},True{},0n) == 2n : Nat}
def browser_ui_reserve(): {==}
law browser_remote_development_ui:
  {select(["ui","web"],True{},True{},True{},True{},True{},2n) == 3n : Nat}
def browser_remote_development_ui(): {==}
law engine_refusal_preserves_registration:
  {manage(1n,1n,3n,False{}) == "refused/1/1" : String}
def engine_refusal_preserves_registration(): {==}
law zero_exit_can_skip:
  {manage(1n,2n,1n,True{}) == "skipped/0/2" : String}
def zero_exit_can_skip(): {==}
law uninstall_membership:
  {manage(2n,2n,0n,True{}) == "removed/0/0" : String}
def uninstall_membership(): {==}
