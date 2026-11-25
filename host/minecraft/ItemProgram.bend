import Base
import ../java/FloatOrder.bend as F

type IPFallback is Data:
  Absent{}
  ExplicitNull{}
  Child{index: Nat}
type IPCase is Data:
  Case{fields: Bool,child: Nat,keys: List<&2,Nat>}
type IPRangeEntry is Data:
  Entry{threshold: Nat,fields: Bool,body: Nat,child: Nat}
type IPInstruction is Data:
  Empty{fields: Bool}
  Leaf{fields: Bool,present: Bool,reference: Nat,tints: Nat}
  Composite{fields: Bool,children: List<&2,Nat>,empty_run: Nat}
  Condition{fields: Bool,yes: Nat,no: Nat}
  Select{fields: Bool,cases: List<&2,IPCase>,fallback: IPFallback}
  Range{fields: Bool,entries: List<&2,IPRangeEntry>,flip: Bool,fallback: IPFallback}
  Unsupported{}
type IPState is Data:
  State{error: Nat,used: Nat,dependencies: List<&2,Nat>,reverse_events: List<&2,Nat>}
type IPSeen is Data:
  Seen{threshold: Nat,body: Nat}
type IPFound is Data:
  Found{present: Bool,value: Nat}
type IPScope is Data:
  Scope{id: Nat,keys: List<&2,Nat>,alternatives: Nat,thresholds: List<&2,IPSeen>}
type IPTask is Data:
  Visit{index: Nat,depth: Nat}
  Cases{rows: List<&2,IPCase>,depth: Nat,scope: Nat,fallback: IPFallback}
  BeginKeys{keys: List<&2,Nat>,scope: Nat}
  Keys{keys: List<&2,Nat>,scope: Nat}
  Ranges{rows: List<&2,IPRangeEntry>,depth: Nat,scope: Nat,fallback: IPFallback}
  Fallback{fallback: IPFallback,depth: Nat}
  FinishRoot{overflow: Bool}
type IPMachine is Data:
  Machine{tasks: List<&2,IPTask>,state: IPState,scopes: List<&2,IPScope>}

def ip_contains(xs: List<&2,Nat>,+value: Nat) -> Bool:
  match xs:
    case Nil{}: False{}
    case Con{head,tail}: Bool.or(Nat.is_eq(head,value),ip_contains(tail,value))
def ip_error(state: IPState) -> Nat:
  match state:
    case State{error,used,dependencies,events}: error
def ip_used(state: IPState) -> Nat:
  match state:
    case State{error,used,dependencies,events}: used
def ip_fail(state: IPState,code: Nat) -> IPState:
  match state:
    case State{error,used,dependencies,events}: State{code,used,dependencies,events}
def ip_increment(state: IPState) -> IPState:
  match state:
    case State{error,used,dependencies,events}: State{error,Nat.add(used,1n),dependencies,events}
def ip_emit(state: IPState,event: Nat) -> IPState:
  match state:
    case State{error,used,dependencies,events}: State{error,used,dependencies,Con{event,events}}
def ip_reference(state: IPState,+value: Nat) -> IPState:
  match state:
    case State{+error,+used,+dependencies,+events}:
      Bool.pick(IPState,ip_contains(dependencies,value),State{error,used,dependencies,events},State{error,used,Con{value,dependencies},events})
def ip_repeated_events(count: Nat,+value: Nat,state: IPState) -> IPState:
  match count:
    case 0n: state
    case 1n+remaining: ip_repeated_events(remaining,value,ip_emit(state,value))
def ip_empty_children(state: IPState,depth: Nat,+count: Nat) -> IPState:
  match state:
    case State{+error,+used,+dependencies,+events}:
      Bool.pick(IPState,Nat.is_eq(count,0n),State{error,used,dependencies,events},
        Bool.pick(IPState,Nat.is_gt(depth,32n),State{13n,used,dependencies,events},
          Bool.pick(IPState,Nat.is_gt(Nat.add(used,count),4096n),State{13n,4097n,dependencies,events},State{error,Nat.add(used,count),dependencies,events})))
