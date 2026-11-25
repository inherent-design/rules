import Base

# Case-local identity labels and non-reentrant authored callback outcomes.
type RCValue is Data:
  Absent{}
  CachedText{identity: Nat}
type RCProjection is Data:
  Returned{value: RCValue}
  Failed{}
type RCCell is Data:
  Cell{kind: Nat,value: RCValue}
type RCEntry is Data:
  Entry{identity: Nat,cells: List<&2,RCCell>}
type RCCallback is Data:
  Callback{event: Nat,failures: Nat}
type RCState is Data:
  State{capacity: Nat,entries: List<&2,RCEntry>,callbacks: List<&2,RCCallback>,events: List<&2,Nat>}
type RCFound is Data:
  Missing{}
  Found{value: RCValue}
type RCStep is Data:
  Step{state: RCState,error: Nat,value: RCFound}
type RCStart is Data:
  CreateRefused{}
  Created{state: RCState}
type RCCallbackRun is Data:
  Callbacks{callbacks: List<&2,RCCallback>,events: List<&2,Nat>,failed: Bool}

def rc_create(+capacity: Nat) -> RCStart:
  Bool.pick(RCStart,Nat.is_eq(capacity,0n),CreateRefused{},Created{State{capacity,Nil{},Nil{},Nil{}}})

def rc_cells(cells: List<&2,RCCell>,+kind: Nat) -> RCFound:
  match cells:
    case Nil{}: Missing{}
    case Con{Cell{current,value},tail}:
      Bool.pick(RCFound,Nat.is_eq(current,kind),Found{value},rc_cells(tail,kind))

def rc_lookup(entries: List<&2,RCEntry>,+identity: Nat,+kind: Nat) -> RCFound:
  match entries:
    case Nil{}: Missing{}
    case Con{Entry{current,cells},tail}:
      Bool.pick(RCFound,Nat.is_eq(current,identity),rc_cells(cells,kind),rc_lookup(tail,identity,kind))

def rc_has(entries: List<&2,RCEntry>,+identity: Nat) -> Bool:
  match entries:
    case Nil{}: False{}
    case Con{Entry{current,cells},tail}:
      Bool.or(Nat.is_eq(current,identity),rc_has(tail,identity))

def rc_drop(entries: List<&2,RCEntry>) -> List<&2,RCEntry>:
  match entries:
    case Nil{}: Nil{}
    case Con{head,tail}: tail

def rc_admit(state: RCState,+identity: Nat) -> RCState:
  match state:
    case State{+capacity,+entries,+callbacks,+events}:
      Bool.pick(RCState,rc_has(entries,identity),State{capacity,entries,callbacks,events},
        State{capacity,List.append(&2,RCEntry,Bool.pick(List<&2,RCEntry>,Nat.is_eq(List.length(&2,RCEntry,entries),capacity),rc_drop(entries),entries),[Entry{identity,Nil{}}]),callbacks,events})

def rc_remove_kind(cells: List<&2,RCCell>,+kind: Nat) -> List<&2,RCCell>:
  match cells:
    case Nil{}: Nil{}
    case Con{Cell{+current,value},+tail}:
      Bool.pick(List<&2,RCCell>,Nat.is_eq(current,kind),rc_remove_kind(tail,kind),Con{Cell{current,value},rc_remove_kind(tail,kind)})

def rc_store(entries: List<&2,RCEntry>,+identity: Nat,+kind: Nat,+value: RCValue) -> List<&2,RCEntry>:
  match entries:
    case Nil{}: Nil{}
    case Con{Entry{+current,+cells},tail}:
      Con{Entry{current,Bool.pick(List<&2,RCCell>,Nat.is_eq(current,identity),List.append(&2,RCCell,rc_remove_kind(cells,kind),[Cell{kind,value}]),cells)},rc_store(tail,identity,kind,value)}

def rc_project_called(state: RCState,identity: Nat,kind: Nat,event: Nat,projection: RCProjection) -> RCStep:
  match state:
    case State{capacity,+entries,callbacks,+events}:
      match projection:
        case Failed{}: Step{State{capacity,entries,callbacks,List.append(&2,Nat,events,[event])},1n,Missing{}}
        case Returned{+value}:
          Step{State{capacity,rc_store(entries,identity,kind,value),callbacks,List.append(&2,Nat,events,[event])},0n,Found{value}}

def rc_project_lookup(+state: RCState,+identity: Nat,kind: Nat,event: Nat,projection: RCProjection,found: RCFound) -> RCStep:
  match found:
    case Found{value}: Step{state,0n,Found{value}}
    case Missing{}: rc_project_called(rc_admit(state,identity),identity,kind,event,projection)

def rc_entries(state: RCState) -> List<&2,RCEntry>:
  match state:
    case State{capacity,entries,callbacks,events}: entries

