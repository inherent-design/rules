import Base

type ChildAction is Data:
  NoChild{}
  Child{token: Nat, group: Nat, force: Bool}
type Callback is Data:
  Callback{token: Nat, group: Nat, child: ChildAction}
type Request is Data:
  Request{callback: Callback, force: Bool}
type State is Data:
  State{active: Bool, trace: List<&2, Nat>, pending: List<&2, Callback>}
type Timeline is Data:
  Timeline{before: State, first: State, second: State}

def token(callback: Callback) -> Nat:
  match callback:
    case Callback{token,_,_}: token
def group(callback: Callback) -> Nat:
  match callback:
    case Callback{_,group,_}: group
def insert(+callback: Callback,xs: List<&2, Callback>) -> List<&2, Callback>:
  match xs:
    case Nil{}: Con{callback,Nil{}}
    case Con{+head,+tail}:
      Bool.pick(List<&2, Callback>,Nat.is_lt(group(callback),group(head)),
        Con{callback,Con{head,tail}},Con{head,insert(callback,tail)})
def append(xs: List<&2, Nat>,value: Nat) -> List<&2, Nat>:
  match xs:
    case Nil{}: Con{value,Nil{}}
    case Con{head,tail}: Con{head,append(tail,value)}
def register_leaf(state: State,+event: Nat,+rank: Nat,force: Bool) -> State:
  match state:
    case State{+active,+trace,+pending}:
      Bool.pick(State,Bool.or(active,force),
        State{active,trace,insert(Callback{event,rank,NoChild{}},pending)},
        State{active,append(trace,event),pending})
def fire_child(state: State,child: ChildAction) -> State:
  match child:
    case NoChild{}: state
    case Child{event,rank,force}: register_leaf(state,event,rank,force)
def fire(state: State,callback: Callback) -> State:
  match state:
    case State{active,trace,pending}:
      match callback:
        case Callback{event,_,child}: fire_child(State{active,append(trace,event),pending},child)
def register(state: State,request: Request) -> State:
  match state:
    case State{+active,+trace,+pending}:
      match request:
        case Request{+callback,force}:
          Bool.pick(State,Bool.or(active,force),
            State{active,trace,insert(callback,pending)},fire(State{active,trace,pending},callback))
def register_all(requests: List<&2, Request>,state: State) -> State:
  match requests:
    case Nil{}: state
    case Con{head,tail}: register_all(tail,register(state,head))
def fire_all(callbacks: List<&2, Callback>,state: State) -> State:
  match callbacks:
    case Nil{}: state
    case Con{head,tail}: fire_all(tail,fire(state,head))
def clear_pending(state: State) -> State:
  match state:
    case State{active,trace,_}: State{active,trace,Nil{}}
def finish(+detached: Bool,state: State) -> State:
  match state:
    case State{_,trace,+pending}:
      +fired = fire_all(pending,State{False{},trace,Bool.pick(List<&2, Callback>,detached,Nil{},pending)})
      Bool.pick(State,detached,fired,clear_pending(fired))
def run(+detached: Bool,active: Bool,requests: List<&2, Request>) -> Timeline:
  +before = register_all(requests,State{active,Nil{},Nil{}})
  +first = finish(detached,before)
  Timeline{before,first,finish(detached,first)}

def insert_token(+value: Nat,xs: List<&2, Nat>) -> List<&2, Nat>:
  match xs:
    case Nil{}: Con{value,Nil{}}
    case Con{+head,+tail}:
      Bool.pick(List<&2, Nat>,Nat.is_lt(value,head),Con{value,Con{head,tail}},Con{head,insert_token(value,tail)})
def connected(callbacks: List<&2, Callback>) -> List<&2, Nat>:
  match callbacks:
    case Nil{}: Nil{}
    case Con{head,tail}: insert_token(token(head),connected(tail))