def ip_get(program: List<&2,IPInstruction>,+index: Nat) -> IPInstruction:
  match program:
    case Nil{}: Unsupported{}
    case Con{head,tail}: Bool.pick(IPInstruction,Nat.is_eq(index,0n),head,ip_get(tail,Nat.sub(index,1n)))
def ip_visits(children: List<&2,Nat>,+depth: Nat,tail: List<&2,IPTask>) -> List<&2,IPTask>:
  match children:
    case Nil{}: tail
    case Con{head,rest}: Con{Visit{head,depth},ip_visits(rest,depth,tail)}
def ip_seen(rows: List<&2,IPSeen>,+key: Nat) -> IPFound:
  match rows:
    case Nil{}: Found{False{},0n}
    case Con{Seen{threshold,body},tail}: Bool.pick(IPFound,Nat.is_eq(key,threshold),Found{True{},body},ip_seen(tail,key))
def ip_scope(scopes: List<&2,IPScope>,+wanted: Nat) -> IPScope:
  match scopes:
    case Nil{}: Scope{0n,Nil{},0n,Nil{}}
    case Con{Scope{+id,keys,alternatives,thresholds},tail}:
      Bool.pick(IPScope,Nat.is_eq(id,wanted),Scope{id,keys,alternatives,thresholds},ip_scope(tail,wanted))
def ip_scope_id(scope: IPScope) -> Nat:
  match scope:
    case Scope{id,keys,alternatives,thresholds}: id
def ip_scope_seen(scope: IPScope,key: Nat) -> IPFound:
  match scope:
    case Scope{id,keys,alternatives,thresholds}: ip_seen(thresholds,key)
def ip_replace(scopes: List<&2,IPScope>,+scope: IPScope) -> List<&2,IPScope>:
  match scopes:
    case Nil{}: Nil{}
    case Con{+head,+tail}:
      Bool.pick(List<&2,IPScope>,Nat.is_eq(ip_scope_id(head),ip_scope_id(scope)),Con{scope,tail},Con{head,ip_replace(tail,scope)})

def ip_leaf(fields: Bool,present: Bool,reference: Nat,+tints: Nat,+tail: List<&2,IPTask>,+state: IPState,+scopes: List<&2,IPScope>) -> IPMachine:
  +next = ip_reference(state,reference)
  Machine{tail,Bool.pick(IPState,fields,Bool.pick(IPState,present,
    Bool.pick(IPState,Nat.is_gt(tints,32n),ip_fail(next,5n),ip_repeated_events(tints,1n,next)),ip_fail(state,4n)),ip_fail(state,3n)),scopes}
def ip_start_select(fields: Bool,+cases: List<&2,IPCase>,fallback: IPFallback,+depth: Nat,+tail: List<&2,IPTask>,+state: IPState,+scopes: List<&2,IPScope>) -> IPMachine:
  +next = ip_emit(state,3n)
  +id = ip_used(next)
  Bool.pick(IPMachine,fields,
    Bool.pick(IPMachine,Nat.is_gt(List.length(&2,IPCase,cases),512n),Machine{tail,ip_fail(next,6n),scopes},
      Machine{Con{Cases{cases,Nat.add(depth,1n),id,fallback},tail},next,Con{Scope{id,Nil{},0n,Nil{}},scopes}}),Machine{tail,ip_fail(state,3n),scopes})
def ip_start_range(fields: Bool,+entries: List<&2,IPRangeEntry>,fallback: IPFallback,+depth: Nat,+tail: List<&2,IPTask>,+state: IPState,+scopes: List<&2,IPScope>) -> IPMachine:
  +id = ip_used(state)
  Bool.pick(IPMachine,fields,
    Bool.pick(IPMachine,Nat.is_gt(List.length(&2,IPRangeEntry,entries),512n),Machine{tail,ip_fail(state,10n),scopes},
      Machine{Con{Ranges{entries,Nat.add(depth,1n),id,fallback},tail},state,Con{Scope{id,Nil{},0n,Nil{}},scopes}}),Machine{tail,ip_fail(state,3n),scopes})
