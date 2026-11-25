import Base

# Two keys/three authored identities. No iteration-order promise for HashMap.
type AtlasState is Data:
  AtlasState{slots: List<&2,Nat>,created: List<&2,Nat>,discards: List<&2,Nat>,runs: Nat,catches: Nat,error: Nat}
type AtlasAction is Data:
  AtlasAction{kind: Nat,key: Nat,supplier: Nat,caught: Bool}
def atlas_empty() -> AtlasState:
  AtlasState{Con{0n,Con{0n,Nil{}}},Con{0n,Con{0n,Con{0n,Nil{}}}},Con{0n,Con{0n,Con{0n,Nil{}}}},0n,0n,0n}
def atlas_at(xs: List<&2,Nat>,+index: Nat) -> Nat:
  match xs:
    case Nil{}: 0n
    case Con{head,tail}: Bool.pick(Nat,Nat.is_eq(index,0n),head,atlas_at(tail,Nat.sub(index,1n)))
def atlas_replace(xs: List<&2,Nat>,+index: Nat,+value: Nat) -> List<&2,Nat>:
  match xs:
    case Nil{}: Nil{}
    case Con{+head,+tail}: Bool.pick(List<&2,Nat>,Nat.is_eq(index,0n),Con{value,tail},Con{head,atlas_replace(tail,Nat.sub(index,1n),value)})
def atlas_slots(s: AtlasState) -> List<&2,Nat>:
  match s:
    case AtlasState{slots,_,_,_,_,_}: slots
def atlas_error(s: AtlasState) -> Nat:
  match s:
    case AtlasState{_,_,_,_,_,error}: error
def atlas_discard(s: AtlasState,+supplier: Nat,throwing: Nat) -> AtlasState:
  match s:
    case AtlasState{+slots,+created,+discards,+runs,+catches,+error}:
      +index=Nat.sub(supplier,1n)
      Bool.pick(AtlasState,Nat.is_eq(supplier,0n),AtlasState{slots,created,discards,runs,catches,error},
        AtlasState{slots,created,atlas_replace(discards,index,Nat.add(atlas_at(discards,index),1n)),runs,catches,Bool.pick(Nat,Nat.is_eq(supplier,throwing),Nat.add(supplier,1n),0n)})
def atlas_add(s: AtlasState,+key: Nat,+supplier: Nat,throwing: Nat) -> AtlasState:
  match s:
    case AtlasState{+slots,created,discards,runs,catches,error}:
      old=atlas_at(slots,key)
      atlas_discard(AtlasState{atlas_replace(slots,key,supplier),atlas_replace(created,Nat.sub(supplier,1n),1n),discards,runs,catches,error},old,throwing)
def atlas_remove_clear(s: AtlasState,+key: Nat) -> AtlasState:
  match s:
    case AtlasState{+slots,+created,+discards,+runs,+catches,+error}:
      Bool.pick(AtlasState,Nat.is_eq(error,0n),AtlasState{atlas_replace(slots,key,0n),created,discards,runs,catches,error},AtlasState{slots,created,discards,runs,catches,error})
def atlas_remove_at(+s: AtlasState,+key: Nat,throwing: Nat) -> AtlasState:
  atlas_remove_clear(atlas_discard(s,atlas_at(atlas_slots(s),key),throwing),key)
def atlas_matches(+selection: Nat,key: Nat) -> Bool:
  Bool.or(Nat.is_eq(selection,1n),Bool.and(Nat.is_eq(selection,2n),Nat.is_eq(key,0n)))
def atlas_remove_right(+s: AtlasState,selection: Nat,throwing: Nat) -> AtlasState:
  Bool.pick(AtlasState,Bool.and(Nat.is_eq(atlas_error(s),0n),atlas_matches(selection,1n)),atlas_remove_at(s,1n,throwing),s)
def atlas_remove(+s: AtlasState,+selection: Nat,+throwing: Nat) -> AtlasState:
  atlas_remove_right(Bool.pick(AtlasState,atlas_matches(selection,0n),atlas_remove_at(s,0n,throwing),s),selection,throwing)
def atlas_fail(s: AtlasState) -> AtlasState:
  match s:
    case AtlasState{slots,created,discards,runs,catches,_}: AtlasState{slots,created,discards,runs,catches,1n}
def atlas_raw_kind(+s: AtlasState,kind: Nat,key: Nat,supplier: Nat,+throwing: Nat) -> AtlasState:
  match kind:
    case 0n: atlas_add(s,key,supplier,throwing)
    case 1n: atlas_remove(s,key,throwing)
    case _: atlas_fail(s)
def atlas_raw(+s: AtlasState,a: AtlasAction,+throwing: Nat) -> AtlasState:
  match a:
    case AtlasAction{kind,key,supplier,_}:
      Bool.pick(AtlasState,Nat.is_eq(atlas_error(s),0n),atlas_raw_kind(s,kind,key,supplier,throwing),s)
def atlas_catch(s: AtlasState,caught: Bool) -> AtlasState:
  match s:
    case AtlasState{+slots,+created,+discards,+runs,+catches,+error}:
      Bool.pick(AtlasState,Bool.and(caught,Bool.not(Nat.is_eq(error,0n))),AtlasState{slots,created,discards,runs,Nat.add(catches,1n),0n},AtlasState{slots,created,discards,runs,catches,error})
