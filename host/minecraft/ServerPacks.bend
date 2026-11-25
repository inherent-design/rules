import Base

# Serial single-record branch projections; not callback/network/filesystem execution.
def sp_first(+old: Nat,next: Nat) -> Nat:
  Bool.pick(Nat,Nat.is_eq(old,0n),next,old)
def sp_wanted(accepted: Nat,download: Nat,reason: Nat) -> Bool:
  Bool.and(Nat.is_eq(accepted,1n),Bool.and(Nat.is_eq(download,2n),Nat.is_eq(reason,0n)))
def sp_waiting(present: Nat,accepted: Nat,download: Nat,reason: Nat) -> Bool:
  Bool.and(Nat.is_eq(present,1n),Bool.and(Nat.is_eq(accepted,1n),Bool.and(Bool.not(Nat.is_eq(download,2n)),Nat.is_eq(reason,0n))))
def sp_reload(+present: Nat,+accepted: Nat,+download: Nat,+activation: Nat,+reason: Nat) -> Nat:
  +wanted=sp_wanted(accepted,download,reason)
  blocked=Bool.or(Nat.is_eq(present,0n),Bool.or(sp_waiting(present,accepted,download,reason),Nat.is_eq(activation,1n)))
  Bool.pick(Nat,blocked,0n,Bool.pick(Nat,Bool.and(wanted,Nat.is_eq(activation,0n)),1n,Bool.pick(Nat,Bool.and(Bool.not(wanted),Nat.is_eq(activation,2n)),2n,0n)))
def sp_cleanup(present: Nat,activation: Nat,reason: Nat) -> Bool:
  Bool.and(Nat.is_eq(present,1n),Bool.and(Nat.is_eq(activation,0n),Bool.not(Nat.is_eq(reason,0n))))
def sp_bit(value: Bool) -> Nat:
  Bool.pick(Nat,value,1n,0n)
def sp_out(a: Nat,b: Nat,c: Nat,d: Nat) -> String:
  Nat.show(a) ++ ":" ++ Nat.show(b) ++ ":" ++ Nat.show(c) ++ ":" ++ Nat.show(d) ++ "\n"
def sp_tick(+present: Nat,+accepted: Nat,+download: Nat,+activation: Nat,+reason: Nat) -> String:
  +reload=sp_reload(present,accepted,download,activation,reason)
  +next=Bool.pick(Nat,Bool.not(Nat.is_eq(reload,0n)),1n,activation)
  +gone=sp_cleanup(present,next,reason)
  sp_out(sp_bit(Bool.and(sp_waiting(present,accepted,download,reason),Nat.is_eq(download,0n))),sp_bit(Bool.not(Nat.is_eq(reload,0n))),Bool.pick(Nat,Bool.or(gone,Nat.is_eq(present,0n)),0n,next),sp_bit(gone))