def ip_visit_node(instruction: IPInstruction,+depth: Nat,+tail: List<&2,IPTask>,+state: IPState,+scopes: List<&2,IPScope>) -> IPMachine:
  match instruction:
    case Unsupported{}: Machine{tail,ip_fail(state,2n),scopes}
    case Empty{fields}: Machine{tail,Bool.pick(IPState,fields,state,ip_fail(state,3n)),scopes}
    case Leaf{fields,present,reference,tints}: ip_leaf(fields,present,reference,tints,tail,state,scopes)
    case Composite{fields,children,+empty_run}:
      Bool.pick(IPMachine,fields,
        Bool.pick(IPMachine,Nat.is_eq(empty_run,0n),Machine{ip_visits(children,Nat.add(depth,1n),tail),state,scopes},Machine{tail,ip_empty_children(state,Nat.add(depth,1n),empty_run),scopes}),Machine{tail,ip_fail(state,3n),scopes})
    case Condition{fields,yes,no}:
      Bool.pick(IPMachine,fields,Machine{Con{Visit{yes,Nat.add(depth,1n)},Con{Visit{no,Nat.add(depth,1n)},tail}},ip_emit(state,2n),scopes},Machine{tail,ip_fail(state,3n),scopes})
    case Select{fields,cases,fallback}: ip_start_select(fields,cases,fallback,depth,tail,state,scopes)
    case Range{fields,entries,flip,fallback}: ip_start_range(fields,entries,fallback,depth,tail,state,scopes)
def ip_visit(program: List<&2,IPInstruction>,index: Nat,+depth: Nat,+tail: List<&2,IPTask>,+state: IPState,+scopes: List<&2,IPScope>) -> IPMachine:
  +next = ip_increment(state)
  Bool.pick(IPMachine,Nat.is_gt(depth,32n),Machine{tail,ip_fail(state,13n),scopes},
    Bool.pick(IPMachine,Nat.is_gt(ip_used(next),4096n),Machine{tail,ip_fail(next,13n),scopes},ip_visit_node(ip_get(program,index),depth,tail,next,scopes)))
def ip_case_rows(rows: List<&2,IPCase>,+depth: Nat,+scope: Nat,fallback: IPFallback,+tail: List<&2,IPTask>,+state: IPState,+scopes: List<&2,IPScope>) -> IPMachine:
  match rows:
    case Nil{}: Machine{Con{Fallback{fallback,depth},tail},state,scopes}
    case Con{Case{fields,child,keys},rest}:
      Bool.pick(IPMachine,fields,Machine{Con{Visit{child,depth},Con{BeginKeys{keys,scope},Con{Cases{rest,depth,scope,fallback},tail}}},state,scopes},Machine{tail,ip_fail(state,3n),scopes})
def ip_decode_key(+key: Nat,+remaining: List<&2,Nat>,+id: Nat,+tail: List<&2,IPTask>,+state: IPState,+scopes: List<&2,IPScope>,scope: IPScope) -> IPMachine:
  match scope:
    case Scope{actual,+seen,+alternatives,+thresholds}:
      +next = ip_emit(state,Nat.add(100n,key))
      +updated : IPScope = Scope{id,Con{key,seen},Nat.add(alternatives,1n),thresholds}
      Bool.pick(IPMachine,Nat.is_eq(actual,0n),Machine{tail,ip_fail(state,99n),scopes},
        Bool.pick(IPMachine,Nat.is_ge(alternatives,512n),Machine{tail,ip_fail(state,6n),scopes},
          Bool.pick(IPMachine,ip_contains(seen,key),Machine{tail,ip_fail(next,8n),scopes},
            Machine{Con{Keys{remaining,id},tail},next,ip_replace(scopes,updated)})))
