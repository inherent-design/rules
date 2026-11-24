import Base

# Same-root admitted-capability projection. Current=0, metadata candidate=1.
# Phase: fresh/locked/allocated/returned/killed. API: pending/ok/unknown/busy.
# Command: running/acknowledged/killed. Found: not lookup/absent/present.
type IActor is Data:
  IActor{variant: Nat, phase: Nat, api: Nat, command: Nat, scratch: Bool, found: Nat}
type IState is Data:
  IState{slot: Bool, operation: Bool, metadata: Bool, association: Bool, unknown: Bool, actors: List<&2,IActor>, writes: Nat, valid: Bool}
type IEvent is Data:
  IEvent{kind: Nat, actor: Nat, variant: Nat}
def fresh() -> IActor:
  IActor{0n,0n,0n,0n,False{},0n}
def base() -> IState:
  IState{False{},False{},False{},False{},False{},[fresh(),fresh()],0n,True{}}
def holding(+a: IActor) -> Bool:
  match a:
    case IActor{_,+p,_,_,_,_}: Bool.or(Nat.is_eq(p,1n),Nat.is_eq(p,2n))
def held(+xs: List<&2,IActor>,+variant: Nat) -> Bool:
  match xs:
    case Nil{}: False{}
    case +a <> +tail:
      match a:
        case IActor{+v,_,_,_,_,_}: Bool.or(Bool.and(holding(a),Nat.is_eq(v,variant)),held(tail,variant))
def scratch(+xs: List<&2,IActor>) -> Bool:
  match xs:
    case Nil{}: False{}
    case IActor{_,_,_,_,+s,_} <> +tail: Bool.or(s,scratch(tail))
def at(+xs: List<&2,IActor>,+n: Nat) -> IActor:
  match xs n:
    case Nil{} _: fresh()
    case +a <> _ 0n: a
    case _ <> +tail +k: at(tail,Nat.sub(k,1n))
def put(+xs: List<&2,IActor>,+n: Nat,+a: IActor) -> List<&2,IActor>:
  match xs n:
    case Nil{} _: []
    case _ <> +tail 0n: a <> tail
    case +h <> +tail +k: h <> put(tail,Nat.sub(k,1n),a)
def reject(+s: IState) -> IState:
  match s:
    case IState{+a,+b,+c,+d,+e,+f,+g,_}: IState{a,b,c,d,e,f,g,False{}}
def replace_actor(+s: IState,+n: Nat,+a: IActor) -> IState:
  match s:
    case IState{+x,+y,+z,+w,+u,+xs,+k,+v}: IState{x,y,z,w,u,put(xs,n,a),k,v}
def start_actor(+s: IState,+n: Nat,+variant: Nat,+a: IActor,+lookup: Bool) -> IState:
  match s a:
    case IState{+slot,+op,+meta,+assoc,+unknown,+xs,+writes,_} IActor{_,+p,_,_,_,_}:
      +unresolved=Bool.and(Bool.not(assoc),Bool.or(op,Bool.or(scratch(xs),unknown)))
      +ordinary=Bool.pick(Nat,assoc,1n,Bool.pick(Nat,held(xs,variant),3n,0n))
      +answer=Bool.pick(Nat,unresolved,2n,Bool.pick(Nat,lookup,1n,ordinary))
      +owns=Nat.is_eq(answer,0n)
      +f=Bool.pick(Nat,Bool.and(lookup,Bool.not(unresolved)),Bool.pick(Nat,assoc,2n,1n),0n)
      +target={IActor{variant,Bool.pick(Nat,owns,1n,3n),answer,0n,False{},f} : IActor}
      +changed={IState{Bool.or(slot,owns),Bool.or(op,Bool.and(owns,Nat.is_eq(variant,0n))),Bool.or(meta,Bool.and(owns,Nat.is_eq(variant,1n))),assoc,unknown,put(xs,n,target),writes,True{}} : IState}
      Bool.pick(IState,Nat.is_eq(p,0n),changed,reject(s))
def allocate_actor(+s: IState,+n: Nat,+a: IActor) -> IState:
  match s a:
    case IState{_,_,_,+assoc,_,_,_,_} IActor{+v,+p,+a,+c,_,+f}:
      +allowed=Bool.and(Nat.is_eq(p,1n),Bool.not(assoc))
      Bool.pick(IState,allowed,replace_actor(s,n,IActor{v,2n,a,c,True{},f}),reject(s))
