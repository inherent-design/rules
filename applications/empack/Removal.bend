import Base

type EvidenceNode is Data:
  EvidenceNode{key: Nat, complete: Bool, requires: List<&2, Nat>}

def has(keys: List<&2, Nat>, +key: Nat) -> Bool:
  match keys:
    case Nil{}: False{}
    case Con{head,tail}: Bool.or(Nat.is_eq(head,key),has(tail,key))

def exists(nodes: List<&2, EvidenceNode>, +key: Nat) -> Bool:
  match nodes:
    case Nil{}: False{}
    case Con{EvidenceNode{id,complete,requires},rest}: Bool.or(Nat.is_eq(id,key),exists(rest,key))

# Codes distinguish the source's first selection error and evidence priority.
# 0=admitted,1=unknown,2=duplicate,3=not-root,4=required,5=incomplete.
def selection_error(+nodes: List<&2, EvidenceNode>, +roots: List<&2, Nat>, selection: List<&2, Nat>, +seen: List<&2, Nat>, +forget: Bool) -> Nat:
  match selection:
    case Nil{}: 0n
    case Con{+head,tail}:
      Bool.pick(Nat,Bool.not(exists(nodes,head)),1n,
        Bool.pick(Nat,has(seen,head),2n,
          Bool.pick(Nat,Bool.and(forget,Bool.not(has(roots,head))),3n,
            selection_error(nodes,roots,tail,Con{head,seen},forget))))

def intersects(edges: List<&2, Nat>, +selected: List<&2, Nat>) -> Bool:
  match edges:
    case Nil{}: False{}
    case Con{head,tail}: Bool.or(has(selected,head),intersects(tail,selected))

def retained_evidence(nodes: List<&2, EvidenceNode>, +selection: List<&2, Nat>, +known: Bool) -> Bool:
  match nodes:
    case Nil{}: False{}
    case Con{EvidenceNode{key,complete,requires},rest}:
      issue = Bool.pick(Bool,known,intersects(requires,selection),Bool.not(complete))
      Bool.or(Bool.and(Bool.not(has(selection,key)),issue),retained_evidence(rest,selection,known))

def after_selection(+code: Nat, +nodes: List<&2, EvidenceNode>, +selection: List<&2, Nat>, forget: Bool, acknowledge: Bool) -> Nat:
  Bool.pick(Nat,Bool.not(Nat.is_eq(code,0n)),code,
    Bool.pick(Nat,forget,0n,
      Bool.pick(Nat,retained_evidence(nodes,selection,True{}),4n,
        Bool.pick(Nat,Bool.and(retained_evidence(nodes,selection,False{}),Bool.not(acknowledge)),5n,0n))))

def decide(+nodes: List<&2, EvidenceNode>, roots: List<&2, Nat>, +selection: List<&2, Nat>, +forget: Bool, acknowledge: Bool) -> Nat:
  after_selection(selection_error(nodes,roots,selection,Nil{},forget),nodes,selection,forget,acknowledge)

# Exact unchanged A->B request profile only. 0=add,1=adopt,2=update.
def merge_error(+exists: Bool, operation: Nat) -> Nat:
  Bool.pick(Nat,Bool.and(Nat.is_eq(operation,2n),Bool.not(exists)),6n,0n)
def merge_root(+exists: Bool, +operation: Nat) -> Bool:
  Bool.or(Nat.is_eq(operation,0n),Bool.and(Nat.is_eq(operation,1n),Bool.not(exists)))

def base() -> List<&2, EvidenceNode>:
  Con{EvidenceNode{1n,True{},Con{2n,Nil{}}},Con{EvidenceNode{2n,True{},Nil{}},Con{EvidenceNode{3n,True{},Nil{}},Nil{}}}}

law demotion_keeps_required_content:
  {decide(base(),Con{1n,Nil{}},Con{1n,Nil{}},True{},False{}) == 0n : Nat}
def demotion_keeps_required_content():
  {==}
law transitive_cannot_be_forgotten:
  {decide(base(),Con{1n,Nil{}},Con{2n,Nil{}},True{},False{}) == 3n : Nat}
def transitive_cannot_be_forgotten():
  {==}
law acknowledgement_does_not_override_requirement:
  {decide(base(),Con{1n,Nil{}},Con{2n,Nil{}},False{},True{}) == 4n : Nat}
def acknowledgement_does_not_override_requirement():
  {==}
law unknown_blocks_content_removal:
  {decide(Con{EvidenceNode{1n,True{},Nil{}},Con{EvidenceNode{3n,False{},Nil{}},Nil{}}},Con{1n,Nil{}},Con{1n,Nil{}},False{},False{}) == 5n : Nat}
def unknown_blocks_content_removal():
  {==}
law selected_unknown_is_not_retained:
  {decide(Con{EvidenceNode{1n,False{},Nil{}},Nil{}},Con{1n,Nil{}},Con{1n,Nil{}},False{},False{}) == 0n : Nat}
def selected_unknown_is_not_retained():
  {==}
law duplicate_is_not_an_empty_change:
  {decide(base(),Con{1n,Nil{}},Con{1n,Con{1n,Nil{}}},False{},False{}) == 2n : Nat}
def duplicate_is_not_an_empty_change():
  {==}
law add_can_promote_unchanged_retained_selection:
  {merge_root(True{},0n) == True{} : Bool}
def add_can_promote_unchanged_retained_selection():
  {==}
law adoption_preserves_existing_nonroot:
  {merge_root(True{},1n) == False{} : Bool}
def adoption_preserves_existing_nonroot():
  {==}
law update_cannot_install_missing_identity:
  {merge_error(False{},2n) == 6n : Nat}
def update_cannot_install_missing_identity():
  {==}
