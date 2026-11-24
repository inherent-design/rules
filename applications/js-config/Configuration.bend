import Base

type Manager is Data:
  Npm{}
  Pnpm{}
  Yarn{}
type Scope is Data:
  Default{}
  Global{}
  Home{}
  Project{}
type Action is Data:
  Get{}
  Explain{}
  Set{}
  Unset{}
type State is Data:
  State{global: Nat, home: Nat, project: Nat}
type Context is Data:
  Context{environment: Nat, command: Nat, global_mode: Bool, custom_rc: Bool, fallback: Nat}
type Source is Data:
  Fallback{}
  GlobalSource{}
  HomeSource{}
  ProjectSource{}
  Environment{}
  Command{}
type Effective is Data:
  Effective{value: Nat, source: Source}

def npm(a: Manager) -> Bool:
  match a:
    case Npm{}: True{}
    case Pnpm{}: False{}
    case Yarn{}: False{}

def yarn(a: Manager) -> Bool:
  match a:
    case Npm{}: False{}
    case Pnpm{}: False{}
    case Yarn{}: True{}

def default_target(a: Manager) -> Scope:
  match a:
    case Npm{}: Home{}
    case Pnpm{}: Global{}
    case Yarn{}: Project{}

def target(a: Manager, s: Scope) -> Scope:
  match s:
    case Default{}: default_target(a)
    case Global{}: Global{}
    case Home{}: Home{}
    case Project{}: Project{}

def put_fields(scope: Scope, global: Nat, home: Nat, project: Nat, +v: Nat) -> State:
  match scope:
    case Default{}: State{global,home,project}
    case Global{}: State{v,home,project}
    case Home{}: State{global,v,project}
    case Project{}: State{global,home,v}

def put(s: State, scope: Scope, +v: Nat) -> State:
  match s:
    case State{global,home,project}: put_fields(scope,global,home,project,v)

def after_at(s: State, action: Action, scope: Scope, v: Nat) -> State:
  match action:
    case Get{}: s
    case Explain{}: s
    case Set{}: put(s,scope,v)
    case Unset{}: put(s,scope,0n)

def after(+a: Manager, s: State, action: Action, scope: Scope, v: Nat) -> State:
  after_at(s,action,target(a,scope),v)

def present(v: Nat) -> Bool:
  Bool.not(Nat.is_eq(v,0n))

def effective_values(+a: Manager, +global: Nat, +home: Nat, +project: Nat, +environment: Nat, +command: Nat, global_mode: Bool, custom_rc: Bool, fallback: Nat, align_home: Bool) -> Effective:
  Bool.pick(Effective,present(command),Effective{command,Command{}},Bool.pick(Effective,present(environment),Effective{environment,Environment{}},Bool.pick(Effective,Bool.and(Bool.not(global_mode),present(project)),Effective{project,ProjectSource{}},Bool.pick(Effective,Bool.and(npm(a),present(home)),Effective{home,HomeSource{}},Bool.pick(Effective,Bool.and(yarn(a),Bool.and(Bool.or(Bool.not(custom_rc),align_home),present(home))),Effective{home,HomeSource{}},Bool.pick(Effective,Bool.and(Bool.not(yarn(a)),present(global)),Effective{global,GlobalSource{}},Effective{fallback,Fallback{}}))))))

def effective_fields(a: Manager, global: Nat, home: Nat, project: Nat, c: Context, align_home: Bool) -> Effective:
  match c:
    case Context{environment,command,global_mode,custom_rc,fallback}:
      effective_values(a,global,home,project,environment,command,global_mode,custom_rc,fallback,align_home)

def effective(+a: Manager, s: State, c: Context, align_home: Bool) -> Effective:
  match s:
    case State{global,home,project}: effective_fields(a,global,home,project,c,align_home)

def value(e: Effective) -> Nat:
  match e:
    case Effective{v,s}: v

def source_text(s: Source) -> String:
  match s:
    case Fallback{}: "default"
    case GlobalSource{}: "global"
    case HomeSource{}: "home"
    case ProjectSource{}: "project"
    case Environment{}: "environment"
    case Command{}: "command"

def source_name(e: Effective) -> String:
  match e:
    case Effective{v,s}: source_text(s)

def set_action(a: Action) -> Bool:
  match a:
    case Get{}: False{}
    case Explain{}: False{}
    case Set{}: True{}
    case Unset{}: False{}

def writes(a: Action) -> Bool:
  match a:
    case Get{}: False{}
    case Explain{}: False{}
    case Set{}: True{}
    case Unset{}: True{}

def reported(+a: Manager, +action: Action, s: State, c: Context, scope: Scope, v: Nat) -> Nat:
  Bool.pick(Nat,Bool.and(yarn(a),set_action(action)),value(effective(a,after(a,s,action,scope,v),c,False{})),0n)

law distinct_default_write_targets:
  {default_target(Npm{}) == Home{} : Scope}
def distinct_default_write_targets():
  {==}

law pnpm_defaults_to_global_write:
  {default_target(Pnpm{}) == Global{} : Scope}
def pnpm_defaults_to_global_write():
  {==}

law yarn_defaults_to_project_write:
  {default_target(Yarn{}) == Project{} : Scope}
def yarn_defaults_to_project_write():
  {==}

law home_write_does_not_edit_project:
  {put(State{1n,2n,3n},Home{},7n) == State{1n,7n,3n} : State}
def home_write_does_not_edit_project():
  {==}

law npm_global_mode_keeps_user_layer:
  {effective(Npm{},State{1n,2n,3n},Context{0n,0n,True{},False{},9n},False{}) == Effective{2n,HomeSource{}} : Effective}
def npm_global_mode_keeps_user_layer():
  {==}

law current_custom_home_value_is_not_loaded:
  {effective(Yarn{},State{0n,7n,0n},Context{0n,0n,False{},True{},10n},False{}) == Effective{10n,Fallback{}} : Effective}
def current_custom_home_value_is_not_loaded():
  {==}

law standard_home_value_is_loaded:
  {effective(Yarn{},State{0n,7n,0n},Context{0n,0n,False{},False{},10n},False{}) == Effective{7n,HomeSource{}} : Effective}
def standard_home_value_is_loaded():
  {==}

law masked_yarn_set_reports_environment_value:
  {reported(Yarn{},Set{},State{0n,2n,3n},Context{4n,0n,False{},False{},10n},Home{},7n) == 4n : Nat}
def masked_yarn_set_reports_environment_value():
  {==}

law proposed_aligned_home_reader_keeps_value:
  {effective(Yarn{},State{0n,7n,0n},Context{0n,0n,False{},True{},10n},True{}) == Effective{7n,HomeSource{}} : Effective}
def proposed_aligned_home_reader_keeps_value():
  {==}
