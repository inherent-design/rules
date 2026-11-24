import Base

# Fixed single-package publication projection; server truth is not client evidence.
type Profile is Data:
  Npm{}
  Pnpm{}
  Yarn{}

type Loss is Data:
  NoLoss{}
  BeforeAcceptance{}
  AfterAcceptance{}

type Hook is Data:
  NoHook{}
  BeforeUpload{}
  AfterUpload{}

type Request is Data:
  Request{dry: Bool, exists: Bool, rejected: Bool, loss: Loss, hooks: Bool, hook: Hook}

type Facts is Data:
  Facts{sent: Bool, accepted: Bool, present: Bool, acknowledged: Bool, effects: Bool, status: Nat}

def npm(p: Profile) -> Bool:
  match p:
    case Npm{}: True{}
    case Pnpm{}: False{}
    case Yarn{}: False{}

def no_loss(loss: Loss) -> Bool:
  match loss:
    case NoLoss{}: True{}
    case BeforeAcceptance{}: False{}
    case AfterAcceptance{}: False{}

def before_loss(loss: Loss) -> Bool:
  match loss:
    case NoLoss{}: False{}
    case BeforeAcceptance{}: True{}
    case AfterAcceptance{}: False{}

def before_hook(hook: Hook) -> Bool:
  match hook:
    case NoHook{}: False{}
    case BeforeUpload{}: True{}
    case AfterUpload{}: False{}

def after_hook(hook: Hook) -> Bool:
  match hook:
    case NoHook{}: False{}
    case BeforeUpload{}: False{}
    case AfterUpload{}: True{}

def precheck(p: Profile, dry: Bool, exists: Bool) -> Bool:
  Bool.and(Bool.not(dry),Bool.and(npm(p),exists))

def result_status(failed: Bool, hook_failed: Bool, p: Profile) -> Nat:
  match failed:
    case False{}: 0n
    case True{}:
      match hook_failed:
        case False{}: 1n
        case True{}:
          match p:
            case Npm{}: 7n
            case Pnpm{}: 1n
            case Yarn{}: 1n

def finish(p: Profile, exists: Bool, hooks: Bool, sent: Bool, +accepted: Bool, acknowledged: Bool, checked: Bool, network_failed: Bool, +hook_failed: Bool) -> Facts:
  Facts{sent,accepted,Bool.or(exists,accepted),acknowledged,hooks,result_status(Bool.or(checked,Bool.or(network_failed,hook_failed)),hook_failed,p)}

def with_network(p: Profile, exists: Bool, +hooks: Bool, hook: Hook, +early: Bool, +checked: Bool, sent: Bool, accepted: Bool, acknowledged: Bool, +network_failed: Bool) -> Facts:
  finish(p,exists,hooks,sent,accepted,acknowledged,checked,network_failed,Bool.or(early,Bool.and(Bool.not(early),Bool.and(Bool.not(checked),Bool.and(Bool.not(network_failed),Bool.and(hooks,after_hook(hook)))))))

def complete(p: Profile, exists: Bool, hooks: Bool, hook: Hook, early: Bool, checked: Bool, +sent: Bool, accepted: Bool, +acknowledged: Bool) -> Facts:
  with_network(p,exists,hooks,hook,early,checked,sent,accepted,acknowledged,Bool.and(sent,Bool.not(acknowledged)))

def accepted_result(p: Profile, exists: Bool, hooks: Bool, hook: Hook, early: Bool, checked: Bool, sent: Bool, +accepted: Bool, loss: Loss) -> Facts:
  complete(p,exists,hooks,hook,early,checked,sent,accepted,Bool.and(accepted,no_loss(loss)))

def exchange(p: Profile, +exists: Bool, hooks: Bool, hook: Hook, early: Bool, checked: Bool, +sent: Bool, +loss: Loss, rejected: Bool) -> Facts:
  accepted_result(p,exists,hooks,hook,early,checked,sent,Bool.and(sent,Bool.and(Bool.not(exists),Bool.and(Bool.not(rejected),Bool.not(before_loss(loss))))),loss)

def send(p: Profile, exists: Bool, hooks: Bool, hook: Hook, +early: Bool, +checked: Bool, dry: Bool, loss: Loss, rejected: Bool) -> Facts:
  exchange(p,exists,hooks,hook,early,checked,Bool.and(Bool.not(early),Bool.and(Bool.not(dry),Bool.not(checked))),loss,rejected)

def publish(+p: Profile, r: Request) -> Facts:
  match r:
    case Request{+dry,+exists,rejected,loss,+hooks,+hook}:
      send(p,exists,hooks,hook,Bool.and(hooks,before_hook(hook)),precheck(p,dry,exists),dry,loss,rejected)

law dry_run_can_have_local_effects:
  {publish(Npm{},Request{True{},False{},False{},NoLoss{},True{},NoHook{}}) == Facts{False{},False{},False{},False{},True{},0n} : Facts}
def dry_run_can_have_local_effects():
  {==}

law loss_before_acceptance:
  {publish(Pnpm{},Request{False{},False{},False{},BeforeAcceptance{},False{},NoHook{}}) == Facts{True{},False{},False{},False{},False{},1n} : Facts}
def loss_before_acceptance():
  {==}

law loss_after_acceptance:
  {publish(Pnpm{},Request{False{},False{},False{},AfterAcceptance{},False{},NoHook{}}) == Facts{True{},True{},True{},False{},False{},1n} : Facts}
def loss_after_acceptance():
  {==}

law failed_postpack_can_follow_publication:
  {publish(Yarn{},Request{False{},False{},False{},NoLoss{},True{},AfterUpload{}}) == Facts{True{},True{},True{},True{},True{},1n} : Facts}
def failed_postpack_can_follow_publication():
  {==}

law failed_prepack_prevents_upload:
  {publish(Npm{},Request{False{},False{},False{},NoLoss{},True{},BeforeUpload{}}) == Facts{False{},False{},False{},False{},True{},7n} : Facts}
def failed_prepack_prevents_upload():
  {==}

law existing_npm_version_refuses_before_put:
  {publish(Npm{},Request{False{},True{},False{},NoLoss{},False{},NoHook{}}) == Facts{False{},False{},True{},False{},False{},1n} : Facts}
def existing_npm_version_refuses_before_put():
  {==}

law existing_yarn_version_refuses_at_put:
  {publish(Yarn{},Request{False{},True{},False{},NoLoss{},False{},NoHook{}}) == Facts{True{},False{},True{},False{},False{},1n} : Facts}
def existing_yarn_version_refuses_at_put():
  {==}

def main() -> IO(Unit):
  IO.print("Publication, acknowledgement, local hooks, and command status are separate facts.")
