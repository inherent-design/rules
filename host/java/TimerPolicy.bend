import Base

# Admission state only: no queue,clock,running callback or worker retirement.
type TimerState is Data:
  State{timers: List<&2,Nat>,tasks: List<&2,Nat>}
type TimerReply is Data:
  Reply{state: TimerState,error: Nat,value: List<&2,Bool>}
def timer_initial() -> TimerState:
  State{[0n,0n],[0n,0n,0n,0n,0n,0n]}
def at(values: List<&2,Nat>,+index: Nat) -> Nat:
  match values:
    case Nil{}: 0n
    case head <> tail: Bool.pick(Nat,Nat.is_eq(index,0n),head,at(tail,Nat.sub(index,1n)))
def put(values: List<&2,Nat>,+index: Nat,+value: Nat) -> List<&2,Nat>:
  match values:
    case Nil{}: []
    case +head <> +tail: Bool.pick(List<&2,Nat>,Nat.is_eq(index,0n),value <> tail,head <> put(tail,Nat.sub(index,1n),value))
def timer_step(state: TimerState,+operation: Nat,+timer: Nat,+task: Nat,valid: Bool) -> TimerReply:
  match state:
    case State{+timers,+tasks}:
      admitted=Bool.pick(TimerReply,Bool.or(Nat.is_eq(at(timers,timer),1n),Bool.not(Nat.is_eq(at(tasks,task),0n))),Reply{State{timers,tasks},1n,[]},Reply{State{timers,put(tasks,task,1n)},0n,[]})
      scheduled=Bool.pick(TimerReply,valid,admitted,Reply{State{timers,tasks},2n,[]})
      other=Bool.pick(TimerReply,Nat.is_eq(operation,1n),Reply{State{timers,put(tasks,task,2n)},0n,[Nat.is_eq(at(tasks,task),1n)]},scheduled)
      Bool.pick(TimerReply,Nat.is_eq(operation,2n),Reply{State{put(timers,timer,1n),tasks},0n,[]},other)
def state(reply: TimerReply) -> TimerState:
  match reply:
    case Reply{state,error,value}: state
def error(reply: TimerReply) -> Nat:
  match reply:
    case Reply{state,error,value}: error
def value(reply: TimerReply) -> List<&2,Bool>:
  match reply:
    case Reply{state,error,value}: value

law fresh_cancel_false:
  {value(timer_step(timer_initial(),1n,0n,0n,True{})) == [False{}] : List<&2,Bool>}
def fresh_cancel_false():
  {==}
law false_cancel_changes_state:
  {state(timer_step(timer_initial(),1n,0n,0n,True{})) == State{[0n,0n],[2n,0n,0n,0n,0n,0n]} : TimerState}
def false_cancel_changes_state():
  {==}
law canceled_task_refuses:
  {error(timer_step(state(timer_step(timer_initial(),1n,0n,0n,True{})),0n,0n,0n,True{})) == 1n : Nat}
def canceled_task_refuses():
  {==}
law scheduled_cancel_true:
  {value(timer_step(state(timer_step(timer_initial(),0n,0n,0n,True{})),1n,0n,0n,True{})) == [True{}] : List<&2,Bool>}
def scheduled_cancel_true():
  {==}
law repeated_cancel_false:
  {value(timer_step(state(timer_step(timer_initial(),1n,0n,0n,True{})),1n,0n,0n,True{})) == [False{}] : List<&2,Bool>}
def repeated_cancel_false():
  {==}
law bad_argument_keeps_initial:
  {state(timer_step(timer_initial(),0n,0n,0n,False{})) == timer_initial() : TimerState}
def bad_argument_keeps_initial():
  {==}
law timer_closed_refuses:
  {error(timer_step(state(timer_step(timer_initial(),2n,0n,0n,True{})),0n,0n,1n,True{})) == 1n : Nat}
def timer_closed_refuses():
  {==}
law other_timer_open:
  {error(timer_step(state(timer_step(timer_initial(),2n,0n,0n,True{})),0n,1n,1n,True{})) == 0n : Nat}
def other_timer_open():
  {==}
law argument_guard_first_source_example:
  {error(timer_step(State{[1n,0n],[0n,0n,0n,0n,0n,0n]},0n,0n,0n,False{})) == 2n : Nat}
def argument_guard_first_source_example():
  {==}
