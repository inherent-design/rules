import Base

type Snapshot is Data:
  Snap{id: String, parent: Maybe<&2, String>, reachable: List<&2, String>}

type Repository is Data:
  Repo{snapshots: List<&2, Snapshot>, available: List<&2, String>}

def any_pair(left: Bool, right: Bool) -> Bool:
  match left:
    case True{}: True{}
    case False{}: right

def negate(value: Bool) -> Bool:
  match value:
    case True{}: False{}
    case False{}: True{}

def keep(-A: Data, held: Bool, head: A, tail: List<&2, A>) -> List<&2, A>:
  match held:
    case True{}: Con{head, tail}
    case False{}: tail

def snapshot_id(snapshot: Snapshot) -> String:
  match snapshot:
    case Snap{id, parent, reachable}: id

def contains(+blob: String, values: List<&2, String>) -> Bool:
  match values:
    case Nil{}: False{}
    case Con{head, tail}:
      any_pair(String.eq(blob, head), contains(blob, tail))

def retained(+blob: String, snapshots: List<&2, Snapshot>) -> Bool:
  match snapshots:
    case Nil{}: False{}
    case Con{head, tail}:
      match head:
        case Snap{id, parent, reachable}:
          any_pair(contains(blob, reachable), retained(blob, tail))

def remove_snapshot(+gone: String, snapshots: List<&2, Snapshot>) -> List<&2, Snapshot>:
  match snapshots:
    case Nil{}: []
    case Con{+head, tail}:
      keep(Snapshot, negate(String.eq(gone, snapshot_id(head))), head, remove_snapshot(gone, tail))

def forget(gone: String, repo: Repository) -> Repository:
  match repo:
    case Repo{snapshots, available}:
      Repo{remove_snapshot(gone, snapshots), available}

def keep_reachable(+snapshots: List<&2, Snapshot>, available: List<&2, String>) -> List<&2, String>:
  match available:
    case Nil{}: []
    case Con{+head, tail}:
      keep(String, retained(head, snapshots), head, keep_reachable(snapshots, tail))

# Selected --max-unused 0 profile with complete stationary roots. The false
# branch is the proposed safe admission rule; unsafe no-lock/partial modes
# require separate models and are not silently described by this function.
def prune(exclusive: Bool, repo: Repository) -> Repository:
  match exclusive:
    case False{}: repo
    case True{}:
      match repo:
        case Repo{+snapshots, available}:
          Repo{snapshots, keep_reachable(snapshots, available)}

def backing(repo: Repository) -> List<&2, String>:
  match repo:
    case Repo{snapshots, available}: available

def lines(values: List<&2, String>) -> String:
  match values:
    case Nil{}: ""
    case Con{head, tail}: head ++ "\n" ++ lines(tail)

law forgetting_preserves_data:
  for gone: String
  for snapshots: List<&2, Snapshot>
  for +available: List<&2, String>
  {backing(forget(gone, Repo{snapshots, available})) == available : List<&2, String>}
def forgetting_preserves_data(gone, snapshots, available):
  {==}

law lack_of_exclusive_preserves_data:
  for +repo: Repository
  {prune(False{}, repo) == repo : Repository}
def lack_of_exclusive_preserves_data(repo):
  {==}

law lineage_is_not_a_data_root:
  {retained("old", [Snap{"B", Some{"A"}, ["shared", "new"]}]) == False{} : Bool}
def lineage_is_not_a_data_root():
  {==}

def main() -> IO(Unit):
  do IO<Unit>:
    repo : Repository = Repo{[Snap{"A", None{}, ["old", "shared"]}, Snap{"B", Some{"A"}, ["shared", "new"]}], ["old", "shared", "new"]}
    IO.print(lines(backing(prune(True{}, forget("A", repo)))))
