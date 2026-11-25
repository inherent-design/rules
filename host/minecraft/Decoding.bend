import Base

def metadata(description: Bool, number: Bool) -> Bool:
  Bool.and(description,number)
def optional_range(present: Bool, valid: Bool) -> Bool:
  Bool.and(present,valid)
def identifier(namespace: Bool, path: Bool) -> Bool:
  Bool.and(namespace,path)
def le(a: Nat, b: Nat) -> Bool:
  Bool.not(Nat.is_gt(a,b))

def positive(n: Nat) -> Bool:
  Bool.not(Nat.is_eq(n,0n))
def less(+a: Nat, +b: Nat) -> Bool:
  Bool.and(le(a,b),Bool.not(Nat.is_eq(a,b)))
def gui(+kind: Nat, +width: Nat, +height: Nat, +left: Nat, top: Nat, right: Nat, bottom: Nat, scalar: Bool) -> Bool:
  Bool.pick(Bool,Nat.is_eq(kind,0n),True{},Bool.pick(Bool,Nat.is_eq(kind,1n),Bool.and(positive(width),positive(height)),Bool.and(Nat.is_eq(kind,2n),Bool.and(Bool.and(positive(width),positive(height)),Bool.and(Bool.or(Bool.not(scalar),positive(left)),Bool.and(less(Nat.add(left,right),width),less(Nat.add(top,bottom),height)))))))
def animation(successor: Bool, dimensions: Bool, times: Bool, negative_primitive: Bool, negative_object: Bool) -> Bool:
  Bool.and(dimensions,Bool.and(times,Bool.and(Bool.not(negative_object),Bool.or(Bool.not(successor),Bool.not(negative_primitive)))))
def boolean_shape(successor: Bool, shape: Nat) -> Bool:
  Bool.or(Bool.not(successor),le(shape,2n))
def boolean_value(+shape: Nat) -> Bool:
  Bool.or(Nat.is_eq(shape,2n),Nat.is_eq(shape,5n))
def texture(+successor: Bool, blur: Nat, clamp: Nat) -> Bool:
  Bool.and(boolean_shape(successor,blur),boolean_shape(successor,clamp))
def texture_value(blur: Nat, clamp: Nat) -> Nat:
  Nat.add(Bool.pick(Nat,boolean_value(blur),1n,0n),Bool.pick(Nat,boolean_value(clamp),2n,0n))
def angle(+twice_absolute: Nat) -> Bool:
  Bool.or(Nat.is_eq(twice_absolute,0n),Bool.or(Nat.is_eq(twice_absolute,45n),Nat.is_eq(twice_absolute,90n)))
def geometry(negative_extent: Nat, positive_extent: Nat, twice_angle: Nat, shape: Bool, axis: Bool) -> Bool:
  Bool.and(shape,Bool.and(axis,Bool.and(le(negative_extent,16n),Bool.and(le(positive_extent,32n),angle(twice_angle)))))
def equipment(known: Bool, groups: Nat, smallest_group: Nat) -> Bool:
  Bool.and(known,Bool.and(positive(groups),positive(smallest_group)))
def post_target(width: Nat, height: Nat) -> Nat:
  Bool.pick(Nat,Bool.and(positive(width),positive(height)),2n,1n)
def usable(decoded: Bool, references: Bool, context: Bool, prepared: Bool, published: Bool) -> Bool:
  Bool.and(decoded,Bool.and(references,Bool.and(context,Bool.and(prepared,published))))

law invalid_optional_range_is_absent:
  {optional_range(True{},False{}) == False{} : Bool}
def invalid_optional_range_is_absent():
  {==}
law scalar_zero_border_refused:
  {gui(2n,8n,8n,0n,0n,0n,0n,True{}) == False{} : Bool}
def scalar_zero_border_refused():
  {==}
law record_zero_border_accepted:
  {gui(2n,8n,8n,0n,0n,0n,0n,False{}) == True{} : Bool}
def record_zero_border_accepted():
  {==}
law legacy_negative_primitive_accepted:
  {animation(False{},True{},True{},True{},False{}) == True{} : Bool}
def legacy_negative_primitive_accepted():
  {==}
law successor_negative_primitive_refused:
  {animation(True{},True{},True{},True{},False{}) == False{} : Bool}
def successor_negative_primitive_refused():
  {==}
law legacy_boolean_coercion:
  {texture(False{},3n,5n) == True{} : Bool}
def legacy_boolean_coercion():
  {==}
law successor_boolean_coercion_refused:
  {texture(True{},3n,0n) == False{} : Bool}
def successor_boolean_coercion_refused():
  {==}
law arbitrary_scalar_refused:
  {geometry(0n,16n,122n,True{},True{}) == False{} : Bool}
def arbitrary_scalar_refused():
  {==}
law empty_equipment_refused:
  {equipment(True{},0n,0n) == False{} : Bool}
def empty_equipment_refused():
  {==}
law invalid_fixed_falls_back:
  {post_target(0n,16n) == 1n : Nat}
def invalid_fixed_falls_back():
  {==}
law parser_does_not_imply_consumer:
  {usable(True{},False{},True{},True{},True{}) == False{} : Bool}
def parser_does_not_imply_consumer():
  {==}
