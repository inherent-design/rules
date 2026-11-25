import Base
def linkfs_same(fs: Bool,node: Bool) -> Bool:
  Bool.and(fs,node)
def linkfs_exists(absolute: Bool,registered: Bool) -> Bool:
  Bool.and(absolute,registered)
def linkfs_read(registered: Bool,+backing: Nat) -> Nat:
  Bool.pick(Nat,Bool.and(registered,Bool.not(Nat.is_eq(backing,0n))),Bool.pick(Nat,Nat.is_eq(backing,1n),3n,4n),0n)
def linkfs_evaluate(+kind: Nat,fs: Bool,node: Bool,absolute: Bool,+registered: Bool,mapped: Bool,backing: Nat) -> Nat:
  Bool.pick(Nat,Nat.is_eq(kind,0n),2n,
    Bool.pick(Nat,Nat.is_eq(kind,1n),Bool.pick(Nat,linkfs_same(fs,node),2n,1n),
      Bool.pick(Nat,Nat.is_eq(kind,2n),Bool.pick(Nat,linkfs_exists(absolute,registered),2n,1n),
        Bool.pick(Nat,Nat.is_eq(kind,3n),linkfs_read(mapped,backing),
          Bool.pick(Nat,Nat.is_eq(kind,4n),Bool.pick(Nat,registered,5n,0n),Bool.pick(Nat,Nat.is_eq(kind,5n),6n,0n))))))
law linkfs_other_scope:
  for node: Bool
  {linkfs_same(False{},node) == False{} : Bool}
def linkfs_other_scope(node):
  {==}
law linkfs_distinct_nodes:
  for fs: Bool
  {linkfs_same(fs,False{}) == False{} : Bool}
def linkfs_distinct_nodes(fs):
  match fs:
    case False{}: {==}
    case True{}: {==}
law linkfs_relative_entry_not_existing:
  {linkfs_exists(False{},True{}) == False{} : Bool}
def linkfs_relative_entry_not_existing():
  {==}
law linkfs_relative_read_can_succeed:
  {linkfs_read(True{},1n) == 3n : Nat}
def linkfs_relative_read_can_succeed():
  {==}
law linkfs_entry_can_outlive_backing:
  {linkfs_exists(True{},True{}) == True{} : Bool}
def linkfs_entry_can_outlive_backing():
  {==}
law linkfs_missing_backing_refuses:
  {linkfs_read(True{},0n) == 0n : Nat}
def linkfs_missing_backing_refuses():
  {==}
law linkfs_changed_backing_visible:
  {linkfs_read(True{},2n) == 4n : Nat}
def linkfs_changed_backing_visible():
  {==}
law linkfs_close_does_not_revoke:
  {linkfs_evaluate(0n,False{},False{},False{},False{},False{},0n) == 2n : Nat}
def linkfs_close_does_not_revoke():
  {==}
law linkfs_write_open_refused:
  {linkfs_evaluate(5n,False{},False{},True{},True{},False{},1n) == 6n : Nat}
def linkfs_write_open_refused():
  {==}
