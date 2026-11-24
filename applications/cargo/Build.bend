import Base

# Selected normal dependency edge, not Cargo's resolver or fingerprint engine.
type Features is Data:
  Feat{red: Bool, blue: Bool}

def selected_features(workspace: Bool) -> Features:
  Feat{True{}, workspace}

type CachedScript is Data:
  Cache{watched: String, value: String}

def reuse_or_capture(same: Bool, previous: CachedScript, signature: String, actual: String) -> CachedScript:
  match same:
    case True{}: previous
    case False{}: Cache{signature, actual}

def capture(previous: CachedScript, +signature: String, actual: String) -> CachedScript:
  match previous:
    case Cache{+watched, +value}:
      reuse_or_capture(String.eq(watched, signature), Cache{watched, value}, signature, actual)

def captured(cache: CachedScript) -> String:
  match cache:
    case Cache{watched, value}: value

type Effects is Data:
  Effect{target_present: Bool, outside_output: String}

def clean(effect: Effects) -> Effects:
  match effect:
    case Effect{target_present, outside_output}: Effect{False{}, outside_output}

def outside(effect: Effects) -> String:
  match effect:
    case Effect{target_present, outside_output}: outside_output

def target_present(effect: Effects) -> Bool:
  match effect:
    case Effect{target_present, outside_output}: target_present

law app_only_does_not_enable_blue:
  {selected_features(False{}) == Feat{True{}, False{}} : Features}
def app_only_does_not_enable_blue():
  {==}

law selected_workspace_enables_both:
  {selected_features(True{}) == Feat{True{}, True{}} : Features}
def selected_workspace_enables_both():
  {==}

law clean_preserves_external_output:
  for present: Bool
  for +value: String
  {outside(clean(Effect{present, value})) == value : String}
def clean_preserves_external_output(present, value):
  {==}

def main() -> IO(Unit):
  IO.print(captured(capture(Cache{"watched", "first"}, "watched", "second")))