def sp_branch(op: Nat,+prompt: Nat,+present: Nat,+accepted: Nat,+download: Nat,+activation: Nat,+reason: Nat,+load: Nat) -> String:
  match op:
    case 0n: Bool.pick(String,Nat.is_eq(prompt,2n),sp_out(1n,0n,0n,0n),sp_out(0n,sp_bit(Nat.is_eq(prompt,1n)),0n,1n))
    case 1n: Bool.pick(String,Nat.is_eq(prompt,2n),sp_out(1n,0n,0n,0n),sp_out(0n,sp_bit(Nat.is_eq(prompt,1n)),2n,1n))
    case 2n:
      +grant=Bool.and(Nat.is_eq(present,1n),Bool.and(Nat.is_eq(accepted,0n),Nat.is_eq(reason,0n)))
      sp_out(1n,Bool.pick(Nat,grant,1n,accepted),sp_bit(grant),1n)
    case 3n: sp_out(2n,accepted,Bool.pick(Nat,Bool.and(Nat.is_eq(present,1n),Nat.is_eq(accepted,0n)),sp_first(reason,1n),reason),present)
    case 4n: sp_out(0n,accepted,reason,0n)
    case 5n: sp_tick(present,accepted,download,activation,reason)
    case 6n: sp_out(Bool.pick(Nat,Nat.is_eq(present,1n),2n,0n),sp_bit(Bool.and(Nat.is_eq(present,1n),Nat.is_eq(reason,0n))),1n,0n)
    case 7n: sp_out(Bool.pick(Nat,Bool.and(Nat.is_eq(present,1n),Bool.not(Nat.is_eq(activation,2n))),sp_first(reason,2n),reason),1n,0n,0n)
    case 8n: sp_out(Bool.pick(Nat,Nat.is_eq(present,0n),0n,Bool.pick(Nat,Nat.is_eq(load,1n),2n,Bool.pick(Nat,Nat.is_eq(activation,1n),0n,activation))),sp_bit(Bool.and(Nat.is_eq(load,1n),Bool.and(Nat.is_eq(present,1n),Nat.is_eq(reason,0n)))),1n,0n)
    case 9n: sp_out(Bool.pick(Nat,Nat.is_eq(activation,1n),0n,activation),Bool.pick(Nat,Nat.is_eq(present,0n),0n,Bool.pick(Nat,Nat.is_eq(activation,1n),sp_first(reason,3n),Bool.pick(Nat,Nat.is_eq(activation,0n),sp_first(reason,4n),reason))),1n,0n)
    case 10n: sp_out(Bool.pick(Nat,Nat.is_eq(activation,1n),0n,activation),reason,0n,0n)
    case 11n: sp_out(Bool.pick(Nat,Nat.is_eq(present,1n),sp_first(reason,5n),0n),sp_bit(Bool.and(Nat.is_eq(present,1n),Nat.is_eq(reason,0n))),activation,0n)
    case 12n: sp_out(Bool.pick(Nat,Nat.is_eq(present,1n),sp_first(reason,5n),0n),1n,activation,0n)
    case _: "UNSELECTED\n"

type SPRow is Data:
  SPRow{op: Nat,prompt: Nat,present: Nat,accepted: Nat,download: Nat,activation: Nat,reason: Nat,load: Nat}
def sp_row(row: SPRow) -> String:
  match row:
    case SPRow{op,prompt,present,accepted,download,activation,reason,load}: sp_branch(op,prompt,present,accepted,download,activation,reason,load)
def sp_trace(rows: List<&2,SPRow>) -> String:
  match rows:
    case Nil{}: ""
    case Con{row,rest}: sp_row(row) ++ sp_trace(rest)

law sp_local_is_not_consent:
  {sp_branch(1n,0n,0n,0n,0n,0n,0n,0n) == "0:0:2:1\n" : String}
def sp_local_is_not_consent():
  {==}
law sp_declined_admission:
  {sp_branch(0n,2n,0n,0n,0n,0n,0n,0n) == "1:0:0:0\n" : String}
def sp_declined_admission():
  {==}
law sp_preserve_removal:
  {sp_first(5n,3n) == 5n : Nat}
def sp_preserve_removal():
  {==}
law sp_pending_keeps_removed:
  {sp_cleanup(1n,1n,5n) == False{} : Bool}
def sp_pending_keeps_removed():
  {==}
law sp_active_keeps_removed:
  {sp_cleanup(1n,2n,5n) == False{} : Bool}
def sp_active_keeps_removed():
  {==}
law sp_inactive_can_remove:
  {sp_cleanup(1n,0n,5n) == True{} : Bool}
def sp_inactive_can_remove():
  {==}
law sp_active_unload:
  {sp_reload(1n,1n,2n,2n,5n) == 2n : Nat}
def sp_active_unload():
  {==}
law sp_reject_keeps_acceptance:
  {sp_branch(3n,1n,1n,1n,2n,0n,0n,0n) == "2:1:0:1\n" : String}
def sp_reject_keeps_acceptance():
  {==}
law sp_failure_marks:
  {sp_branch(9n,1n,1n,1n,2n,1n,0n,1n) == "0:3:1:0\n" : String}
def sp_failure_marks():
  {==}
law sp_recovery_failure_preserves:
  {sp_branch(10n,1n,1n,1n,2n,1n,0n,1n) == "0:0:0:0\n" : String}
def sp_recovery_failure_preserves():
  {==}
law sp_late_download_silent:
  {sp_branch(6n,1n,0n,0n,0n,0n,0n,0n) == "0:0:1:0\n" : String}
def sp_late_download_silent():
  {==}
law sp_removed_success_not_reported:
  {sp_branch(8n,1n,1n,1n,2n,1n,5n,1n) == "2:0:1:0\n" : String}
def sp_removed_success_not_reported():
  {==}
