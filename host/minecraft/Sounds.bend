import Base
import ../java/Word32.bend as J

type SoundEntry is Data:
  SoundEntry{first: U32,second: U32,fail: Bool}
type SoundChoice is Data:
  SoundChoice{selected: Nat,calls: List<&2,Nat>}
type SoundPreload is Data:
  SoundPreload{error: Nat,calls: List<&2,Nat>}
type SoundResult is Data:
  SoundResult{weight: U32,selected: Nat,fallback: Bool,error: Nat,weightCalls: List<&2,Nat>,preloadCalls: List<&2,Nat>,bound: U32,randomCalls: Nat}
def sound_sum(entries: List<&2,SoundEntry>) -> U32:
  match entries:
    case Nil{}: 0
    case Con{SoundEntry{first,_,_},tail}: U32.add(first,sound_sum(tail))
def sound_fill(entries: List<&2,SoundEntry>,+value: Nat) -> List<&2,Nat>:
  match entries:
    case Nil{}: Nil{}
    case Con{_,tail}: Con{value,sound_fill(tail,value)}
def sound_choice_prepend(choice: SoundChoice) -> SoundChoice:
  match choice:
    case SoundChoice{selected,calls}: SoundChoice{selected,Con{2n,calls}}
def sound_traverse(entries: List<&2,SoundEntry>,+index: U32,+ordinal: Nat) -> SoundChoice:
  match entries:
    case Nil{}: SoundChoice{0n,Nil{}}
    case Con{SoundEntry{_,second,_},+tail}:
      +next=U32.sub(index,second)
      Bool.pick(SoundChoice,J.jw_negative(next),SoundChoice{ordinal,Con{2n,sound_fill(tail,1n)}},sound_choice_prepend(sound_traverse(tail,next,Nat.add(ordinal,1n))))
def sound_preload_prepend(result: SoundPreload) -> SoundPreload:
  match result:
    case SoundPreload{error,calls}: SoundPreload{error,Con{1n,calls}}
def sound_preload(entries: List<&2,SoundEntry>) -> SoundPreload:
  match entries:
    case Nil{}: SoundPreload{0n,Nil{}}
    case Con{SoundEntry{_,_,fail},+tail}:
      Bool.pick(SoundPreload,fail,SoundPreload{2n,Con{1n,sound_fill(tail,0n)}},sound_preload_prepend(sound_preload(tail)))
def sound_from_preload(+entries: List<&2,SoundEntry>,result: SoundPreload) -> SoundResult:
  match result:
    case SoundPreload{error,calls}: SoundResult{0,0n,False{},error,sound_fill(entries,0n),calls,0,0n}
def sound_from_choice(entries: List<&2,SoundEntry>,+total: U32,choice: SoundChoice) -> SoundResult:
  match choice:
    case SoundChoice{+selected,calls}: SoundResult{total,selected,Nat.is_eq(selected,0n),0n,calls,sound_fill(entries,0n),total,1n}
def sound_run_total(+operation: Nat,+entries: List<&2,SoundEntry>,draw: U32,+total: U32) -> SoundResult:
  Bool.pick(SoundResult,Nat.is_eq(operation,0n),SoundResult{total,0n,False{},0n,sound_fill(entries,1n),sound_fill(entries,0n),0,0n},
    Bool.pick(SoundResult,U32.is_zero(total),SoundResult{total,0n,True{},0n,sound_fill(entries,1n),sound_fill(entries,0n),0,0n},
      Bool.pick(SoundResult,J.jw_negative(total),SoundResult{total,0n,False{},1n,sound_fill(entries,1n),sound_fill(entries,0n),total,1n},
        sound_from_choice(entries,total,sound_traverse(entries,draw,1n)))))
def sound_run(+operation: Nat,+entries: List<&2,SoundEntry>,draw: U32) -> SoundResult:
  Bool.pick(SoundResult,Nat.is_eq(operation,2n),sound_from_preload(entries,sound_preload(entries)),sound_run_total(operation,entries,draw,sound_sum(entries)))
def sound_counts(xs: List<&2,Nat>) -> String:
  match xs:
    case Nil{}: ""
    case Con{head,tail}: ":" ++ Nat.show(head) ++ sound_counts(tail)
def sound_bit(value: Bool) -> Nat:
  Bool.pick(Nat,value,1n,0n)
def sound_render(result: SoundResult) -> String:
  match result:
    case SoundResult{weight,selected,fallback,error,w,p,bound,random}:
      U32.show(weight) ++ ":" ++ Nat.show(selected) ++ ":" ++ Nat.show(sound_bit(fallback)) ++ ":" ++ Nat.show(error) ++ ":" ++ U32.show(bound) ++ ":" ++ Nat.show(random) ++ sound_counts(w) ++ sound_counts(p)

law sound_empty_fallback:
  {sound_render(sound_run(1n,Nil{},0)) == "0:0:1:0:0:0" : String}
def sound_empty_fallback():
  {==}
law sound_overflow_invalid_bound:
  {sound_render(sound_run(1n,Con{SoundEntry{2147483647,2147483647,False{}},Con{SoundEntry{1,1,False{}},Nil{}}},0)) == "2147483648:0:0:1:2147483648:1:1:1:0:0" : String}
def sound_overflow_invalid_bound():
  {==}
law sound_live_shrink_fallback:
  {sound_render(sound_run(1n,Con{SoundEntry{3,0,False{}},Con{SoundEntry{2,0,False{}},Nil{}}},0)) == "5:0:1:0:5:1:2:2:0:0" : String}
def sound_live_shrink_fallback():
  {==}
law sound_zero_can_later_select:
  {sound_render(sound_run(1n,Con{SoundEntry{0,5,False{}},Con{SoundEntry{2,2,False{}},Nil{}}},1)) == "2:1:0:0:2:1:2:1:0:0" : String}
def sound_zero_can_later_select():
  {==}
law sound_preload_zero_weight:
  {sound_render(sound_run(2n,Con{SoundEntry{0,0,False{}},Nil{}},0)) == "0:0:0:0:0:0:0:1" : String}
def sound_preload_zero_weight():
  {==}
law sound_preload_partial:
  {sound_render(sound_run(2n,Con{SoundEntry{1,1,False{}},Con{SoundEntry{2,2,True{}},Con{SoundEntry{3,3,False{}},Nil{}}}},0)) == "0:0:0:2:0:0:0:0:0:1:1:0" : String}
def sound_preload_partial():
  {==}