def ip_range_existing(+remaining: List<&2,IPRangeEntry>,+depth: Nat,+id: Nat,+fallback: IPFallback,+threshold: Nat,+body: Nat,child: Nat,+tail: List<&2,IPTask>,+state: IPState,+scopes: List<&2,IPScope>,scope: IPScope,found: IPFound) -> IPMachine:
  match scope:
    case Scope{actual,+keys,+alternatives,+seen}:
      match found:
        case Found{present,previous}:
          +next_tasks : List<&2,IPTask> = Con{Ranges{remaining,depth,id,fallback},tail}
          Bool.pick(IPMachine,Nat.is_eq(actual,0n),Machine{tail,ip_fail(state,99n),scopes},
            Bool.pick(IPMachine,present,
              Bool.pick(IPMachine,Nat.is_eq(body,previous),Machine{next_tasks,state,scopes},Machine{tail,ip_fail(state,12n),scopes}),
              Machine{Con{Visit{child,depth},next_tasks},state,ip_replace(scopes,Scope{id,keys,alternatives,Con{Seen{threshold,body},seen}})}))
def ip_range_row(row: IPRangeEntry,remaining: List<&2,IPRangeEntry>,depth: Nat,+id: Nat,fallback: IPFallback,+tail: List<&2,IPTask>,+state: IPState,+scopes: List<&2,IPScope>) -> IPMachine:
  match row:
    case Entry{+threshold,fields,body,child}:
      +scope = ip_scope(scopes,id)
      +found = ip_scope_seen(scope,threshold)
      Bool.pick(IPMachine,Nat.is_gt(threshold,3n),Machine{tail,ip_fail(state,11n),scopes},
        Bool.pick(IPMachine,fields,ip_range_existing(remaining,depth,id,fallback,threshold,body,child,tail,state,scopes,scope,found),Machine{tail,ip_fail(state,3n),scopes}))

def ip_compile_step(program: List<&2,IPInstruction>,task: IPTask,+tail: List<&2,IPTask>,+state: IPState,+scopes: List<&2,IPScope>) -> IPMachine:
  match task:
    case Visit{index,depth}: ip_visit(program,index,depth,tail,state,scopes)
    case Cases{rows,depth,scope,fallback}: ip_case_rows(rows,depth,scope,fallback,tail,state,scopes)
    case BeginKeys{+keys,scope}:
      Bool.pick(IPMachine,Nat.is_eq(List.length(&2,Nat,keys),0n),Machine{tail,ip_fail(state,7n),scopes},Machine{Con{Keys{keys,scope},tail},state,scopes})
    case Keys{keys,+scope}:
      match keys:
        case Nil{}: Machine{tail,state,scopes}
        case Con{key,remaining}: ip_decode_key(key,remaining,scope,tail,state,scopes,ip_scope(scopes,scope))
    case Ranges{rows,+depth,+scope,+fallback}:
      match rows:
        case Nil{}: Machine{Con{Fallback{fallback,depth},tail},ip_emit(state,5n),scopes}
        case Con{row,remaining}: ip_range_row(row,remaining,depth,scope,fallback,tail,state,scopes)
    case Fallback{fallback,depth}:
      match fallback:
        case Absent{}: Machine{tail,state,scopes}
        case ExplicitNull{}: Machine{tail,ip_fail(state,9n),scopes}
        case Child{index}: Machine{Con{Visit{index,depth},tail},state,scopes}
    case FinishRoot{overflow}:
      Machine{tail,Bool.pick(IPState,overflow,ip_fail(state,14n),state),scopes}

# This fuel bounds the research machine, not the original compiler's API.
def ip_compile_loop(fuel: Nat,+program: List<&2,IPInstruction>,machine: IPMachine) -> IPState:
  match fuel:
    case 0n:
      match machine:
        case Machine{tasks,state,scopes}: ip_fail(state,99n)
    case 1n+remaining:
      match machine:
        case Machine{tasks,+state,scopes}:
          match tasks:
            case Nil{}: state
            case Con{task,tail}:
              Bool.pick(IPState,Bool.not(Nat.is_eq(ip_error(state),0n)),state,
                ip_compile_loop(remaining,program,ip_compile_step(program,task,tail,state,scopes)))
def ip_root(bad_fields: Bool,overflow: Bool,program: List<&2,IPInstruction>,index: Nat) -> IPState:
  Bool.pick(IPState,bad_fields,State{1n,0n,Nil{},Nil{}},
    ip_compile_loop(20000n,program,Machine{[Visit{index,0n},FinishRoot{overflow}],State{0n,0n,Nil{},Nil{}},Nil{}}))