def rc_project(+state: RCState,+identity: Nat,+kind: Nat,event: Nat,projection: RCProjection) -> RCStep:
  Bool.pick(RCStep,Nat.is_eq(identity,0n),Step{state,0n,Found{Absent{}}},
    rc_project_lookup(state,identity,kind,event,projection,rc_lookup(rc_entries(state),identity,kind)))

def rc_on_clear(state: RCState,callback: RCCallback) -> RCStep:
  match state:
    case State{capacity,entries,callbacks,events}:
      Step{State{capacity,entries,List.append(&2,RCCallback,callbacks,[callback]),events},0n,Missing{}}

def rc_callback_continue(+event: Nat,run: RCCallbackRun) -> RCCallbackRun:
  match run:
    case Callbacks{callbacks,events,failed}:
      Callbacks{Con{Callback{event,0n},callbacks},Con{event,events},failed}

def rc_invoke(callbacks: List<&2,RCCallback>) -> RCCallbackRun:
  match callbacks:
    case Nil{}: Callbacks{Nil{},Nil{},False{}}
    case Con{Callback{+event,+failures},+rest}:
      Bool.pick(RCCallbackRun,Nat.is_eq(failures,0n),rc_callback_continue(event,rc_invoke(rest)),
        Callbacks{Con{Callback{event,Nat.sub(failures,1n)},rest},[event],True{}})

def rc_cleared(capacity: Nat,previous: List<&2,Nat>,run: RCCallbackRun) -> RCStep:
  match run:
    case Callbacks{callbacks,events,failed}:
      Step{State{capacity,Nil{},callbacks,List.append(&2,Nat,previous,events)},Bool.pick(Nat,failed,2n,0n),Missing{}}

def rc_clear(state: RCState) -> RCStep:
  match state:
    case State{capacity,entries,callbacks,events}: rc_cleared(capacity,events,rc_invoke(callbacks))

law rc_zero_refuses:
  {rc_create(0n) == CreateRefused{} : RCStart}
def rc_zero_refuses():
  {==}
law rc_null_does_not_call:
  {rc_project(State{1n,Nil{},Nil{},Nil{}},0n,0n,9n,Failed{}) == Step{State{1n,Nil{},Nil{},Nil{}},0n,Found{Absent{}}} : RCStep}
def rc_null_does_not_call():
  {==}
law rc_hit_ignores_new_projection:
  {rc_project(State{2n,[Entry{1n,[Cell{0n,CachedText{7n}}]}],Nil{},[1n]},1n,0n,9n,Failed{}) == Step{State{2n,[Entry{1n,[Cell{0n,CachedText{7n}}]}],Nil{},[1n]},0n,Found{CachedText{7n}}} : RCStep}
def rc_hit_ignores_new_projection():
  {==}
law rc_absent_is_a_hit:
  {rc_lookup([Entry{1n,[Cell{0n,Absent{}}]}],1n,0n) == Found{Absent{}} : RCFound}
def rc_absent_is_a_hit():
  {==}
law rc_distinct_identity_misses:
  {rc_lookup([Entry{1n,[Cell{0n,CachedText{7n}}]}],2n,0n) == Missing{} : RCFound}
def rc_distinct_identity_misses():
  {==}
law rc_distinct_kind_misses:
  {rc_lookup([Entry{1n,[Cell{0n,CachedText{7n}}]}],1n,1n) == Missing{} : RCFound}
def rc_distinct_kind_misses():
  {==}
law rc_fifo_evicts_first:
  {rc_admit(State{2n,[Entry{1n,Nil{}},Entry{2n,Nil{}}],Nil{},Nil{}},3n) == State{2n,[Entry{2n,Nil{}},Entry{3n,Nil{}}],Nil{},Nil{}} : RCState}
def rc_fifo_evicts_first():
  {==}
law rc_failed_projection_keeps_empty_entry:
  {rc_project(State{1n,Nil{},Nil{},Nil{}},1n,0n,9n,Failed{}) == Step{State{1n,[Entry{1n,Nil{}}],Nil{},[9n]},1n,Missing{}} : RCStep}
def rc_failed_projection_keeps_empty_entry():
  {==}
law rc_register_does_not_call:
  {rc_on_clear(State{1n,Nil{},Nil{},Nil{}},Callback{7n,0n}) == Step{State{1n,Nil{},[Callback{7n,0n}],Nil{}},0n,Missing{}} : RCStep}
def rc_register_does_not_call():
  {==}
law rc_failed_clear_already_emptied_entries:
  {rc_clear(State{1n,[Entry{1n,Nil{}}],[Callback{7n,1n},Callback{8n,0n}],Nil{}}) == Step{State{1n,Nil{},[Callback{7n,0n},Callback{8n,0n}],[7n]},2n,Missing{}} : RCStep}
def rc_failed_clear_already_emptied_entries():
  {==}
