import Base

# One successfully allocated2x2 CPUimage. Pure retainedwords are historical data,
# not a native address, byte-order conversion, or permission after close.
type ImageState is Data:
  State{closed: Bool,words: List<&2,U32>}
type ImageReply is Data:
  Reply{state: ImageState,error: Nat,word: List<&2,U32>}
def image_initial() -> ImageState:
  State{False{},[0,0,0,0]}
def image_inside(+x: Nat,+y: Nat) -> Bool:
  Bool.and(Bool.or(Nat.is_eq(x,1n),Nat.is_eq(x,2n)),Bool.or(Nat.is_eq(y,1n),Nat.is_eq(y,2n)))
def image_index(x: Nat,y: Nat) -> Nat:
  Nat.add(Nat.mul(Nat.sub(y,1n),2n),Nat.sub(x,1n))
def image_set(words: List<&2,U32>,+index: Nat,+value: U32) -> List<&2,U32>:
  match words:
    case Nil{}: []
    case +head <> +tail:
      Bool.pick(List<&2,U32>,Nat.is_eq(index,0n),value <> tail,head <> image_set(tail,Nat.sub(index,1n),value))
def image_get(words: List<&2,U32>,+index: Nat) -> U32:
  match words:
    case Nil{}: 0
    case head <> tail:
      Bool.pick(U32,Nat.is_eq(index,0n),head,image_get(tail,Nat.sub(index,1n)))
def image_step(state: ImageState,+operation: Nat,+x: Nat,+y: Nat,word: U32) -> ImageReply:
  match state:
    case State{+closed,+words}:
      live=Bool.pick(ImageReply,Nat.is_eq(operation,1n),Reply{State{closed,words},0n,[image_get(words,image_index(x,y))]},Reply{State{closed,image_set(words,image_index(x,y),word)},0n,[]})
      access=Bool.pick(ImageReply,image_inside(x,y),Bool.pick(ImageReply,closed,Reply{State{closed,words},2n,[]},live),Reply{State{closed,words},1n,[]})
      meta=Bool.pick(ImageReply,Nat.is_eq(operation,4n),Reply{State{closed,words},0n,[]},access)
      shut=Bool.pick(ImageReply,Nat.is_eq(operation,3n),Reply{State{True{},words},0n,[]},meta)
      Bool.pick(ImageReply,Nat.is_eq(operation,0n),Reply{image_initial(),0n,[]},shut)
def image_error(reply: ImageReply) -> Nat:
  match reply:
    case Reply{state,error,word}: error
def image_state(reply: ImageReply) -> ImageState:
  match reply:
    case Reply{state,error,word}: state

law zero_initial:
  {image_initial() == State{False{},[0,0,0,0]} : ImageState}
def zero_initial():
  {==}
law close_preserves_history:
  {image_state(image_step(State{False{},[1,2,3,4]},3n,0n,0n,0)) == State{True{},[1,2,3,4]} : ImageState}
def close_preserves_history():
  {==}
law repeat_close:
  {image_state(image_step(State{True{},[1,2,3,4]},3n,0n,0n,0)) == State{True{},[1,2,3,4]} : ImageState}
def repeat_close():
  {==}
law metadata_not_reopen:
  {image_state(image_step(State{True{},[1,2,3,4]},4n,0n,0n,0)) == State{True{},[1,2,3,4]} : ImageState}
def metadata_not_reopen():
  {==}
law closed_valid_get:
  {image_error(image_step(State{True{},[1,2,3,4]},1n,1n,1n,0)) == 2n : Nat}
def closed_valid_get():
  {==}
law closed_set_refuses:
  {image_step(State{True{},[1,2,3,4]},2n,1n,1n,9) == Reply{State{True{},[1,2,3,4]},2n,[]} : ImageReply}
def closed_set_refuses():
  {==}
law bounds_precedes_closed:
  {image_error(image_step(State{True{},[1,2,3,4]},1n,3n,1n,0)) == 1n : Nat}
def bounds_precedes_closed():
  {==}
law write_one_cell:
  {image_step(image_initial(),2n,2n,1n,2309737967) == Reply{State{False{},[0,2309737967,0,0]},0n,[]} : ImageReply}
def write_one_cell():
  {==}
law get_written_word:
  {image_step(State{False{},[0,2309737967,0,0]},1n,2n,1n,0) == Reply{State{False{},[0,2309737967,0,0]},0n,[2309737967]} : ImageReply}
def get_written_word():
  {==}
