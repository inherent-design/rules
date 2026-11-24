import Base

type Roots is Data:
  Roots{parent: Bool, leaf: Bool}

type Profile is Data:
  Npm{}
  Pnpm{}
  Yarn{}

type Action is Data:
  RemoveLeaf{}
  AddLeaf{}
  RemoveParent{}

def live_leaf(roots: Roots) -> Bool:
  match roots:
    case Roots{parent, leaf}: Bool.or(parent, leaf)

def root_can_load_leaf(profile: Profile, roots: Roots) -> Bool:
  match profile:
    case Npm{}: live_leaf(roots)
    case Pnpm{}:
      match roots:
        case Roots{parent, leaf}: leaf
    case Yarn{}: live_leaf(roots)

def accepts_missing_root(profile: Profile) -> Bool:
  match profile:
    case Npm{}: True{}
    case Pnpm{}: False{}
    case Yarn{}: False{}

def accepted(roots: Roots, action: Action, profile: Profile) -> Bool:
  match roots:
    case Roots{parent, leaf}:
      match action:
        case RemoveLeaf{}: Bool.or(leaf, accepts_missing_root(profile))
        case AddLeaf{}: True{}
        case RemoveParent{}: Bool.or(parent, accepts_missing_root(profile))

def edit(roots: Roots, action: Action) -> Roots:
  match roots:
    case Roots{parent, leaf}:
      match action:
        case RemoveLeaf{}: Roots{parent, False{}}
        case AddLeaf{}: Roots{parent, True{}}
        case RemoveParent{}: Roots{False{}, leaf}

def choose(ok: Bool, action: Action, +roots: Roots) -> Roots:
  match ok:
    case True{}: edit(roots, action)
    case False{}: roots

def next(profile: Profile, +action: Action, +roots: Roots) -> Roots:
  choose(accepted(roots, action, profile), action, roots)

law remaining_parent_retains_leaf:
  {live_leaf(Roots{True{},False{}}) == True{} : Bool}
def remaining_parent_retains_leaf():
  {==}

law identical_readoption_adds_declaration:
  for profile: Profile
  for +parent: Bool
  {next(profile,AddLeaf{},Roots{parent,False{}}) == Roots{parent,True{}} : Roots}
def identical_readoption_adds_declaration(profile, parent):
  {==}

law retained_leaf_need_not_be_root_visible:
  {root_can_load_leaf(Pnpm{},Roots{True{},False{}}) == False{} : Bool}
def retained_leaf_need_not_be_root_visible():
  {==}

def main() -> IO(Unit):
  IO.print("Bounded two-package removal projection,not a resolver or cache collector.")
