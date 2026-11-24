import Base

# Selected admitted single-package profile, not npm's hidden-index admission.
type Revision is Data:
  Absent{}
  One{}
  Two{}

type Profile is Data:
  Npm{}
  Pnpm{}
  Yarn{}

type Mode is Data:
  Refresh{}
  Frozen{}
  ResolveOnly{}

type State is Data:
  State{wanted: Revision, locked: Revision, payload: Revision, hidden: Revision}

def same(left: Revision, right: Revision) -> Bool:
  match left:
    case Absent{}:
      match right:
        case Absent{}: True{}
        case One{}: False{}
        case Two{}: False{}
    case One{}:
      match right:
        case Absent{}: False{}
        case One{}: True{}
        case Two{}: False{}
    case Two{}:
      match right:
        case Absent{}: False{}
        case One{}: False{}
        case Two{}: True{}

def accepted(mode: Mode, s: State) -> Bool:
  match mode:
    case Frozen{}:
      match s:
        case State{wanted,+locked,payload,hidden}: Bool.and(Bool.not(same(locked,Absent{})),same(locked,wanted))
    case Refresh{}: True{}
    case ResolveOnly{}: True{}

def cached_payload(same_index: Bool, prior: Revision, wanted: Revision) -> Revision:
  match same_index:
    case True{}: prior
    case False{}: wanted

def npm_payload(mode: Mode, +wanted: Revision, +prior: Revision, hidden: Revision) -> Revision:
  match mode:
    case ResolveOnly{}: prior
    case Frozen{}: wanted
    case Refresh{}: cached_payload(same(hidden,wanted),prior,wanted)

def other_payload(mode: Mode, wanted: Revision, prior: Revision) -> Revision:
  match mode:
    case ResolveOnly{}: prior
    case Frozen{}: wanted
    case Refresh{}: wanted

def payload(profile: Profile, mode: Mode, wanted: Revision, prior: Revision, hidden: Revision) -> Revision:
  match profile:
    case Npm{}: npm_payload(mode,wanted,prior,hidden)
    case Pnpm{}: other_payload(mode,wanted,prior)
    case Yarn{}: other_payload(mode,wanted,prior)

def index(profile: Profile, wanted: Revision) -> Revision:
  match profile:
    case Npm{}: wanted
    case Pnpm{}: Absent{}
    case Yarn{}: Absent{}

def admitted(+profile: Profile, mode: Mode, s: State) -> State:
  match s:
    case State{+wanted,locked,+prior,hidden}:
      State{wanted,wanted,payload(profile,mode,wanted,prior,hidden),index(profile,wanted)}

def choose(ok: Bool, profile: Profile, mode: Mode, +s: State) -> State:
  match ok:
    case True{}: admitted(profile,mode,s)
    case False{}: s

def step(profile: Profile, +mode: Mode, +s: State) -> State:
  choose(accepted(mode,s),profile,mode,s)

law missing_lock_refuses_frozen:
  {accepted(Frozen{},State{One{},Absent{},Absent{},Absent{}}) == False{} : Bool}
def missing_lock_refuses_frozen():
  {==}

law stale_lock_refuses_frozen:
  {step(Npm{},Frozen{},State{Two{},One{},One{},One{}}) == State{Two{},One{},One{},One{}} : State}
def stale_lock_refuses_frozen():
  {==}

law lock_only_is_not_materialization:
  {step(Npm{},ResolveOnly{},State{Two{},One{},One{},One{}}) == State{Two{},Two{},One{},Two{}} : State}
def lock_only_is_not_materialization():
  {==}

law successful_refresh_can_preserve_old_payload:
  {step(Npm{},Refresh{},State{Two{},Two{},One{},Two{}}) == State{Two{},Two{},One{},Two{}} : State}
def successful_refresh_can_preserve_old_payload():
  {==}

law invalidated_hidden_control_materializes:
  {step(Npm{},Refresh{},State{Two{},Two{},One{},Absent{}}) == State{Two{},Two{},Two{},Two{}} : State}
def invalidated_hidden_control_materializes():
  {==}

def main() -> IO(Unit):
  IO.print("Lock selection, materialized payload, and npm hidden-index claims are distinct.")
