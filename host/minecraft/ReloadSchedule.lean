namespace Host.Minecraft.ReloadSchedule
/-- Selected future states:0 pending,1 success,2 failure,3 no returned future. -/
def arrived (barrier0 : Bool) (p0 p1 : Nat) : Bool := barrier0 && p0 == 1 && p1 == 1
def first (barrier0 fail0 : Bool) (initial p0 p1 : Nat) : Nat :=
  if p0 == 2 then 2 else if p0 == 0 then 0
  else if !barrier0 then (if fail0 then 2 else 1)
  else if !arrived barrier0 p0 p1 || initial == 0 then 0
  else if initial == 2 then 2 else if fail0 then 2 else 1
def second (barrier0 : Bool) (p0 p1 state0 : Nat) : Nat :=
  if p1 == 2 then 2 else if p1 == 0 then 0
  else if !arrived barrier0 p0 p1 || state0 == 0 then 0
  else if state0 == 2 then 2 else 1
def summary (a b : Nat) : Nat :=
  if a == 2 || b == 2 then 2 else if a == 1 && b == 1 then 1 else 0
def sharedCalls (count : Nat) (hasShared : Bool) : Nat :=
  if count == 0 then 0 else if hasShared then 2 else 0
/-- [factory-threw,listener0,listener1,overall,effect0,effect1,sharedCalls,invocations].
    Two authored listeners only;listener1 obeys the barrier and never fails apply.
    Direct executors,one completion per gate,and selected failure points only. -/
def evaluate (count : Nat) (hasShared sharedFailure : Bool) (initial p0 p1 : Nat)
    (barrier0 fail0 : Bool) : List Nat :=
  if count == 0 then [0,3,3,1,0,0,0,0]
  else if hasShared && sharedFailure then [1,3,3,3,0,0,2,0]
  else
    let a := first barrier0 fail0 initial p0 p1
    let b := second barrier0 p0 p1 a
    let effect0 := p0 == 1 && (!barrier0 || (arrived barrier0 p0 p1 && initial == 1))
    [0,a,b,summary a b,if effect0 then 1 else 0,if b == 1 then 1 else 0,sharedCalls count hasShared,2]

theorem empty_does_not_join_initial (h f b a : Bool) (initial p0 p1 : Nat) :
    evaluate 0 h f initial p0 p1 b a = [0,3,3,1,0,0,0,0] := rfl
theorem old_interface_has_no_shared_calls (count : Nat) : sharedCalls count false = 0 := by
  simp [sharedCalls]
theorem newer_two_listener_shared_calls : sharedCalls 2 true = 2 := rfl
theorem bypass_ignores_initial (i j p1 : Nat) (fail : Bool) :
    first false fail i 1 p1 = first false fail j 1 p1 := by simp [first]
theorem compliant_requires_second_preparation (p1 : Nat) (h : p1 ≠ 1) (i : Nat) (f : Bool) :
    first true f i 1 p1 = 0 := by simp [first,arrived,h]
theorem pending_initial_blocks_compliant_apply :
    evaluate 2 false false 0 1 1 true false = [0,0,0,0,0,0,0,2] := by decide
theorem ordered_completion :
    evaluate 2 false false 1 1 1 true false = [0,1,1,1,1,1,0,2] := by decide
theorem preparation_failure_not_peer_join :
    evaluate 2 false false 1 2 0 true false = [0,2,0,2,0,0,0,2] := by decide
theorem application_failure_not_rollback :
    evaluate 2 false false 1 1 1 true true = [0,2,2,2,1,0,0,2] := by decide
theorem initial_failure_before_barrier_stays_pending :
    evaluate 2 false false 2 1 0 true false = [0,0,0,0,0,0,0,2] := by decide
theorem initial_failure_after_barrier_propagates :
    evaluate 2 false false 2 1 1 true false = [0,2,2,2,0,0,0,2] := by decide
theorem bypass_effect_without_initial_completion :
    evaluate 2 false false 0 1 0 false false = [0,1,0,0,1,0,0,2] := by decide
theorem bypass_leaves_peer_pending_after_initial :
    evaluate 2 false false 1 1 1 false false = [0,1,0,0,1,0,0,2] := by decide
theorem shared_failure_precedes_listener_invocations (i p0 p1 : Nat) (b f : Bool) :
    evaluate 2 true true i p0 p1 b f = [1,3,3,3,0,0,2,0] := rfl
end Host.Minecraft.ReloadSchedule