def finish_actor(+s: IState,+n: Nat,+a: IActor) -> IState:
  match s a:
    case IState{+x,+y,+z,+assoc,+u,+xs,+w,_} IActor{+v,+p,_,+c,_,_}:
      +allowed=Bool.and(holding(a),Bool.or(assoc,Nat.is_eq(p,2n)))
      +changed={IState{x,y,z,True{},u,put(xs,n,IActor{v,3n,1n,c,False{},0n}),Nat.add(Bool.pick(Nat,assoc,0n,1n),w),True{}} : IState}
      Bool.pick(IState,allowed,changed,reject(s))
def kill_actor(+s: IState,+n: Nat,+a: IActor) -> IState:
  match a:
    case IActor{+v,+p,+a,+c,+t,+f}:
      +allowed=Bool.and(Bool.and(Bool.not(Nat.is_eq(p,0n)),Bool.not(Nat.is_eq(p,4n))),Nat.is_eq(c,0n))
      Bool.pick(IState,allowed,replace_actor(s,n,IActor{v,4n,a,2n,t,f}),reject(s))
def ack_actor(+s: IState,+n: Nat,+a: IActor) -> IState:
  match a:
    case IActor{+v,+p,+a,+c,+t,+f}:
      +allowed=Bool.and(Nat.is_eq(p,3n),Nat.is_eq(c,0n))
      Bool.pick(IState,allowed,replace_actor(s,n,IActor{v,p,a,1n,t,f}),reject(s))
def actor_step(+s: IState,+e: IEvent,+a: IActor) -> IState:
  match e:
    case IEvent{0n,+n,+v}: start_actor(s,n,v,a,False{})
    case IEvent{5n,+n,+v}: start_actor(s,n,v,a,True{})
    case IEvent{1n,+n,_}: allocate_actor(s,n,a)
    case IEvent{2n,+n,_}: finish_actor(s,n,a)
    case IEvent{3n,+n,_}: kill_actor(s,n,a)
    case IEvent{4n,+n,_}: ack_actor(s,n,a)
    case _: reject(s)
def count(xs: List<&2,IActor>) -> Nat:
  match xs:
    case Nil{}: 0n
    case _ <> tail: Nat.add(1n,count(tail))
def primitive(+s: IState,+e: IEvent) -> IState:
  match s e:
    case IState{_,_,_,_,_,+xs,_,+valid} IEvent{_,+n,+v}:
      +allowed=Bool.and(valid,Bool.and(Nat.is_le(v,1n),Nat.is_lt(n,count(xs))))
      Bool.pick(IState,allowed,actor_step(s,e,at(xs,n)),reject(s))
def finish_call_actor(+s: IState,+e: IEvent,+a: IActor,+assoc: Bool) -> IState:
  match e a:
    case IEvent{_,+n,+v} IActor{_,+p,_,_,_,_}:
      +allocated=Bool.pick(IState,assoc,s,primitive(s,IEvent{1n,n,v}))
      +finished=Bool.pick(IState,Nat.is_eq(p,1n),primitive(allocated,IEvent{2n,n,v}),s)
      primitive(finished,IEvent{4n,n,v})
def finish_call(+s: IState,+e: IEvent) -> IState:
  match s e:
    case IState{_,_,_,+assoc,_,+xs,_,_} IEvent{_,+n,_}: finish_call_actor(s,e,at(xs,n),assoc)
def step(+s: IState,+e: IEvent) -> IState:
  match e:
    case IEvent{+k,+n,+v}:
      +first=primitive(s,IEvent{Bool.pick(Nat,Nat.is_eq(k,6n),0n,5n),n,v})
      Bool.pick(IState,Bool.or(Nat.is_eq(k,6n),Nat.is_eq(k,7n)),finish_call(first,e),primitive(s,e))
def run(+es: List<&2,IEvent>,+s: IState) -> IState:
  match es:
    case Nil{}: s
    case +e <> +tail: run(tail,step(s,e))
def bit(+b: Bool,+n: Nat) -> Nat:
  Bool.pick(Nat,b,n,0n)
def mask(+s: IState) -> Nat:
  match s:
    case IState{+a,+b,+c,+d,+e,+xs,_,_}: Nat.add(bit(a,1n),Nat.add(bit(b,2n),Nat.add(bit(c,4n),Nat.add(bit(scratch(xs),8n),Nat.add(bit(d,16n),bit(e,32n))))))
def leases(+s: IState) -> Nat:
  match s:
    case IState{_,_,_,_,_,+xs,_,_}: Nat.add(bit(held(xs,0n),1n),bit(held(xs,1n),2n))
def actor_result(+a: IActor) -> Nat:
  match a:
    case IActor{_,_,+r,_,_,_}: r
