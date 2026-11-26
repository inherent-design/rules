import Base
import ../java/CpuImage.bend as C

# Explicit FrameSize+empty metadata. Mask bits label initialized all-zero/all-one
# pixel words; no image decoder,color conversion,native pointer or tick model.
def sprite_frames(masks: List<&2,U32>) -> List<&2,Nat>:
  Bool.pick(List<&2,Nat>,Nat.is_eq(List.length(&2,U32,masks),1n),[1n],[0n,1n])
def mask_at(masks: List<&2,U32>,+frame: Nat) -> U32:
  match masks:
    case Nil{}: 0
    case +head <> +tail:
      Bool.pick(U32,Bool.or(List.is_empty(&2,U32,tail),Nat.is_eq(frame,0n)),head,mask_at(tail,Nat.sub(frame,1n)))
def sprite_transparent(mask: U32,index: Nat) -> Bool:
  U32.is_zero(U32.and(U32.shrn(mask,index),1))
def sprite_map(indices: List<&2,Nat>,+mask: U32) -> List<&2,Bool>:
  match indices:
    case Nil{}: []
    case head <> tail: sprite_transparent(mask,head) <> sprite_map(tail,mask)
def sprite_cells(+width: Nat,mask: U32) -> List<&2,Bool>:
  sprite_map(Bool.pick(List<&2,Nat>,Nat.is_eq(width,3n),[0n,1n,2n,3n,4n,5n],[0n,1n,2n,3n]),mask)
def alias_mutated() -> C.ImageState:
  C.image_state(C.image_step(C.image_initial(),2n,1n,1n,4294967295))
def alias_closed() -> C.ImageState:
  C.image_state(C.image_step(alias_mutated(),3n,0n,0n,0))
def alias_first_transparent(state: C.ImageState) -> Bool:
  match state:
    case C.State{closed,words}: U32.is_zero(U32.shrn(C.image_get(words,0n),24n))
def alias_before_transparent() -> Bool:
  alias_first_transparent(C.image_initial())
def alias_after_transparent() -> Bool:
  alias_first_transparent(alias_mutated())
def alias_closed_error() -> Nat:
  C.image_error(C.image_step(alias_closed(),1n,1n,1n,0))

law singleton_label_one:
  {sprite_frames([0]) == [1n] : List<&2,Nat>}
def singleton_label_one():
  {==}
law singleton_label_not_backing_index:
  {mask_at([5],1n) == 5 : U32}
def singleton_label_not_backing_index():
  {==}
law two_frame_labels:
  {sprite_frames([1,8]) == [0n,1n] : List<&2,Nat>}
def two_frame_labels():
  {==}
law first_frame:
  {mask_at([1,8],0n) == 1 : U32}
def first_frame():
  {==}
law second_frame:
  {mask_at([1,8],1n) == 8 : U32}
def second_frame():
  {==}
law empty_pixels_transparent:
  {sprite_cells(2n,0) == [True{},True{},True{},True{}] : List<&2,Bool>}
def empty_pixels_transparent():
  {==}
law opaque_pixels:
  {sprite_cells(2n,15) == [False{},False{},False{},False{}] : List<&2,Bool>}
def opaque_pixels():
  {==}
law three_columns_preserved:
  {sprite_cells(3n,5) == [False{},True{},False{},True{},True{},True{}] : List<&2,Bool>}
def three_columns_preserved():
  {==}
law alias_closed_refuses:
  {alias_closed_error() == 2n : Nat}
def alias_closed_refuses():
  {==}
law alias_before_write:
  {alias_first_transparent(C.image_initial()) == True{} : Bool}
def alias_before_write():
  {==}
law alias_after_write:
  {alias_first_transparent(alias_mutated()) == False{} : Bool}
def alias_after_write():
  {==}
