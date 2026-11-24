import Base

# Local continuation after B failed in the selected serial fixture. This is
# not the complete task graph scheduler or an OS process-retirement rule.
type Policy is Data:
  NpmSequential{}
  PnpmGraph{bail: Bool}
  YarnSerial{}

def independent_after_failure(policy: Policy) -> Bool:
  match policy:
    case NpmSequential{}: True{}
    case PnpmGraph{bail}: Bool.not(bail)
    case YarnSerial{}: False{}

def dependent_after_failure(policy: Policy) -> Bool:
  match policy:
    case NpmSequential{}: True{}
    case PnpmGraph{bail}: False{}
    case YarnSerial{}: False{}

law npm_continues_independent:
  {independent_after_failure(NpmSequential{}) == True{} : Bool}
def npm_continues_independent():
  {==}

law pnpm_bail_stops_independent:
  {independent_after_failure(PnpmGraph{True{}}) == False{} : Bool}
def pnpm_bail_stops_independent():
  {==}

law pnpm_no_bail_allows_independent:
  {independent_after_failure(PnpmGraph{False{}}) == True{} : Bool}
def pnpm_no_bail_allows_independent():
  {==}

law failed_dependency_still_blocks:
  for bail: Bool
  {dependent_after_failure(PnpmGraph{bail}) == False{} : Bool}
def failed_dependency_still_blocks(bail):
  {==}

def main() -> IO(Unit):
  IO.print("Serial independent continuation and failed dependency gating;see the native workspace trace.")
