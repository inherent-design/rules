import Base

# Profiles are this measured fixture, not general package-manager algorithms.
type FixtureProfile is Data:
  NpmHoisted{}
  PnpmIsolated{}
  YarnNodeModules{}

type Instance is Data:
  Inst{content: String, peer: String}

def fixture_provider(profile: FixtureProfile, direct: String, hoisted: String) -> String:
  match profile:
    case NpmHoisted{}: hoisted
    case PnpmIsolated{}: direct
    case YarnNodeModules{}: direct

def instantiate(profile: FixtureProfile, content: String, direct: String, hoisted: String) -> Instance:
  Inst{content, fixture_provider(profile, direct, hoisted)}

def content(instance: Instance) -> String:
  match instance:
    case Inst{content, peer}: content

def provider(instance: Instance) -> String:
  match instance:
    case Inst{content, peer}: peer

type InstallState is Data:
  State{declared: String, locked: String, lock_bytes: String, installed: String}

type Admission is Data:
  Decision{refused: Bool, state: InstallState}

def negate(value: Bool) -> Bool:
  match value:
    case True{}: False{}
    case False{}: True{}

def frozen_admission(state: InstallState) -> Admission:
  match state:
    case State{+declared, +locked, lock_bytes, installed}:
      Decision{negate(String.eq(declared, locked)), State{declared, locked, lock_bytes, installed}}

def state_after(admission: Admission) -> InstallState:
  match admission:
    case Decision{refused, state}: state

law instantiation_preserves_content:
  for profile: FixtureProfile
  for +bytes: String
  for direct: String
  for hoisted: String
  {content(instantiate(profile, bytes, direct, hoisted)) == bytes : String}
def instantiation_preserves_content(profile, bytes, direct, hoisted):
  {==}

law pnpm_fixture_uses_direct:
  for content: String
  for +direct: String
  for hoisted: String
  {provider(instantiate(PnpmIsolated{}, content, direct, hoisted)) == direct : String}
def pnpm_fixture_uses_direct(content, direct, hoisted):
  {==}

law admission_preserves_selected_scope:
  for +declared: String
  for +locked: String
  for +lock_bytes: String
  for +installed: String
  {state_after(frozen_admission(State{declared, locked, lock_bytes, installed})) == State{declared, locked, lock_bytes, installed} : InstallState}
def admission_preserves_selected_scope(declared, locked, lock_bytes, installed):
  {==}

def main() -> IO(Unit):
  IO.print(provider(instantiate(NpmHoisted{}, "plugin", "api-two", "api-one")))
