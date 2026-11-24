namespace ApplicationStudy.Workspaces

inductive Manager | npm | pnpm | yarn
  deriving BEq, DecidableEq, Repr

structure Package where
  id : Nat
  name : String
  dependencies : List Nat
  script : Bool
  deriving Repr

/-- This band's admitted graph has root 0 and four generated members.
    The model is not a glob, semver, command-line, or lockfile decoder. -/
def nodes (packages : List Package) : List Nat := packages.map (·.id)

def expand (packages : List Package) (reverse : Bool) (selected : List Nat) : List Nat :=
  (selected ++ packages.flatMap (fun p =>
    if reverse then
      if p.dependencies.any selected.contains then [p.id] else []
    else if selected.contains p.id then p.dependencies else [])).eraseDups

def closure (packages : List Package) (reverse : Bool) (selected : List Nat) : List Nat :=
  (List.range 8).foldl (fun current _ => expand packages reverse current) selected

/-- root,members,all,exact-a,a+dependencies,b+dependents,missing selector.
    Native adapters admit only the corresponding captured request profiles. -/
def select (packages : List Package) (mode : Nat) : List Nat :=
  let wanted := match mode with
    | 0 => [0] | 1 => (nodes packages).filter (· != 0)
    | 2 => nodes packages | 3 => [1]
    | 4 => closure packages false [1]
    | 5 => closure packages true [2]
    | _ => []
  (nodes packages).filter wanted.contains

def ready (topological : Bool) (selected passed : List Nat) (p : Package) : Bool :=
  !topological || p.dependencies.all (fun d => !selected.contains d || passed.contains d)

structure Request where
  manager : Manager
  packages : List Package
  mode : Nat
  topological : Bool
  bail : Bool
  ifPresent : Bool
  failB : Bool
  deriving Repr

structure Work where
  selected : List Nat := []
  pending : List Package := []
  queue : List Nat := []
  passed : List Nat := []
  started : List Nat := []
  failed : List Nat := []
  blocked : List Nat := []
  missing : List Nat := []
  code : Nat := 0
  deriving Repr

/-- A failed dependency blocks pnpm's later dependents even without bail.
    No-sort/parallel/tasks declarations and multiple scripts are not modeled. -/
def dropBlocked (r : Request) (w : Work) : Work :=
  if r.manager == .pnpm && r.topological then
    let doomed := w.pending.filter fun p =>
      (closure (r.packages.filter (fun p => w.selected.contains p.id)) false [p.id]).any w.failed.contains
    let ids := nodes doomed
    { w with pending := w.pending.filter (fun p => !ids.contains p.id)
             queue := w.queue.filter (fun id => !ids.contains id)
             blocked := w.blocked ++ ids }
  else w

def runSteps (r : Request) : Nat → Work → Work
  | 0, w => w
  | fuel + 1, w =>
    let w := dropBlocked r w
    let available := w.pending.filter (ready r.topological w.selected w.passed)
    let discovered := nodes available
    let fifo := r.manager == .pnpm
    let queue := if fifo then w.queue ++ discovered.filter (fun id => !w.queue.contains id)
                 else discovered
    match queue with
    | [] => w
    | id :: tail =>
      match w.pending.find? (fun p => p.id == id) with
      | none => w
      | some p =>
        let next := { w with pending := w.pending.filter (fun p => p.id != id)
                             queue := tail }
        if !p.script then
          runSteps r fuel { next with
            passed := next.passed ++ [id]
            missing := next.missing ++ [id]
            code := if r.manager == .npm && !r.ifPresent then 1 else next.code }
        else
          let failed := r.failB && id == 2
          let next := { next with started := next.started ++ [id]
                                  passed := if failed then next.passed else next.passed ++ [id]
                                  failed := if failed then next.failed ++ [id] else next.failed
                                  code := if failed then (if r.manager == .npm then 7 else 1) else next.code }
          if failed && r.bail then next else runSteps r fuel next

def run (r : Request) : Work :=
  let selected := select r.packages r.mode
  let packages := r.packages.filter (fun p => selected.contains p.id)
  let ordered := if r.manager == .yarn then packages.mergeSort (fun a b => a.name ≤ b.name) else packages
  let runnable := if r.manager == .yarn then ordered.filter (·.script) else ordered
  let initial : Work := { selected := selected, pending := runnable }
  if selected.isEmpty || (r.manager == .pnpm && !packages.any (·.script)) then
    { initial with code := 1 }
  else runSteps r 16 initial

theorem exact_selection_does_not_expand_dependencies (packages : List Package) :
    select packages 3 = (nodes packages).filter ([1].contains) := rfl

theorem root_selection_is_explicit (packages : List Package) :
    select packages 0 = (nodes packages).filter ([0].contains) := rfl

theorem member_selection_excludes_root (packages : List Package) :
    !(select packages 1).contains 0 = true := by
  simp [select, nodes, List.contains_eq_mem, List.mem_filter]

theorem ready_requires_selected_dependency (selected passed : List Nat) (p : Package)
    (h : ready true selected passed p = true) (dep : Nat)
    (hd : dep ∈ p.dependencies) (hs : selected.contains dep = true) :
    passed.contains dep = true := by
  simp only [ready, Bool.not_true, Bool.false_or] at h
  have required := (List.all_eq_true.mp h) dep hd
  have membership : dep ∈ selected := by simpa using hs
  simpa [membership] using required

theorem dependency_agnostic_ready (selected passed : List Nat) (p : Package) :
    ready false selected passed p = true := rfl

theorem empty_selection_has_no_started_script (r : Request)
    (h : (select r.packages r.mode).isEmpty = true) : (run r).started = [] := by
  simp [run, h]

end ApplicationStudy.Workspaces
