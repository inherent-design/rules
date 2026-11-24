import Base

# Native adapter supplies independently checked key equality and time ordering.
# This is a keep-last-one decision projection, not a grouping or JSON decoder.
def newer_same_group(same_key: Bool, later: Bool) -> Bool:
  Bool.and(same_key,later)

def retained(has_newer: Bool, tagged: Bool) -> Bool:
  Bool.or(Bool.not(has_newer),tagged)

def removed(has_newer: Bool, tagged: Bool) -> Bool:
  Bool.not(retained(has_newer,tagged))

def filter_match(host: Bool, paths: Bool, tags: Bool) -> Bool:
  Bool.and(host,Bool.and(paths,tags))

law latest_remains_kept:
  for tagged: Bool
  {retained(False{},tagged) == True{} : Bool}
def latest_remains_kept(tagged):
  {==}

law keep_tag_preserves_older_snapshot:
  for newer: Bool
  {retained(newer,True{}) == True{} : Bool}
def keep_tag_preserves_older_snapshot(newer):
  match newer:
    case True{}:
      {==}
    case False{}:
      {==}

law a_newer_different_group_does_not_displace:
  for later: Bool
  {newer_same_group(False{},later) == False{} : Bool}
def a_newer_different_group_does_not_displace(later):
  {==}

law keep_remove_are_complements:
  for +newer: Bool
  for +tagged: Bool
  {Bool.xor(retained(newer,tagged),removed(newer,tagged)) == True{} : Bool}
def keep_remove_are_complements(newer,tagged):
  match newer:
    case True{}:
      match tagged:
        case True{}:
          {==}
        case False{}:
          {==}
    case False{}:
      {==}

def main() -> IO(Unit):
  IO.print("Group-relative newest and independent keep-tag policy; preview is not deletion.")