type IPContext is Data:
  Context{pick: Nat,condition: Bool,number: F.FloatAtom,color: Nat}
type IPLayer is Data:
  Layer{reference: Nat,tints: Nat}
type IPEvaluation is Data:
  Evaluation{valid: Bool,layers: List<&2,IPLayer>,events: List<&2,Nat>}
type IPEvalTask is Data:
  Eval{index: Nat}
type IPEvalMachine is Data:
  EvalMachine{tasks: List<&2,IPEvalTask>,reverse_layers: List<&2,IPLayer>,reverse_events: List<&2,Nat>,valid: Bool}

def ip_pick(context: IPContext) -> Nat:
  match context:
    case Context{pick,condition,number,color}: pick
def ip_condition(context: IPContext) -> Bool:
  match context:
    case Context{pick,condition,number,color}: condition
def ip_number(context: IPContext) -> F.FloatAtom:
  match context:
    case Context{pick,condition,number,color}: number
def ip_eval_visits(children: List<&2,Nat>,tail: List<&2,IPEvalTask>) -> List<&2,IPEvalTask>:
  match children:
    case Nil{}: tail
    case Con{head,rest}: Con{Eval{head},ip_eval_visits(rest,tail)}
def ip_select(cases: List<&2,IPCase>,+key: Nat) -> IPFound:
  match cases:
    case Nil{}: Found{False{},0n}
    case Con{Case{fields,child,keys},tail}:
      Bool.pick(IPFound,ip_contains(keys,key),Found{True{},child},ip_select(tail,key))
type IPBest is Data:
  Best{present: Bool,child: Nat,rank: Nat}
def ip_better(entry: IPRangeEntry,+value: Nat,best: IPBest) -> IPBest:
  match entry:
    case Entry{+threshold,fields,body,+child}:
      match best:
        case Best{+present,+previous,+rank}:
          Bool.pick(IPBest,Bool.and(Nat.is_le(threshold,value),Bool.or(Bool.not(present),Nat.is_gt(threshold,rank))),Best{True{},child,threshold},Best{present,previous,rank})
def ip_best(entries: List<&2,IPRangeEntry>,+value: Nat,best: IPBest) -> IPFound:
  match entries:
    case Nil{}:
      match best:
        case Best{present,child,rank}: Found{present,child}
    case Con{head,tail}: ip_best(tail,value,ip_better(head,value,best))
def ip_eval_fallback(fallback: IPFallback,tail: List<&2,IPEvalTask>,layers: List<&2,IPLayer>,events: List<&2,Nat>) -> IPEvalMachine:
  match fallback:
    case Absent{}: EvalMachine{tail,Con{Layer{0n,0n},layers},events,True{}}
    case ExplicitNull{}: EvalMachine{tail,layers,events,False{}}
    case Child{index}: EvalMachine{Con{Eval{index},tail},layers,events,True{}}
def ip_eval_selected(found: IPFound,fallback: IPFallback,+tail: List<&2,IPEvalTask>,+layers: List<&2,IPLayer>,+events: List<&2,Nat>) -> IPEvalMachine:
  match found:
    case Found{present,index}:
      Bool.pick(IPEvalMachine,present,EvalMachine{Con{Eval{index},tail},layers,events,True{}},ip_eval_fallback(fallback,tail,layers,events))
def ip_eval_step(instruction: IPInstruction,+context: IPContext,+tail: List<&2,IPEvalTask>,+layers: List<&2,IPLayer>,+events: List<&2,Nat>) -> IPEvalMachine:
  match instruction:
    case Unsupported{}: EvalMachine{tail,layers,events,False{}}
    case Empty{fields}: EvalMachine{tail,layers,events,True{}}
    case Leaf{fields,present,reference,tints}: EvalMachine{tail,Con{Layer{reference,tints},layers},events,True{}}
    case Composite{fields,children,empty_run}:
      Bool.pick(IPEvalMachine,Nat.is_eq(empty_run,0n),EvalMachine{ip_eval_visits(children,tail),layers,events,True{}},EvalMachine{tail,layers,events,True{}})
    case Condition{fields,yes,no}:
      EvalMachine{Con{Eval{Bool.pick(Nat,ip_condition(context),yes,no)},tail},layers,Con{6n,events},True{}}
    case Select{fields,cases,fallback}:
      ip_eval_selected(ip_select(cases,ip_pick(context)),fallback,tail,layers,Con{7n,events})
    case Range{fields,entries,flip,fallback}:
      +value = F.jf_scale(flip,ip_number(context))
      ip_eval_selected(Bool.pick(IPFound,F.jf_nan(value),Found{False{},0n},ip_best(entries,F.jf_rank(value),Best{False{},0n,0n})),fallback,tail,layers,Con{8n,events})
