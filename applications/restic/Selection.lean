namespace ApplicationStudy.ResticSelection

structure Snapshot where
  id : String
  host : String
  paths : List String
  tags : List String
  rank : Nat
  deriving BEq, DecidableEq, Repr

structure Grouping where
  host : Bool
  paths : Bool
  tags : Bool
  deriving BEq, DecidableEq, Repr

def ungrouped : Grouping := ⟨false, false, false⟩
def hostPaths : Grouping := ⟨true, true, false⟩

def sameGroup (group : Grouping) (a b : Snapshot) : Bool :=
  (!group.host || a.host == b.host) &&
  (!group.paths || a.paths.mergeSort == b.paths.mergeSort) &&
  (!group.tags || a.tags.mergeSort == b.tags.mergeSort)

/-- `snapshots --latest` falls back to host/path selection even when display
    grouping is disabled. `forget` uses the requested group directly. -/
def inspectionGrouping (group : Grouping) : Grouping :=
  if group.host || group.paths || group.tags then group else hostPaths

/-- The captured timestamps have a unique total order. Equal-time tie behavior,
    calendar buckets and arbitrary retention counts remain outside this band. -/
def newestInGroup (snapshots : List Snapshot) (group : Grouping) (candidate : Snapshot) : Bool :=
  !(snapshots.any fun other => sameGroup group candidate other && candidate.rank < other.rank)

def latest (snapshots : List Snapshot) (group : Grouping) : List Snapshot :=
  snapshots.filter (newestInGroup snapshots group)

/-- Nonempty tag spellings only. restic's special empty-string untagged selector
    requires a separate case and is refused by this band's input decoder. -/
def tagMatch (groups : List (List String)) (tags : List String) : Bool :=
  groups.isEmpty || groups.any (fun group => group.all tags.contains)

structure Filter where
  hosts : List String
  paths : List String
  tags : List (List String)
  deriving Repr

def matchesFilter (filter : Filter) (snapshot : Snapshot) : Bool :=
  (filter.hosts.isEmpty || filter.hosts.contains snapshot.host) &&
  filter.paths.all snapshot.paths.contains && tagMatch filter.tags snapshot.tags

def select (snapshots : List Snapshot) (filter : Filter) : List Snapshot :=
  snapshots.filter (matchesFilter filter)

def kept (snapshots : List Snapshot) (group : Grouping) (keepTags : List (List String)) (snapshot : Snapshot) : Bool :=
  newestInGroup snapshots group snapshot || (!keepTags.isEmpty && tagMatch keepTags snapshot.tags)

def keep (snapshots : List Snapshot) (group : Grouping) (tags : List (List String)) : List Snapshot :=
  snapshots.filter (kept snapshots group tags)

def remove (snapshots : List Snapshot) (group : Grouping) (tags : List (List String)) : List Snapshot :=
  snapshots.filter (fun snapshot => !(kept snapshots group tags snapshot))

theorem no_grouping_has_one_key (a b : Snapshot) : sameGroup ungrouped a b = true := rfl

theorem disabled_display_grouping_still_selects_per_host_path : inspectionGrouping ungrouped = hostPaths := rfl

theorem selected_snapshot_is_an_input (snapshots : List Snapshot) (filter : Filter) (snapshot : Snapshot)
    (h : snapshot ∈ select snapshots filter) : snapshot ∈ snapshots := (List.mem_filter.mp h).1

theorem retained_snapshot_is_an_input (snapshots : List Snapshot) (group : Grouping)
    (tags : List (List String)) (snapshot : Snapshot) (h : snapshot ∈ keep snapshots group tags) :
    snapshot ∈ snapshots := (List.mem_filter.mp h).1

theorem tag_preservation_does_not_remove_latest (snapshots : List Snapshot) (group : Grouping)
    (tags : List (List String)) (snapshot : Snapshot) (h : newestInGroup snapshots group snapshot = true) :
    kept snapshots group tags snapshot = true := by simp [kept, h]

theorem keep_and_remove_are_disjoint (snapshots : List Snapshot) (group : Grouping)
    (tags : List (List String)) (snapshot : Snapshot)
    (h₁ : snapshot ∈ keep snapshots group tags) : snapshot ∉ remove snapshots group tags := by
  intro h₂
  have hk := (List.mem_filter.mp h₁).2
  have hr := (List.mem_filter.mp h₂).2
  simp [hk] at hr

theorem every_input_has_a_preview_disposition (snapshots : List Snapshot) (group : Grouping)
    (tags : List (List String)) (snapshot : Snapshot) (h : snapshot ∈ snapshots) :
    snapshot ∈ keep snapshots group tags ∨ snapshot ∈ remove snapshots group tags := by
  cases hk : kept snapshots group tags snapshot with
  | false => exact Or.inr (List.mem_filter.mpr ⟨h, by simp [hk]⟩)
  | true => exact Or.inl (List.mem_filter.mpr ⟨h, hk⟩)

end ApplicationStudy.ResticSelection
