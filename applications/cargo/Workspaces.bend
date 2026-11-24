import Base

type Scope is Data:
  Empty{}
  Root{}
  A{}
  B{}
  AB{}
  RootA{}
  RootAB{}

type Request is Data:
  Default{}
  WorkspaceExcludeB{}
  ExplicitA{}
  InvalidExclude{}

def defaults(root: Bool, explicit_a: Bool, member_b: Bool) -> Scope:
  Bool.pick(Scope,member_b,B{},Bool.pick(Scope,explicit_a,A{},Bool.pick(Scope,root,Root{},AB{})))

def selected(root: Bool, explicit_a: Bool, member_b: Bool, request: Request) -> Scope:
  match request:
    case Default{}: defaults(root,explicit_a,member_b)
    case WorkspaceExcludeB{}: Bool.pick(Scope,root,RootA{},A{})
    case ExplicitA{}: A{}
    case InvalidExclude{}: Empty{}

def checked(scope: Scope) -> Scope:
  match scope:
    case Empty{}: Empty{}
    case Root{}: Root{}
    case A{}: AB{}
    case B{}: B{}
    case AB{}: AB{}
    case RootA{}: RootAB{}
    case RootAB{}: RootAB{}

def label(scope: Scope) -> String:
  match scope:
    case Empty{}: ""
    case Root{}: "0"
    case A{}: "1"
    case B{}: "2"
    case AB{}: "1,2"
    case RootA{}: "0,1"
    case RootAB{}: "0,1,2"

law member_context_wins:
  for root: Bool
  for explicit_a: Bool
  {defaults(root,explicit_a,True{}) == B{} : Scope}
def member_context_wins(root,explicit_a):
  {==}

law explicit_defaults_wins_at_root:
  for root: Bool
  {defaults(root,True{},False{}) == A{} : Scope}
def explicit_defaults_wins_at_root(root):
  {==}

law exclusion_does_not_erase_dependency:
  {checked(selected(False{},False{},False{},WorkspaceExcludeB{})) == AB{} : Scope}
def exclusion_does_not_erase_dependency():
  {==}

law explicit_a_requires_b:
  for root: Bool
  for explicit_a: Bool
  for member_b: Bool
  {checked(selected(root,explicit_a,member_b,ExplicitA{})) == AB{} : Scope}
def explicit_a_requires_b(root,explicit_a,member_b):
  {==}

def main() -> IO(Unit):
  IO.print("Request roots,effective default context,and dependency closure for the selected Cargo workspace profile.")
