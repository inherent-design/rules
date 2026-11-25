import Base

# Synchronous string settings plus injected CheckJava result projection.
# No INI persistence, process/GUI callbacks or runtime discovery is modeled.
type S is Data:
  S{passthrough: Bool,gate: Bool,global_default: String,global_value: String,local_value: Maybe<&2,String>}
type A is Data:
  Set{value: String}
  Global{value: String}
  Gate{value: Bool}
  Reset{}
def optional(m: Maybe<&2,String>,fallback: String) -> String:
  match m:
    case None{}: fallback
    case Some{s}: s
def effective(s: S) -> String:
  match s:
    case S{_,gate,_,+g,l}: Bool.pick(String,gate,optional(l,g),g)
def default_value(s: S) -> String:
  match s:
    case S{pass,gate,d,g,_}: Bool.pick(String,Bool.and(pass,Bool.not(gate)),d,g)
def set_value(+s: S,+v: String) -> S:
  match s:
    case S{+pass,+gate,d,g,l}:
      new_local=Bool.pick(Maybe<&2,String>,Bool.and(Bool.or(Bool.not(pass),gate),Bool.not(String.eq(v,effective(s)))),Some{v},l)
      S{pass,gate,d,Bool.pick(String,pass,v,g),new_local}
def set_global(s: S,v: String) -> S:
  match s:
    case S{pass,gate,d,_,l}: S{pass,gate,d,v,l}
def set_gate(s: S,v: Bool) -> S:
  match s:
    case S{pass,_,d,g,l}: S{pass,v,d,g,l}
def reset(s: S) -> S:
  match s:
    case S{+pass,+gate,+d,g,l}: S{pass,gate,d,Bool.pick(String,pass,d,g),Bool.pick(Maybe<&2,String>,Bool.or(Bool.not(pass),gate),None{},l)}
def step(s: S,a: A) -> S:
  match a:
    case Set{v}: set_value(s,v)
    case Global{v}: set_global(s,v)
    case Gate{v}: set_gate(s,v)
    case Reset{}: reset(s)
def setting_text(+s: S) -> String:
  match s:
    case S{_,_,_,g,l}: g ++ "|" ++ optional(l,"-") ++ "|" ++ effective(s) ++ "|" ++ default_value(s)
def trace(actions: List<&2,A>,+s: S) -> String:
  match actions:
    case Nil{}: setting_text(s)
    case Con{a,rest}: setting_text(s) ++ ";" ++ trace(rest,step(s,a))
type M is Data:
  M{version: String,major: Nat,arch: String,real: String,vendor: String}
def complete(m: M) -> Bool:
  match m:
    case M{v,_,a,r,vendor}: Bool.and(Bool.not(String.eq(v,"")),Bool.and(Bool.not(String.eq(a,"")),Bool.and(Bool.not(String.eq(r,"")),Bool.not(String.eq(vendor,"")))))
type I is Data:
  I{executable: Bool,checker: Bool,override: Bool,signature_matches: Bool,stored: M,probe: Nat,result: M,memory: Nat,ignore: Bool,majors: List<&2,Nat>}
def contains(ns: List<&2,Nat>,+n: Nat) -> Bool:
  match ns:
    case Nil{}: False{}
    case Con{x,rest}: Bool.or(Nat.is_eq(x,n),contains(rest,n))
def unrestricted(ns: List<&2,Nat>) -> Bool:
  match ns:
    case Nil{}: True{}
    case _: False{}
def bit(b: Bool) -> String:
  Bool.pick(String,b,"1","0")
def local_field(+write: Bool,override: Bool,+old: String,+v: String) -> String:
  Bool.pick(String,Bool.and(write,Bool.and(override,Bool.not(String.eq(old,v)))),v,"-")
def metadata_text(m: M) -> String:
  match m:
    case M{v,major,a,r,vendor}: Nat.show(major) ++ "|" ++ v ++ "|" ++ a ++ "|" ++ r ++ "|" ++ vendor
def locals(+write: Bool,+override: Bool,old: M,new: M) -> String:
  match old new:
    case M{ov,_,oa,orr,ovendor} M{v,_,a,r,vendor}:
      local_field(write,override,ov,v) ++ "|" ++ local_field(write,override,oa,a) ++ "|" ++ local_field(write,override,orr,r) ++ "|" ++ local_field(write,override,ovendor,vendor)