def result(+s: IState,+n: Nat) -> Nat:
  match s:
    case IState{_,_,_,_,_,+xs,_,_}: actor_result(at(xs,n))
def writes(+s: IState) -> Nat:
  match s:
    case IState{_,_,_,_,_,_,+n,_}: n
def valid(+s: IState) -> Bool:
  match s:
    case IState{_,_,_,_,_,_,_,+v}: v
def actor_text(+a: IActor) -> String:
  match a:
    case IActor{+v,+p,+a,+c,+t,+f}: Nat.show(v) ++ "," ++ Nat.show(p) ++ "," ++ Nat.show(a) ++ "," ++ Nat.show(c) ++ "," ++ Nat.show(bit(t,1n)) ++ "," ++ Nat.show(f)
def actors_text(+xs: List<&2,IActor>) -> String:
  match xs:
    case Nil{}: ""
    case +a <> +tail: "/" ++ actor_text(a) ++ actors_text(tail)
def render(+s: IState) -> String:
  match s:
    case IState{_,_,_,_,_,+xs,+w,+v}: Nat.show(bit(v,1n)) ++ "/" ++ Nat.show(mask(s)) ++ "/" ++ Nat.show(leases(s)) ++ "/" ++ Nat.show(w) ++ actors_text(xs)

# PROPOSED admission only: no native directory publication executed.
def proposed(+complete: Bool,+identity: Bool,+root: Bool,+host_ready: Bool,+target: Nat) -> Nat:
  +ready=Bool.and(Bool.and(complete,identity),Bool.and(root,host_ready))
  +outcome=Bool.pick(Nat,Nat.is_eq(target,0n),1n,Bool.pick(Nat,Nat.is_eq(target,1n),2n,0n))
  Bool.pick(Nat,ready,outcome,0n)

law current_post_lock_retry_refuses:
  {result(run([IEvent{0n,0n,0n},IEvent{3n,0n,0n},IEvent{0n,1n,0n}],base()),1n) == 2n : Nat}
def current_post_lock_retry_refuses():
  {==}
law candidate_post_lock_retry_admitted:
  {leases(run([IEvent{0n,0n,1n},IEvent{3n,0n,0n},IEvent{0n,1n,1n}],base())) == 2n : Nat}
def candidate_post_lock_retry_admitted():
  {==}
law candidate_temporary_retry_refuses:
  {result(run([IEvent{0n,0n,1n},IEvent{1n,0n,0n},IEvent{3n,0n,0n},IEvent{0n,1n,1n}],base()),1n) == 2n : Nat}
def candidate_temporary_retry_refuses():
  {==}
law kill_releases_lease_not_file:
  {mask(run([IEvent{0n,0n,1n},IEvent{3n,0n,0n}],base())) == 5n : Nat}
def kill_releases_lease_not_file():
  {==}
law metadata_contender_busy:
  {result(run([IEvent{0n,0n,1n},IEvent{0n,1n,1n}],base()),1n) == 3n : Nat}
def metadata_contender_busy():
  {==}
law two_protocol_leases_can_coexist:
  {leases(run([IEvent{0n,0n,1n},IEvent{0n,1n,0n}],base())) == 3n : Nat}
def two_protocol_leases_can_coexist():
  {==}
law second_read_does_not_rewrite:
  {writes(run([IEvent{0n,0n,1n},IEvent{0n,1n,0n},IEvent{1n,1n,0n},IEvent{2n,1n,0n},IEvent{2n,0n,0n}],base())) == 1n : Nat}
def second_read_does_not_rewrite():
  {==}
law killed_after_API_return_preserves_success:
  {result(run([IEvent{0n,0n,0n},IEvent{1n,0n,0n},IEvent{2n,0n,0n},IEvent{3n,0n,0n}],base()),0n) == 1n : Nat}
def killed_after_API_return_preserves_success():
  {==}
law dead_actor_cannot_publish:
  {valid(run([IEvent{0n,0n,1n},IEvent{3n,0n,0n},IEvent{2n,0n,0n}],base())) == False{} : Bool}
def dead_actor_cannot_publish():
  {==}
law proposed_unknown_target_refuses:
  {proposed(True{},True{},True{},True{},2n) == 0n : Nat}
def proposed_unknown_target_refuses():
  {==}
law proposed_incomplete_image_refuses:
  {proposed(False{},True{},True{},True{},0n) == 0n : Nat}
def proposed_incomplete_image_refuses():
  {==}
law proposed_existing_is_not_publication:
  {proposed(True{},True{},True{},True{},1n) == 2n : Nat}
def proposed_existing_is_not_publication():
  {==}
