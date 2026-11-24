import Base

type FileFacts is Data:
  FileFacts{prohibited: Bool, required: Bool, git_ignored: Bool, include_match: Bool, exclude_match: Bool}

def optional(include: Bool, git_ignored: Bool, include_match: Bool, exclude_match: Bool) -> Bool:
  match include:
    case True{}: include_match
    case False{}: Bool.and(Bool.not(git_ignored),Bool.not(exclude_match))

def selected(file: FileFacts, include: Bool) -> Bool:
  match file:
    case FileFacts{prohibited,required,git_ignored,include_match,exclude_match}:
      Bool.and(Bool.not(prohibited),Bool.or(required,optional(include,git_ignored,include_match,exclude_match)))

type Request is Data:
  ListOnly{}
  Unchecked{}
  Verify{}

type Outcome is Data:
  Outcome{archive: Bool, checked: Bool, build_ok: Bool, command_ok: Bool}

def outcome(request: Request, +compiles: Bool) -> Outcome:
  match request:
    case ListOnly{}: Outcome{False{},False{},False{},True{}}
    case Unchecked{}: Outcome{True{},False{},False{},True{}}
    case Verify{}: Outcome{True{},True{},compiles,compiles}

law prohibited_input_not_selected:
  for include: Bool
  for required: Bool
  for git_ignored: Bool
  for include_match: Bool
  for exclude_match: Bool
  {selected(FileFacts{True{},required,git_ignored,include_match,exclude_match},include) == False{} : Bool}
def prohibited_input_not_selected(include,required,git_ignored,include_match,exclude_match):
  {==}

law required_root_metadata_survives_filter:
  for include: Bool
  for git_ignored: Bool
  for include_match: Bool
  for exclude_match: Bool
  {selected(FileFacts{False{},True{},git_ignored,include_match,exclude_match},include) == True{} : Bool}
def required_root_metadata_survives_filter(include,git_ignored,include_match,exclude_match):
  {==}

law include_ignores_git_and_exclude:
  for git_ignored: Bool
  for +include_match: Bool
  for exclude_match: Bool
  {selected(FileFacts{False{},False{},git_ignored,include_match,exclude_match},True{}) == include_match : Bool}
def include_ignores_git_and_exclude(git_ignored,include_match,exclude_match):
  {==}

law failed_verification_can_leave_archive:
  {outcome(Verify{},False{}) == Outcome{True{},True{},False{},False{}} : Outcome}
def failed_verification_can_leave_archive():
  {==}

def main() -> IO(Unit):
  IO.print("Archive selection and controlled build outcome; not registry publication evidence.")
