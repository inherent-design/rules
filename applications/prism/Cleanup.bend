import Base

# Scheduling/string projection only. Typed filesystem effects are in Lean.
# norm is an independently checked lexical host witness, not realpath authority.
type Choice is Data:
  Unasked{}
  Yes{}
  No{}
type CleanupRequest is Data:
  CleanupRequest{raw: String, norm: String, pair: Bool}
type CleanupPlan is Data:
  CleanupPlan{choice: Choice, prompts: Nat, paths: List<&2,String>, answers: List<&2,Choice>, unknown: Bool}

def is_unasked(c: Choice) -> Bool:
  match c:
    case Unasked{}: True{}
    case _: False{}
def is_no(c: Choice) -> Bool:
  match c:
    case No{}: True{}
    case _: False{}
def code(c: Choice) -> Nat:
  match c:
    case Unasked{}: 0n
    case Yes{}: 1n
    case No{}: 2n
def alternate(+path: String) -> String:
  Bool.pick(String,String.ends_with(path,".disabled"),String.reverse(String.drop(String.reverse(path),9n)),path ++ ".disabled")
def protected(raw: String,+norm: String,proposed: Bool) -> Bool:
  Bool.pick(Bool,proposed,Bool.or(String.eq(norm,"saves"),String.starts_with(norm,"saves/")),String.starts_with(raw,"saves/"))
def refresh(p: CleanupPlan) -> CleanupPlan:
  match p:
    case CleanupPlan{choice,n,paths,Nil{},u}: CleanupPlan{choice,n,paths,Nil{},True{}}
    case CleanupPlan{choice,n,paths,+answer <> tail,u}:
      CleanupPlan{answer,Nat.add(n,1n),paths,tail,Bool.or(u,is_unasked(answer))}
def add_path(p: CleanupPlan,+norm: String,pair: Bool,guarded: Bool) -> CleanupPlan:
  match p:
    case CleanupPlan{+choice,+n,+paths,+answers,+unknown}:
      blocked=Bool.or(unknown,Bool.and(guarded,is_no(choice)))
      added=Bool.pick(List<&2,String>,pair,[norm,alternate(norm)],[norm])
      Bool.pick(CleanupPlan,blocked,CleanupPlan{choice,n,paths,answers,unknown},
        CleanupPlan{choice,n,List.append(&2,String,paths,added),answers,unknown})
def step_nonempty(+p: CleanupPlan,+raw: String,norm: String,pair: Bool,+guarded: Bool) -> CleanupPlan:
  match p:
    case CleanupPlan{+choice,n,paths,answers,+unknown}:
      needs=Bool.and(guarded,is_unasked(choice))
      ready=Bool.pick(CleanupPlan,needs,refresh(p),p)
      Bool.pick(CleanupPlan,Bool.or(String.eq(raw,""),unknown),p,add_path(ready,norm,pair,guarded))
def step(+p: CleanupPlan,r: CleanupRequest,+proposed: Bool) -> CleanupPlan:
  match r:
    case CleanupRequest{+raw,+norm,pair}:
      guarded=protected(raw,norm,proposed)
      step_nonempty(p,raw,norm,pair,guarded)
def plan(requests: List<&2,CleanupRequest>,p: CleanupPlan,+proposed: Bool) -> CleanupPlan:
  match requests:
    case Nil{}: p
    case head <> tail: plan(tail,step(p,head,proposed),proposed)

def last_suffix(+s: String,+needle: String,+best: String) -> String:
  match s:
    case SNil{}: best
    case SCon{c,tail}:
      next=Bool.pick(String,String.starts_with(s,needle),String.drop(s,String.length(needle)),best)
      last_suffix(tail,needle,next)
def recorded(+name: String,path: String) -> String:
  +raw="/" ++ path
  String.drop(last_suffix(raw,name,raw),1n)
def space(+c: Char) -> Bool:
  Bool.or(Char.is_space(c),Char.is_eq(c,' '))
def trim_start(s: String) -> String:
  match s:
    case SNil{}: SNil{}
    case SCon{+c,+tail}: Bool.pick(String,space(c),trim_start(tail),SCon{c,tail})
def trim(s: String) -> String:
  String.reverse(trim_start(String.reverse(trim_start(s))))
def serialize(+name: String,paths: List<&2,String>) -> String:
  match paths:
    case Nil{}: ""
    case head <> tail: recorded(name,head) ++ "\n" ++ serialize(name,tail)
def trim_lines(lines: List<&2,String>) -> List<&2,String>:
  match lines:
    case Nil{}: Nil{}
    case head <> tail: trim(head) <> trim_lines(tail)
