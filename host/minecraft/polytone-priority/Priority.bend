import Base

type Item is Data:
  Item{key: Nat,enabled: Bool,rank: Nat,marker: Nat}
type State is Data:
  State{items: List<&2,Item>,warnings: Nat}

def key(item: Item) -> Nat:
  match item:
    case Item{k,_,_,_}: k
def rank(item: Item) -> Nat:
  match item:
    case Item{_,_,r,_}: r
def replaces(old: Item,candidate: Item) -> Bool:
  match old candidate:
    case Item{_,_,a,_} Item{_,enabled,b,_}: Bool.and(enabled,Nat.is_gt(b,a))
def put(items: List<&2,Item>,+candidate: Item) -> List<&2,Item>:
  match items:
    case Nil{}: Con{candidate,Nil{}}
    case Con{+head,+rest}:
      Bool.pick(List<&2,Item>,Nat.is_eq(key(head),key(candidate)),Con{Bool.pick(Item,replaces(head,candidate),candidate,head),rest},Con{head,put(rest,candidate)})
def replacement(items: List<&2,Item>,+candidate: Item) -> Bool:
  match items:
    case Nil{}: False{}
    case Con{+head,+rest}: Bool.pick(Bool,Nat.is_eq(key(head),key(candidate)),replaces(head,candidate),replacement(rest,candidate))
def step(s: State,+candidate: Item) -> State:
  match s:
    case State{+items,warnings}: State{put(items,candidate),Nat.add(warnings,Bool.pick(Nat,replacement(items,candidate),1n,0n))}
def run_go(items: List<&2,Item>,s: State) -> State:
  match items:
    case Nil{}: s
    case Con{head,rest}: run_go(rest,step(s,head))
def run(items: List<&2,Item>) -> State:
  run_go(items,State{Nil{},0n})
def ordered_insert(+item: Item,items: List<&2,Item>) -> List<&2,Item>:
  match items:
    case Nil{}: Con{item,Nil{}}
    case Con{+head,+rest}: Bool.pick(List<&2,Item>,Bool.not(Nat.is_gt(rank(item),rank(head))),Con{item,Con{head,rest}},Con{head,ordered_insert(item,rest)})
def ordered(items: List<&2,Item>) -> List<&2,Item>:
  match items:
    case Nil{}: Nil{}
    case Con{head,rest}: ordered_insert(head,ordered(rest))

law first_disabled_retained:
  {put(Nil{},Item{0n,False{},2n,1n}) == Con{Item{0n,False{},2n,1n},Nil{}} : List<&2,Item>}
def first_disabled_retained():
  {==}
law disabled_does_not_replace:
  {put(Con{Item{0n,True{},0n,1n},Nil{}},Item{0n,False{},2n,2n}) == Con{Item{0n,True{},0n,1n},Nil{}} : List<&2,Item>}
def disabled_does_not_replace():
  {==}
law equal_rank_does_not_replace:
  {replaces(Item{0n,True{},1n,1n},Item{0n,True{},1n,2n}) == False{} : Bool}
def equal_rank_does_not_replace():
  {==}
law higher_enabled_replaces:
  {replaces(Item{0n,False{},0n,1n},Item{0n,True{},1n,2n}) == True{} : Bool}
def higher_enabled_replaces():
  {==}
law disabled_high_stays:
  {put(Con{Item{0n,False{},2n,1n},Nil{}},Item{0n,True{},1n,2n}) == Con{Item{0n,False{},2n,1n},Nil{}} : List<&2,Item>}
def disabled_high_stays():
  {==}
law sorted_differs_from_insertion:
  {ordered(Con{Item{0n,True{},2n,1n},Con{Item{1n,True{},0n,2n},Nil{}}}) == Con{Item{1n,True{},0n,2n},Con{Item{0n,True{},2n,1n},Nil{}}} : List<&2,Item>}
def sorted_differs_from_insertion():
  {==}
law ties_keep_input_order:
  {ordered(Con{Item{1n,True{},1n,2n},Con{Item{0n,True{},1n,1n},Nil{}}}) == Con{Item{1n,True{},1n,2n},Con{Item{0n,True{},1n,1n},Nil{}}} : List<&2,Item>}
def ties_keep_input_order():
  {==}