def finish(+probed: Bool,+success: Bool,+write: Bool,+override: Bool,+sig: Bool,+probe: Nat,+memory: Nat,+ignore: Bool,+majors: List<&2,Nat>,+old: M,+after: M) -> String:
  match after:
    case M{_,+major,+arch,_,_}:
      +admitted=Bool.or(unrestricted(majors),contains(majors,major))
      bit(probed) ++ "|" ++ bit(success) ++ "|" ++ bit(Bool.not(success)) ++ "|" ++ bit(success) ++ "|" ++
      bit(Bool.and(success,Bool.or(admitted,ignore))) ++ "|" ++ bit(Bool.and(success,Bool.not(Bool.or(admitted,ignore)))) ++ "|" ++
      bit(Bool.and(success,Bool.and(String.eq(arch,"32"),Nat.is_gt(memory,2048n)))) ++ "|" ++
      bit(Bool.and(success,Bool.and(Bool.not(admitted),ignore))) ++ "|" ++ bit(Bool.and(probed,Nat.is_eq(probe,1n))) ++ "|" ++
      bit(Bool.or(write,sig)) ++ "|" ++ metadata_text(after) ++ "|" ++ locals(write,override,old,after)
def run(i: I) -> String:
  match i:
    case I{exe,checker,override,+sig,+old,+probe,new,memory,ignore,majors}:
      +ready=Bool.and(exe,checker)
      +probed=Bool.and(ready,Bool.or(Bool.not(sig),Bool.not(complete(old))))
      +write=Bool.and(probed,Nat.is_eq(probe,2n))
      success=Bool.and(ready,Bool.not(Bool.and(probed,Nat.is_eq(probe,0n))))
      finish(probed,success,write,override,sig,probe,memory,ignore,majors,old,Bool.pick(M,write,new,old))

law disabled_read_is_global:
  for pass: Bool
  for d: String
  for g: String
  for l: Maybe<&2,String>
  {effective(S{pass,False{},d,g,l}) == g : String}
def disabled_read_is_global(pass,d,g,l): {==}
law absent_local_inherits:
  for pass: Bool
  for gate: Bool
  for d: String
  for g: String
  {effective(S{pass,gate,d,g,None{}}) == g : String}
def absent_local_inherits(pass,gate,d,g):
  match gate:
    case False{}: {==}
    case True{}: {==}
law override_write_keeps_global:
  for gate: Bool
  for d: String
  for g: String
  for l: Maybe<&2,String>
  for v: String
  {step(S{False{},gate,d,g,l},Set{v}) == S{False{},gate,d,g,Bool.pick(Maybe<&2,String>,Bool.not(String.eq(v,effective(S{False{},gate,d,g,l}))),Some{v},l)} : S}
def override_write_keeps_global(gate,d,g,l,v): {==}
law passthrough_writes_both_when_enabled:
  for d: String
  for g: String
  for l: Maybe<&2,String>
  for v: String
  {step(S{True{},True{},d,g,l},Set{v}) == S{True{},True{},d,v,Bool.pick(Maybe<&2,String>,Bool.not(String.eq(v,optional(l,g))),Some{v},l)} : S}
def passthrough_writes_both_when_enabled(d,g,l,v): {==}
law disabled_passthrough_reset_keeps_dormant_value:
  for d: String
  for g: String
  for l: Maybe<&2,String>
  {step(S{True{},False{},d,g,l},Reset{}) == S{True{},False{},d,d,l} : S}
def disabled_passthrough_reset_keeps_dormant_value(d,g,l): {==}
law equal_write_leaves_local_absent:
  {step(S{True{},True{},"default","global",None{}},Set{"global"}) == S{True{},True{},"default","global",None{}} : S}
def equal_write_leaves_local_absent(): {==}
law gate_does_not_clear_values:
  for pass: Bool
  for gate: Bool
  for d: String
  for g: String
  for l: Maybe<&2,String>
  for v: Bool
  {step(S{pass,gate,d,g,l},Gate{v}) == S{pass,v,d,g,l} : S}
def gate_does_not_clear_values(pass,gate,d,g,l,v): {==}
law old_major_remains_usable_after_invalid_probe:
  {run(I{True{},True{},True{},False{},M{"21.0.1",21n,"64","aarch64","old-vendor"},1n,M{"25.0.1",25n,"64","aarch64","fixture-vendor"},4096n,False{},[21n]}) == "1|1|0|1|1|0|0|0|1|0|21|21.0.1|64|aarch64|old-vendor|-|-|-|-" : String}
def old_major_remains_usable_after_invalid_probe(): {==}
