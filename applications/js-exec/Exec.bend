import Base

# app0/1/2 npm/pnpm/Yarn;mode0/1/2 exec/named-script/npm-call.
type EContext is Data:
  EContext{dependency: Bool,inherited: Bool,cwd: Nat,args: List<&2,String>}
type EOutcome is Data:
  EOutcome{selected: Nat,stage: Nat,exit: Nat,cwd: Nat,args: List<&2,String>}
def success(selected: Nat,c: EContext) -> EOutcome:
  match c:
    case EContext{_,_,cwd,args}: EOutcome{selected,0n,0n,cwd,args}
def failure(stage: Nat,exit: Nat) -> EOutcome:
  EOutcome{0n,stage,exit,0n,Nil{}}
def path_lookup(app: Nat,c: EContext) -> EOutcome:
  match c:
    case EContext{+dependency,+inherited,+cwd,+args}:
      Bool.pick(EOutcome,dependency,success(1n,EContext{dependency,inherited,cwd,args}),Bool.pick(EOutcome,inherited,success(2n,EContext{dependency,inherited,cwd,args}),Bool.pick(EOutcome,Nat.is_eq(app,1n),failure(2n,1n),failure(3n,127n))))
def run(+app: Nat,+mode: Nat,c: EContext) -> EOutcome:
  match c:
    case EContext{+dependency,+inherited,+cwd,+args}:
      +ctx : EContext = EContext{dependency,inherited,cwd,args}
      default=Bool.pick(EOutcome,Nat.is_eq(app,0n),Bool.pick(EOutcome,dependency,success(1n,ctx),failure(1n,1n)),path_lookup(app,ctx))
      Bool.pick(EOutcome,Nat.is_eq(mode,1n),success(3n,ctx),Bool.pick(EOutcome,Nat.is_eq(mode,2n),path_lookup(app,ctx),default))
def arg_count(args: List<&2,String>) -> Nat:
  match args:
    case Nil{}: 0n
    case Con{_,tail}: Nat.add(1n,arg_count(tail))
def joined(args: List<&2,String>) -> String:
  match args:
    case Nil{}: ""
    case Con{head,tail}: head ++ "|" ++ joined(tail)
def render(r: EOutcome) -> String:
  match r:
    case EOutcome{selected,stage,exit,cwd,+args}:
      Nat.show(selected) ++ "/" ++ Nat.show(stage) ++ "/" ++ Nat.show(exit) ++ "/" ++ Nat.show(cwd) ++ "/" ++ Nat.show(arg_count(args)) ++ "/" ++ joined(args)

law npm_default_does_not_run_inherited_path:
  {render(run(0n,0n,EContext{False{},True{},1n,Nil{}})) == "0/1/1/0/0/" : String}
def npm_default_does_not_run_inherited_path(): {==}
law npm_call_uses_inherited_path:
  {render(run(0n,2n,EContext{False{},True{},1n,Nil{}})) == "2/0/0/1/0/" : String}
def npm_call_uses_inherited_path(): {==}
law pnpm_uses_inherited_path:
  {render(run(1n,0n,EContext{False{},True{},1n,Nil{}})) == "2/0/0/1/0/" : String}
def pnpm_uses_inherited_path(): {==}
law yarn_uses_inherited_path:
  {render(run(2n,0n,EContext{False{},True{},1n,Nil{}})) == "2/0/0/1/0/" : String}
def yarn_uses_inherited_path(): {==}
law dependency_beats_path:
  {render(run(0n,0n,EContext{True{},True{},1n,Nil{}})) == "1/0/0/1/0/" : String}
def dependency_beats_path(): {==}
law root_script_is_separate:
  {render(run(1n,1n,EContext{True{},True{},1n,Nil{}})) == "3/0/0/1/0/" : String}
def root_script_is_separate(): {==}
law missing_pnpm_program_returns_one:
  {render(run(1n,0n,EContext{False{},False{},1n,Nil{}})) == "0/2/1/0/0/" : String}
def missing_pnpm_program_returns_one(): {==}
law missing_yarn_program_returns_shell_status:
  {render(run(2n,0n,EContext{False{},False{},1n,Nil{}})) == "0/3/127/0/0/" : String}
def missing_yarn_program_returns_shell_status(): {==}
law nested_directory_and_argument_survive:
  {render(run(2n,0n,EContext{True{},True{},2n,Con{"alpha β",Nil{}}})) == "1/0/0/2/1/alpha β|" : String}
def nested_directory_and_argument_survive(): {==}
