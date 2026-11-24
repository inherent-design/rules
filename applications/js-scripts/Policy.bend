import Base

type Profile is Data:
  Npm{ignore: Bool, dangerous: Bool}
  Pnpm{ignore: Bool, dangerous: Bool}
  Yarn{enabled: Bool}

type Review is Data:
  Unreviewed{}
  Allow{}
  Deny{}

type Decision is Data:
  Run{}
  Skip{}
  ReviewRequired{}

def npm_review(review: Review) -> Decision:
  match review:
    case Unreviewed{}: Run{}
    case Allow{}: Run{}
    case Deny{}: Skip{}

def npm_wide(dangerous: Bool, review: Review) -> Decision:
  match dangerous:
    case True{}: Run{}
    case False{}: npm_review(review)

def npm_decision(ignore: Bool, dangerous: Bool, review: Review) -> Decision:
  match ignore:
    case True{}: Skip{}
    case False{}: npm_wide(dangerous,review)

def pnpm_review(review: Review, dangerous: Bool) -> Decision:
  match review:
    case Unreviewed{}: Bool.pick(Decision,dangerous,Run{},ReviewRequired{})
    case Allow{}: Run{}
    case Deny{}: Skip{}

def pnpm_decision(ignore: Bool, dangerous: Bool, review: Review) -> Decision:
  match ignore:
    case True{}: Skip{}
    case False{}: pnpm_review(review,dangerous)

def yarn_decision(review: Review, enabled: Bool) -> Decision:
  match review:
    case Unreviewed{}: Bool.pick(Decision,enabled,Run{},Skip{})
    case Allow{}: Run{}
    case Deny{}: Skip{}

def dependency(profile: Profile, review: Review) -> Decision:
  match profile:
    case Npm{ignore,dangerous}: npm_decision(ignore,dangerous,review)
    case Pnpm{ignore,dangerous}: pnpm_decision(ignore,dangerous,review)
    case Yarn{enabled}: yarn_decision(review,enabled)

def workspace(profile: Profile) -> Decision:
  match profile:
    case Npm{ignore,dangerous}: Bool.pick(Decision,ignore,Skip{},Run{})
    case Pnpm{ignore,dangerous}: Bool.pick(Decision,ignore,Skip{},Run{})
    case Yarn{enabled}: Run{}

def label(decision: Decision) -> String:
  match decision:
    case Run{}: "run"
    case Skip{}: "skip"
    case ReviewRequired{}: "review-required"

law npm_ignore_overrides_review:
  for dangerous: Bool
  for review: Review
  {dependency(Npm{True{},dangerous},review) == Skip{} : Decision}
def npm_ignore_overrides_review(dangerous,review):
  {==}

law pnpm_ignore_overrides_review:
  for dangerous: Bool
  for review: Review
  {dependency(Pnpm{True{},dangerous},review) == Skip{} : Decision}
def pnpm_ignore_overrides_review(dangerous,review):
  {==}

law pnpm_deny_overrides_broad_allow:
  for dangerous: Bool
  {dependency(Pnpm{False{},dangerous},Deny{}) == Skip{} : Decision}
def pnpm_deny_overrides_broad_allow(dangerous):
  {==}

law npm_broad_allow_bypasses_deny:
  {dependency(Npm{False{},True{}},Deny{}) == Run{} : Decision}
def npm_broad_allow_bypasses_deny():
  {==}

law yarn_explicit_allow_overrides_disabled_default:
  {dependency(Yarn{False{}},Allow{}) == Run{} : Decision}
def yarn_explicit_allow_overrides_disabled_default():
  {==}

law yarn_workspace_scripts_ignore_dependency_default:
  for enabled: Bool
  {workspace(Yarn{enabled}) == Run{} : Decision}
def yarn_workspace_scripts_ignore_dependency_default(enabled):
  {==}

def main() -> IO(Unit):
  IO.print("Context-specific hook policy,not a process sandbox or physical effect verifier.")