def atlas_step(+s: AtlasState,+a: AtlasAction,throwing: Nat) -> AtlasState:
  match a:
    case AtlasAction{+kind,+key,+supplier,+caught}: atlas_catch(atlas_raw(s,AtlasAction{kind,key,supplier,caught},throwing),caught)
def atlas_actions(actions: List<&2,AtlasAction>,+s: AtlasState,+throwing: Nat) -> AtlasState:
  match actions:
    case Nil{}: s
    case Con{a,tail}: Bool.pick(AtlasState,Nat.is_eq(atlas_error(s),0n),atlas_actions(tail,atlas_step(s,a,throwing),throwing),s)
def atlas_run(s: AtlasState) -> AtlasState:
  match s:
    case AtlasState{slots,created,discards,runs,catches,error}: AtlasState{slots,created,discards,Nat.add(runs,1n),catches,error}
def atlas_sources(groups: List<&2,List<&2,AtlasAction>>,+s: AtlasState,+throwing: Nat) -> AtlasState:
  match groups:
    case Nil{}: s
    case Con{head,tail}: Bool.pick(AtlasState,Nat.is_eq(atlas_error(s),0n),atlas_sources(tail,atlas_actions(head,atlas_run(s),throwing),throwing),s)
def atlas_count(xs: List<&2,Nat>,+supplier: Nat) -> Nat:
  match xs:
    case Nil{}: 0n
    case Con{head,tail}: Nat.add(Bool.pick(Nat,Nat.is_eq(head,supplier),1n,0n),atlas_count(tail,supplier))
def atlas_bit(value: Bool) -> Nat:
  Bool.pick(Nat,value,1n,0n)
def atlas_render(s: AtlasState) -> String:
  match s:
    case AtlasState{+slots,+created,+discards,runs,catches,+error}:
      +ok=atlas_bit(Nat.is_eq(error,0n))
      +slots=Bool.pick(List<&2,Nat>,Nat.is_eq(error,0n),slots,Nil{})
      Nat.show(ok) ++ ":" ++ Nat.show(ok) ++ ":" ++ Nat.show(atlas_count(slots,1n)) ++ ":" ++ Nat.show(atlas_count(slots,2n)) ++ ":" ++ Nat.show(atlas_count(slots,3n)) ++ ":" ++ Nat.show(atlas_at(created,0n)) ++ ":" ++ Nat.show(atlas_at(created,1n)) ++ ":" ++ Nat.show(atlas_at(created,2n)) ++ ":" ++ Nat.show(atlas_at(discards,0n)) ++ ":" ++ Nat.show(atlas_at(discards,1n)) ++ ":" ++ Nat.show(atlas_at(discards,2n)) ++ ":" ++ Nat.show(runs) ++ ":" ++ Nat.show(catches) ++ ":" ++ Nat.show(error)

law atlas_empty_default:
  {atlas_render(atlas_empty()) == "1:1:0:0:0:0:0:0:0:0:0:0:0:0" : String}
def atlas_empty_default():
  {==}
law atlas_replacement_discards_old:
  {atlas_render(atlas_add(atlas_add(atlas_empty(),0n,1n,0n),0n,2n,0n)) == "1:1:0:1:0:1:1:0:1:0:0:0:0:0" : String}
def atlas_replacement_discards_old():
  {==}
law atlas_failed_put_keeps_new:
  {atlas_slots(atlas_add(atlas_add(atlas_empty(),0n,1n,0n),0n,2n,1n)) == Con{2n,Con{0n,Nil{}}} : List<&2,Nat>}
def atlas_failed_put_keeps_new():
  {==}
law atlas_failed_remove_keeps_old:
  {atlas_slots(atlas_remove_at(atlas_add(atlas_empty(),0n,1n,0n),0n,1n)) == Con{1n,Con{0n,Nil{}}} : List<&2,Nat>}
def atlas_failed_remove_keeps_old():
  {==}
law atlas_same_identity_retained:
  {atlas_render(atlas_add(atlas_add(atlas_empty(),0n,1n,0n),0n,1n,0n)) == "1:1:1:0:0:1:0:0:1:0:0:0:0:0" : String}
def atlas_same_identity_retained():
  {==}
law atlas_alias_survives:
  {atlas_slots(atlas_add(atlas_add(atlas_add(atlas_empty(),0n,1n,0n),1n,1n,0n),0n,2n,0n)) == Con{2n,Con{1n,Nil{}}} : List<&2,Nat>}
def atlas_alias_survives():
  {==}
law atlas_remove_clears:
  {atlas_slots(atlas_remove_at(atlas_add(atlas_empty(),0n,1n,0n),0n,0n)) == Con{0n,Con{0n,Nil{}}} : List<&2,Nat>}
def atlas_remove_clears():
  {==}
law atlas_source_failure_no_discard:
  {atlas_render(atlas_fail(atlas_add(atlas_empty(),0n,1n,0n))) == "0:0:0:0:0:1:0:0:0:0:0:0:0:1" : String}
def atlas_source_failure_no_discard():
  {==}
