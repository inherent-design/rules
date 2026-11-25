import Base
import ../js-peers/Publication.bend as P

# Fixed private / consumer->producer graph and explicitly selected CLI profiles.
# failure0 none,1 producer-late,2 private-early;role1 consumer,2 producer.
type WResult is Data:
  WResult{private_hook: Bool,producer: Bool,consumer: Bool,blocked: Bool,order: Nat,rewritten: Bool,summary: Nat,status: Nat}

def finish(+npm: Bool,+pnpm: Bool,+early: Bool,producer: P.Facts,consumer: P.Facts) -> WResult:
  match producer:
    case P.Facts{_,+pa,_,_,_,+status}:
      match consumer:
        case P.Facts{_,ca,_,_,_,_}:
          +accepted_p=Bool.and(Bool.not(early),pa)
          +accepted_c=Bool.and(Bool.not(early),Bool.and(Bool.or(npm,Nat.is_eq(status,0n)),ca))
          blocked=Bool.and(Bool.not(early),Bool.and(Bool.not(npm),Bool.not(Nat.is_eq(status,0n))))
          order=Bool.pick(Nat,early,0n,Bool.pick(Nat,npm,12n,Bool.pick(Nat,accepted_c,21n,2n)))
          WResult{npm,accepted_p,accepted_c,blocked,order,Bool.and(Bool.not(npm),accepted_c),Bool.pick(Nat,pnpm,Nat.add(Bool.pick(Nat,accepted_p,1n,0n),Bool.pick(Nat,accepted_c,1n,0n)),0n),Bool.pick(Nat,early,7n,status)}

def pnpm(profile: P.Profile) -> Bool:
  match profile:
    case P.Npm{}: False{}
    case P.Pnpm{}: True{}
    case P.Yarn{}: False{}
def run(+profile: P.Profile,+failure: Nat) -> WResult:
  finish(P.npm(profile),pnpm(profile),Bool.and(P.npm(profile),Nat.is_eq(failure,2n)),P.publish(profile,P.Request{False{},False{},False{},P.NoLoss{},True{},Bool.pick(P.Hook,Nat.is_eq(failure,1n),P.AfterUpload{},P.NoHook{})}),P.publish(profile,P.Request{False{},False{},False{},P.NoLoss{},True{},P.NoHook{}}))

law npm_private_failure:
  {run(P.Npm{},2n) == WResult{True{},False{},False{},False{},0n,False{},0n,7n} : WResult}
def npm_private_failure(): {==}
law npm_success_order:
  {run(P.Npm{},0n) == WResult{True{},True{},True{},False{},12n,False{},0n,0n} : WResult}
def npm_success_order(): {==}
law npm_late_failure_keeps_uploads:
  {run(P.Npm{},1n) == WResult{True{},True{},True{},False{},12n,False{},0n,7n} : WResult}
def npm_late_failure_keeps_uploads(): {==}
law pnpm_success_order:
  {run(P.Pnpm{},0n) == WResult{False{},True{},True{},False{},21n,True{},2n,0n} : WResult}
def pnpm_success_order(): {==}
law pnpm_late_failure_keeps_summary:
  {run(P.Pnpm{},1n) == WResult{False{},True{},False{},True{},2n,False{},1n,1n} : WResult}
def pnpm_late_failure_keeps_summary(): {==}
law pnpm_private_is_skipped:
  {run(P.Pnpm{},2n) == WResult{False{},True{},True{},False{},21n,True{},2n,0n} : WResult}
def pnpm_private_is_skipped(): {==}
law yarn_success_order:
  {run(P.Yarn{},0n) == WResult{False{},True{},True{},False{},21n,True{},0n,0n} : WResult}
def yarn_success_order(): {==}
law yarn_late_failure_keeps_producer:
  {run(P.Yarn{},1n) == WResult{False{},True{},False{},True{},2n,False{},0n,1n} : WResult}
def yarn_late_failure_keeps_producer(): {==}
law yarn_private_is_skipped:
  {run(P.Yarn{},2n) == WResult{False{},True{},True{},False{},21n,True{},0n,0n} : WResult}
def yarn_private_is_skipped(): {==}

def number(b: Bool) -> Nat: Bool.pick(Nat,b,1n,0n)
def render(r: WResult) -> String:
  match r:
    case WResult{a,b,c,d,e,f,g,h}: Nat.show(number(a)) ++ "/" ++ Nat.show(number(b)) ++ "/" ++ Nat.show(number(c)) ++ "/" ++ Nat.show(number(d)) ++ "/" ++ Nat.show(e) ++ "/" ++ Nat.show(number(f)) ++ "/" ++ Nat.show(g) ++ "/" ++ Nat.show(h)
def main() -> IO(Unit): IO.print("Workspace selection, packed ranges, accepted prefixes, and final status remain distinct.")
