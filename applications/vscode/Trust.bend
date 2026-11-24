import Base

type Support is Data:
  Missing{}
  Deny{}
  Allow{}
  Limited{}

def prefer(value: Support, fallback: Support) -> Support:
  match value:
    case Missing{}: fallback
    case Deny{}: Deny{}
    case Allow{}: Allow{}
    case Limited{}: Limited{}

def support(enabled: Bool, entry: Bool, version_matches: Bool, configured: Support, override: Support, declared: Support, fallback: Support) -> Support:
  Bool.pick(Support,Bool.and(enabled,entry),prefer(Bool.pick(Support,version_matches,configured,Missing{}),prefer(override,prefer(declared,prefer(fallback,Deny{})))),Allow{})

def denied(value: Support) -> Bool:
  match value:
    case Missing{}: False{}
    case Deny{}: True{}
    case Allow{}: False{}
    case Limited{}: False{}

def blocked(trusted: Bool, inside: Bool, value: Support) -> Bool:
  Bool.and(Bool.not(trusted),Bool.or(inside,denied(value)))

def label(value: Support) -> String:
  match value:
    case Missing{}: "0"
    case Deny{}: "1"
    case Allow{}: "2"
    case Limited{}: "3"

law matching_user_deny_wins:
  for override: Support
  for declared: Support
  for fallback: Support
  {support(True{},True{},True{},Deny{},override,declared,fallback) == Deny{} : Support}
def matching_user_deny_wins(override,declared,fallback):
  {==}

law declarative_extension_supports:
  for enabled: Bool
  for version: Bool
  for configured: Support
  for override: Support
  for declared: Support
  for fallback: Support
  {support(enabled,False{},version,configured,override,declared,fallback) == Allow{} : Support}
def declarative_extension_supports(enabled,version,configured,override,declared,fallback):
  match enabled:
    case False{}: {==}
    case True{}: {==}

law untrusted_workspace_local_blocked:
  for value: Support
  {blocked(False{},True{},value) == True{} : Bool}
def untrusted_workspace_local_blocked(value):
  {==}

law trusted_passes_this_predicate:
  for inside: Bool
  for value: Support
  {blocked(True{},inside,value) == False{} : Bool}
def trusted_passes_this_predicate(inside,value):
  {==}

def main() -> IO(Unit):
  IO.print("Support declaration and trust-related disable predicate;not full extension admission or sandboxing.")