def ip_eval_result(machine: IPEvalMachine) -> IPEvaluation:
  match machine:
    case EvalMachine{tasks,layers,events,valid}:
      Evaluation{valid,List.reverse(&2,IPLayer,layers),List.reverse(&2,Nat,events)}
def ip_eval_loop(fuel: Nat,+program: List<&2,IPInstruction>,+context: IPContext,machine: IPEvalMachine) -> IPEvaluation:
  match fuel:
    case 0n:
      match machine:
        case EvalMachine{tasks,layers,events,valid}: Evaluation{False{},List.reverse(&2,IPLayer,layers),List.reverse(&2,Nat,events)}
    case 1n+remaining:
      match machine:
        case EvalMachine{tasks,+layers,+events,+valid}:
          match tasks:
            case Nil{}: ip_eval_result(EvalMachine{Nil{},layers,events,valid})
            case Con{Eval{index},tail}:
              Bool.pick(IPEvaluation,valid,ip_eval_loop(remaining,program,context,ip_eval_step(ip_get(program,index),context,tail,layers,events)),ip_eval_result(EvalMachine{Nil{},layers,events,valid}))
def ip_eval(program: List<&2,IPInstruction>,index: Nat,context: IPContext) -> IPEvaluation:
  ip_eval_loop(20000n,program,context,EvalMachine{[Eval{index}],Nil{},Nil{},True{}})

law ip_empty_has_no_factory:
  {ip_root(False{},False{},[Empty{True{}}],0n) == State{0n,1n,Nil{},Nil{}} : IPState}
def ip_empty_has_no_factory():
  {==}
law ip_late_refusal_retains_callback:
  {ip_root(False{},True{},[Leaf{True{},True{},7n,1n}],0n) == State{14n,1n,[7n],[1n]} : IPState}
def ip_late_refusal_retains_callback():
  {==}
law ip_tint_limit_before_callbacks:
  {ip_root(False{},False{},[Leaf{True{},True{},7n,33n}],0n) == State{5n,1n,[7n],Nil{}} : IPState}
def ip_tint_limit_before_callbacks():
  {==}
law ip_empty_composite_is_not_missing:
  {ip_eval([Composite{True{},Nil{},0n}],0n,Context{0n,False{},F.PositiveZero{},0n}) == Evaluation{True{},Nil{},Nil{}} : IPEvaluation}
def ip_empty_composite_is_not_missing():
  {==}
law ip_empty_select_constructs_selector:
  {ip_root(False{},False{},[Select{True{},Nil{},Absent{}}],0n) == State{0n,1n,Nil{},[3n]} : IPState}
def ip_empty_select_constructs_selector():
  {==}
law ip_null_fallback_after_selector:
  {ip_root(False{},False{},[Select{True{},Nil{},ExplicitNull{}}],0n) == State{9n,1n,Nil{},[3n]} : IPState}
def ip_null_fallback_after_selector():
  {==}
law ip_empty_run_budget_boundary:
  {ip_empty_children(State{0n,1n,Nil{},Nil{}},1n,4095n) == State{0n,4096n,Nil{},Nil{}} : IPState}
def ip_empty_run_budget_boundary():
  {==}
law ip_empty_run_one_more_refuses:
  {ip_empty_children(State{0n,1n,Nil{},Nil{}},1n,4096n) == State{13n,4097n,Nil{},Nil{}} : IPState}
def ip_empty_run_one_more_refuses():
  {==}
