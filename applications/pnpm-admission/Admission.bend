import Base

# Kinds0=tasks,1=registered placeholder,2=explicit run,3=declared fallback.
# Successful controlled scripts and empty private group state are premises.
type Request is Data:
  Request{kind: Nat,forced: Bool,help: Bool,member: Bool,local: Bool,root: Bool,label: String,args: List<&2,String>}
type Outcome is Data:
  Outcome{action: String,status: Nat,label: Maybe<&2,String>,args: List<&2,String>,npm: Maybe<&2,String>}
def no_child(action: String,status: Nat) -> Outcome:
  Outcome{action,status,None{},[],None{}}
def script(label: String,args: List<&2,String>) -> Outcome:
  Outcome{"script",0n,Some{label},args,Some{"run-script"}}
def run(r: Request) -> Outcome:
  match r:
    case Request{kind,forced,help,member,local,root,label,args}:
      match kind:
        case 0n: Bool.pick(Outcome,help,no_child("builtin-help",0n),Bool.pick(Outcome,forced,no_child("builtin-status",0n),Bool.pick(Outcome,local,script(label,args),Bool.pick(Outcome,Bool.and(member,root),no_child("root-shadow",1n),no_child("builtin-status",0n)))))
        case 1n: no_child("unsupported",1n)
        case _: script(label,args)
def leading_pm(args: List<&2,String>) -> Bool:
  match args:
    case Nil{}: False{}
    case Con{head,_}: String.eq(head,"pm")
def strip_pm(args: List<&2,String>) -> List<&2,String>:
  match args:
    case Nil{}: []
    case Con{+head,+tail}: Bool.pick(List<&2,String>,String.eq(head,"pm"),tail,Con{head,tail})
def optional(value: Maybe<&2,String>) -> String:
  match value:
    case None{}: "~"
    case Some{text}: text
def arguments(values: List<&2,String>) -> String:
  match values:
    case Nil{}: ""
    case Con{head,tail}: head ++ "," ++ arguments(tail)
def render(o: Outcome) -> String:
  match o:
    case Outcome{action,status,label,args,npm}: action ++ "/" ++ Nat.show(status) ++ "/" ++ optional(label) ++ "/" ++ arguments(args) ++ "/" ++ optional(npm)

law local_script_overrides_tasks:
  {render(run(Request{0n,False{},False{},False{},True{},True{},"tasks",["status"]})) == "script/0/tasks/status,/run-script" : String}
def local_script_overrides_tasks(): {==}
law force_selects_tasks_builtin:
  {render(run(Request{0n,True{},False{},False{},True{},True{},"tasks",["status"]})) == "builtin-status/0/~//~" : String}
def force_selects_tasks_builtin(): {==}
law root_shadow_refuses_member_builtin:
  {render(run(Request{0n,False{},False{},True{},False{},True{},"",["status"]})) == "root-shadow/1/~//~" : String}
def root_shadow_refuses_member_builtin(): {==}
law forced_explicit_run_still_runs_script:
  {render(run(Request{2n,True{},False{},False{},True{},True{},"tasks",["status"]})) == "script/0/tasks/status,/run-script" : String}
def forced_explicit_run_still_runs_script(): {==}
law placeholder_refuses_script:
  for local: Bool
  {render(run(Request{1n,False{},False{},False{},local,True{},"edit",[]})) == "unsupported/1/~//~" : String}
def placeholder_refuses_script(local): {==}
law help_precedes_script_override:
  for forced: Bool
  {render(run(Request{0n,forced,True{},False{},True{},True{},"tasks",["--help"]})) == "builtin-help/0/~//~" : String}
def help_precedes_script_override(forced): {==}
law empty_root_does_not_shadow:
  {render(run(Request{0n,False{},False{},True{},False{},False{},"",["status"]})) == "builtin-status/0/~//~" : String}
def empty_root_does_not_shadow(): {==}
law explicit_run_forwards_help:
  {render(run(Request{2n,False{},False{},False{},True{},True{},"tasks",["--help"]})) == "script/0/tasks/--help,/run-script" : String}
def explicit_run_forwards_help(): {==}
law leading_pm_strips_one_token:
  {arguments(strip_pm(["pm","tasks","status"])) == "tasks,status," : String}
def leading_pm_strips_one_token(): {==}
law global_option_before_pm_does_not_force:
  {leading_pm(["--dir",".","pm","tasks","status"]) == False{} : Bool}
def global_option_before_pm_does_not_force(): {==}
