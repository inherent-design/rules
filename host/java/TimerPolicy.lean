import Std

namespace Host.Java.TimerPolicy

/-- Two owned timer objects, six task objects. 0=open timer / fresh task,
    1=closed timer / scheduled task, 2=canceled task. This is admission state,
    not a callback, queue-root, clock, scheduler, or worker-retirement model. -/
structure State where
  timers : List Nat
  tasks : List Nat
  deriving BEq, DecidableEq, Repr

def initial : State := ⟨[0, 0], [0, 0, 0, 0, 0, 0]⟩

structure Reply where
  error : Nat
  value : Option Bool
  deriving BEq, DecidableEq, Repr

/-- Schedule=0, task cancel=1, timer cancel=2. Error1 is the measured
    IllegalStateException class, error2 is IllegalArgumentException. -/
def step (s : State) (operation timer task : Nat) (validArguments : Bool) : State × Reply :=
  if operation == 2 then ({ s with timers := s.timers.set timer 1 }, ⟨0, none⟩)
  else if operation == 1 then
    ({ s with tasks := s.tasks.set task 2 }, ⟨0, some (s.tasks[task]! == 1)⟩)
  else if !validArguments then (s, ⟨2, none⟩)
  else if s.timers[timer]! == 1 || s.tasks[task]! != 0 then (s, ⟨1, none⟩)
  else ({ s with tasks := s.tasks.set task 1 }, ⟨0, none⟩)

theorem fresh_cancel_returns_false : (step initial 1 0 0 true).2.value = some false := by decide
theorem fresh_cancel_changes_admission : (step initial 1 0 0 true).1.tasks[0]! = 2 := by decide
theorem canceled_fresh_task_refuses_schedule :
    (step (step initial 1 0 0 true).1 0 0 0 true).2.error = 1 := by decide
theorem fresh_schedule_succeeds : (step initial 0 0 0 true).2.error = 0 := by decide
theorem scheduled_task_cannot_schedule_again :
    (step (step initial 0 0 0 true).1 0 0 0 true).2.error = 1 := by decide
theorem scheduled_cancel_returns_true :
    (step (step initial 0 0 0 true).1 1 0 0 true).2.value = some true := by decide
theorem repeated_cancel_returns_false :
    (step (step initial 1 0 0 true).1 1 0 0 true).2.value = some false := by decide
theorem invalid_schedule_preserves_state (s : State) (timer task : Nat) :
    (step s 0 timer task false).1 = s := rfl
theorem canceled_timer_refuses_new_task :
    (step (step initial 2 0 0 true).1 0 0 1 true).2.error = 1 := by decide
theorem other_timer_can_admit_new_task :
    (step (step initial 2 0 0 true).1 0 1 1 true).2.error = 0 := by decide
theorem timer_cancel_keeps_task_state (s : State) (timer : Nat) :
    (step s 2 timer 0 true).1.tasks = s.tasks := rfl
theorem timer_cancel_repeat_example :
    (step (step initial 2 0 0 true).1 2 0 0 true).1 = (step initial 2 0 0 true).1 := by decide

-- Source/model-only order and stale-task-state examples, not native extra cases.
theorem invalid_arguments_precede_closed_timer :
    (step (step initial 2 0 0 true).1 0 0 0 false).2.error = 2 := by decide
theorem canceled_timer_does_not_make_task_cancel_false :
    (step (step (step initial 0 0 0 true).1 2 0 0 true).1 1 0 0 true).2.value = some true := by decide

end Host.Java.TimerPolicy
