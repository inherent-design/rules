import Base

type PackFile is Data:
  Entry{path: String, hash: String}

# Decision model only. The generic list plan and staging guard live in Lean.
def match_fields(path_aware: Bool, path_same: Bool, hash_same: Bool) -> Bool:
  match path_aware:
    case False{}: hash_same
    case True{}: Bool.and(path_same, hash_same)

def can_reuse(path_aware: Bool, a: PackFile, b: PackFile) -> Bool:
  match a:
    case Entry{path_a, hash_a}:
      match b:
        case Entry{path_b, hash_b}:
          match_fields(path_aware, String.eq(path_a, path_b), String.eq(hash_a, hash_b))

law hash_mode_ignores_path:
  for path_same: Bool
  for +hash_same: Bool
  {match_fields(False{}, path_same, hash_same) == hash_same : Bool}
def hash_mode_ignores_path(path_same, hash_same):
  {==}

law changed_path_not_reused_by_proposal:
  for hash_same: Bool
  {match_fields(True{}, False{}, hash_same) == False{} : Bool}
def changed_path_not_reused_by_proposal(hash_same):
  {==}

def main() -> IO(Unit):
  IO.print(Bool.pick(String, can_reuse(False{}, Entry{"old", "same"}, Entry{"new", "same"}), "true", "false"))
