import Base

type SpriteState is Data:
  SpriteState{known: Bool,bound: List<&2,Nat>,inputKnown: Bool,input: List<&2,Nat>}
type SpriteAction is Data:
  SpriteAction{kind: Nat,values: List<&2,Nat>,iNeg: Bool,i: Nat,mNeg: Bool,m: Nat,value: Nat}
type SpriteChoice is Data:
  SpriteChoice{code: Nat,selected: Nat}
type SpriteOutcome is Data:
  SpriteOutcome{state: SpriteState,code: Nat,selected: Nat}
def sprite_empty() -> SpriteState:
  SpriteState{False{},Nil{},False{},Nil{}}
def sprite_null(xs: List<&2,Nat>) -> Bool:
  match xs:
    case Nil{}: False{}
    case Con{head,tail}: Bool.or(Nat.is_eq(head,0n),sprite_null(tail))
def sprite_at(xs: List<&2,Nat>,+i: Nat) -> Nat:
  match xs:
    case Nil{}: 0n
    case Con{head,tail}: Bool.pick(Nat,Nat.is_eq(i,0n),head,sprite_at(tail,Nat.sub(i,1n)))
def sprite_replace(xs: List<&2,Nat>,+i: Nat,+v: Nat) -> List<&2,Nat>:
  match xs:
    case Nil{}: Nil{}
    case Con{+head,+tail}: Bool.pick(List<&2,Nat>,Nat.is_eq(i,0n),Con{v,tail},Con{head,sprite_replace(tail,Nat.sub(i,1n),v)})
def sprite_index(+xs: List<&2,Nat>,+negative: Bool,+index: Nat) -> SpriteChoice:
  Bool.pick(SpriteChoice,Bool.or(Bool.and(negative,Nat.is_ne(index,0n)),Nat.is_ge(index,List.length(&2,Nat,xs))),SpriteChoice{3n,0n},SpriteChoice{0n,sprite_at(xs,index)})
def sprite_choice(+xs: List<&2,Nat>,known: Bool,first: Bool,iNeg: Bool,i: Nat,mNeg: Bool,+m: Nat) -> SpriteChoice:
  Bool.pick(SpriteChoice,Bool.not(known),SpriteChoice{1n,0n},
    Bool.pick(SpriteChoice,first,
      Bool.pick(SpriteChoice,Nat.is_eq(List.length(&2,Nat,xs),0n),SpriteChoice{4n,0n},SpriteChoice{0n,sprite_at(xs,0n)}),
      Bool.pick(SpriteChoice,Nat.is_eq(m,0n),SpriteChoice{2n,0n},
        sprite_index(xs,Bool.xor(iNeg,mNeg),Nat.div(Nat.mul(i,Nat.sub(List.length(&2,Nat,xs),1n)),m)))))
def sprite_read(s: SpriteState,c: SpriteChoice) -> SpriteOutcome:
  match c:
    case SpriteChoice{code,selected}: SpriteOutcome{s,code,selected}
def sprite_step(s: SpriteState,a: SpriteAction) -> SpriteOutcome:
  match s:
    case SpriteState{+known,+bound,+inputKnown,+input}:
      match a:
        case SpriteAction{kind,+values,iNeg,+i,mNeg,m,value}:
          match kind:
            case 0n:
              Bool.pick(SpriteOutcome,sprite_null(values),SpriteOutcome{SpriteState{known,bound,True{},values},1n,0n},SpriteOutcome{SpriteState{True{},values,True{},values},0n,0n})
            case 1n: SpriteOutcome{SpriteState{known,bound,False{},Nil{}},1n,0n}
            case 2n: SpriteOutcome{SpriteState{known,bound,inputKnown,sprite_replace(input,i,value)},0n,0n}
            case _: sprite_read(SpriteState{known,bound,inputKnown,input},sprite_choice(bound,known,Nat.is_eq(kind,4n),iNeg,i,mNeg,m))
def sprite_state(o: SpriteOutcome) -> SpriteState:
  match o:
    case SpriteOutcome{s,_,_}: s
def sprite_list(xs: List<&2,Nat>) -> String:
  match xs:
    case Nil{}: ""
    case Con{head,tail}: ":" ++ Nat.show(head) ++ sprite_list(tail)
def sprite_bit(b: Bool) -> Nat:
  Bool.pick(Nat,b,1n,0n)
def sprite_render(o: SpriteOutcome) -> String:
  match o:
    case SpriteOutcome{SpriteState{known,+bound,inputKnown,+input},code,selected}:
      Nat.show(code) ++ ":" ++ Nat.show(selected) ++ ":" ++ Nat.show(sprite_bit(known)) ++ ":" ++ Nat.show(List.length(&2,Nat,bound)) ++ ":" ++ Nat.show(sprite_bit(inputKnown)) ++ ":" ++ Nat.show(List.length(&2,Nat,input)) ++ sprite_list(bound) ++ ":9" ++ sprite_list(input)
def sprite_program(actions: List<&2,SpriteAction>,+s: SpriteState) -> String:
  match actions:
    case Nil{}: ""
    case Con{a,tail}:
      +out=sprite_step(s,a)
      sprite_render(out) ++ "\n" ++ sprite_program(tail,sprite_state(out))

law sprite_unbound_refuses:
  {sprite_choice(Nil{},False{},False{},False{},0n,False{},1n) == SpriteChoice{1n,0n} : SpriteChoice}
def sprite_unbound_refuses():
  {==}
law sprite_empty_bind_admitted:
  {sprite_render(sprite_step(sprite_empty(),SpriteAction{0n,Nil{},False{},0n,False{},1n,0n})) == "0:0:1:0:1:0:9" : String}
def sprite_empty_bind_admitted():
  {==}
law sprite_null_bind_preserves:
  {sprite_render(sprite_step(SpriteState{True{},Con{1n,Con{2n,Nil{}}},True{},Nil{}},SpriteAction{0n,Con{0n,Nil{}},False{},0n,False{},1n,0n})) == "1:0:1:2:1:1:1:2:9:0" : String}
def sprite_null_bind_preserves():
  {==}
law sprite_input_mutation_is_separate:
  {sprite_render(sprite_step(SpriteState{True{},Con{1n,Con{2n,Nil{}}},True{},Con{1n,Con{2n,Nil{}}}},SpriteAction{2n,Nil{},False{},0n,False{},1n,3n})) == "0:0:1:2:1:2:1:2:9:3:2" : String}
def sprite_input_mutation_is_separate():
  {==}
law sprite_negative_fraction_selects_first:
  {sprite_choice(Con{1n,Con{2n,Con{3n,Nil{}}}},True{},False{},True{},1n,False{},3n) == SpriteChoice{0n,1n} : SpriteChoice}
def sprite_negative_fraction_selects_first():
  {==}
law sprite_zero_denominator_refuses:
  {sprite_choice(Con{3n,Nil{}},True{},False{},False{},0n,False{},0n) == SpriteChoice{2n,0n} : SpriteChoice}
def sprite_zero_denominator_refuses():
  {==}
law sprite_empty_first_refuses:
  {sprite_choice(Nil{},True{},True{},False{},0n,False{},1n) == SpriteChoice{4n,0n} : SpriteChoice}
def sprite_empty_first_refuses():
  {==}
law sprite_singleton_frame:
  {sprite_choice(Con{3n,Nil{}},True{},False{},True{},3n,False{},1n) == SpriteChoice{0n,3n} : SpriteChoice}
def sprite_singleton_frame():
  {==}