def read_records(name: String,paths: List<&2,String>) -> List<&2,String>:
  trim_lines(String.lines(serialize(name,paths)))
def has_failure(results: List<&2,Bool>) -> Bool:
  match results:
    case Nil{}: False{}
    case head <> tail: Bool.or(head,has_failure(tail))
def contains_path(+path: String,paths: List<&2,String>) -> Bool:
  match paths:
    case Nil{}: False{}
    case head <> tail: Bool.or(String.eq(path,head),contains_path(path,tail))
def directory_results(+directories: List<&2,String>,paths: List<&2,String>) -> List<&2,Bool>:
  match paths:
    case Nil{}: Nil{}
    case head <> tail: contains_path(head,directories) <> directory_results(directories,tail)
def failure_summary(p: CleanupPlan,directories: List<&2,String>,override_existing: Bool) -> Bool:
  match p:
    case CleanupPlan{choice,n,paths,answers,unknown}:
      Bool.and(override_existing,has_failure(directory_results(directories,paths)))

# JSON renderer covers the admitted fixture text. No general JSON codec claim.
def escaped(s: String) -> String:
  match s:
    case SNil{}: ""
    case SCon{+c,tail}:
      quoted=Bool.pick(String,Char.is_eq(c,'"'),"\\\"",
        Bool.pick(String,Char.is_eq(c,'\\'),"\\\\",
          Bool.pick(String,Char.is_eq(c,'\n'),"\\n",
            Bool.pick(String,Char.is_eq(c,'\r'),"\\r",
              Bool.pick(String,Char.is_eq(c,'\t'),"\\t",SCon{c,SNil{}})))))
      quoted ++ escaped(tail)
def strings_tail(paths: List<&2,String>) -> String:
  match paths:
    case Nil{}: ""
    case head <> tail: ",\"" ++ escaped(head) ++ "\"" ++ strings_tail(tail)
def strings(paths: List<&2,String>) -> String:
  match paths:
    case Nil{}: "[]"
    case head <> tail: "[\"" ++ escaped(head) ++ "\"" ++ strings_tail(tail) ++ "]"
def boolean(b: Bool) -> String:
  match b:
    case True{}: "true"
    case False{}: "false"
def render(p: CleanupPlan) -> String:
  match p:
    case CleanupPlan{choice,n,paths,answers,u}:
      "{\"choice\":" ++ Nat.show(code(choice)) ++ ",\"prompts\":" ++ Nat.show(n) ++
      ",\"paths\":" ++ strings(paths) ++ ",\"unknown\":" ++ boolean(u) ++ "}"

law direct_save_is_guarded:
  {protected("saves/a","saves/a",False{}) == True{} : Bool}
def direct_save_is_guarded():
  {==}
law current_dot_alias_is_not_guarded:
  {protected("./saves/a","saves/a",False{}) == False{} : Bool}
def current_dot_alias_is_not_guarded():
  {==}
law proposed_dot_alias_is_guarded:
  {protected("./saves/a","saves/a",True{}) == True{} : Bool}
def proposed_dot_alias_is_guarded():
  {==}
law directory_failure_is_not_erased_by_later_success:
  {has_failure([False{},True{},False{}]) == True{} : Bool}
def directory_failure_is_not_erased_by_later_success():
  {==}
law refused_save_directory_is_not_attempted:
  {failure_summary(plan([CleanupRequest{"saves/world","saves/world",False{}}],CleanupPlan{No{},0n,[],[],False{}},False{}),["saves/world"],True{}) == False{} : Bool}
def refused_save_directory_is_not_attempted():
  {==}
law marker_in_filename_loses_path:
  {recorded("overrides","config/my-overrides-settings.toml") == "settings.toml" : String}
def marker_in_filename_loses_path():
  {==}
law pairing_removes_disabled_suffix:
  {alternate("mods/a.jar.disabled") == "mods/a.jar" : String}
def pairing_removes_disabled_suffix():
  {==}
law record_trimming_loses_filename_spaces:
  {read_records("overrides",["  options.txt  "]) == ["options.txt",""] : List<&2,String>}
def record_trimming_loses_filename_spaces():
  {==}
law record_newline_is_a_delimiter:
  {read_records("overrides",["config/line\nbreak.txt"]) == ["config/line","break.txt",""] : List<&2,String>}
def record_newline_is_a_delimiter():
  {==}

def main() -> IO(Unit):
  IO.print(strings(read_records("overrides",["config/my-overrides-settings.toml"])))