def count(callbacks: List<&2, Callback>) -> Nat:
  match callbacks:
    case Nil{}: 0n
    case Con{_,tail}: Nat.add(1n,count(tail))
def render_items(values: List<&2, Nat>) -> String:
  match values:
    case Nil{}: ""
    case Con{head,tail}:
      match tail:
        case Nil{}: Nat.show(head)
        case Con{x,xs}: Nat.show(head) ++ "," ++ render_items(Con{x,xs})
def render_list(values: List<&2, Nat>) -> String:
  "[" ++ render_items(values) ++ "]"
def render_state(state: State) -> String:
  match state:
    case State{_,trace,+pending}:
      "{\"trace\":" ++ render_list(trace) ++ ",\"connected\":" ++ render_list(connected(pending)) ++ ",\"pending\":" ++ Nat.show(count(pending)) ++ "}"
def render_timeline(timeline: Timeline) -> String:
  match timeline:
    case Timeline{before,first,second}:
      "{\"before\":" ++ render_state(before) ++ ",\"first\":" ++ render_state(first) ++ ",\"second\":" ++ render_state(second) ++ "}"
def render(detached: Bool,active: Bool,requests: List<&2, Request>) -> String:
  render_timeline(run(detached,active,requests))

def first_pending(timeline: Timeline) -> Nat:
  match timeline:
    case Timeline{_,first,_}:
      match first:
        case State{_,_,pending}: count(pending)
def final_trace(timeline: Timeline) -> List<&2, Nat>:
  match timeline:
    case Timeline{_,_,second}:
      match second:
        case State{_,trace,_}: trace
def same(left: List<&2, Nat>,right: List<&2, Nat>) -> Bool:
  match left:
    case Nil{}:
      match right:
        case Nil{}: True{}
        case Con{_,_}: False{}
    case Con{head,tail}:
      match right:
        case Nil{}: False{}
        case Con{r,rs}: Bool.and(Nat.is_eq(head,r),same(tail,rs))
def future(force: Bool) -> List<&2, Request>:
  Con{Request{Callback{1n,0n,Child{2n,2n,force}},True{}},Nil{}}
def one_shot() -> List<&2, Request>:
  Con{Request{Callback{1n,0n,NoChild{}},True{}},Nil{}}
def grouped() -> List<&2, Request>:
  last : List<&2, Request> = Con{Request{Callback{2n,1n,NoChild{}},True{}},Nil{}}
  middle : List<&2, Request> = Con{Request{Callback{1n,0n,NoChild{}},True{}},last}
  Con{Request{Callback{3n,2n,NoChild{}},True{}},middle}

def law_current_loses_future() -> Bool:
  Nat.is_eq(first_pending(run(False{},True{},future(True{}))),0n)
def law_current_never_fires_lost_child() -> Bool:
  same(final_trace(run(False{},True{},future(True{}))),Con{1n,Nil{}})
def law_detached_retains_future() -> Bool:
  Nat.is_eq(first_pending(run(True{},True{},future(True{}))),1n)
def law_detached_runs_child_next() -> Bool:
  same(final_trace(run(True{},True{},future(True{}))),Con{1n,Con{2n,Nil{}}})
def law_immediate_child_current() -> Bool:
  same(final_trace(run(False{},True{},future(False{}))),Con{1n,Con{2n,Nil{}}})
def law_immediate_child_detached() -> Bool:
  same(final_trace(run(True{},True{},future(False{}))),Con{1n,Con{2n,Nil{}}})
def law_one_shot() -> Bool:
  same(final_trace(run(False{},True{},one_shot())),Con{1n,Nil{}})
def law_group_order_current() -> Bool:
  same(final_trace(run(False{},True{},grouped())),Con{1n,Con{2n,Con{3n,Nil{}}}})
def law_group_order_detached() -> Bool:
  same(final_trace(run(True{},True{},grouped())),Con{1n,Con{2n,Con{3n,Nil{}}}})
