namespace ApplicationStudy.Vscode

structure Point where
  key : String
  text : String
  deriving DecidableEq, Repr

/-- Serial native-file projection. The event counter, undo/save-point identity,
    and independently observed backing are deliberately separate values. -/
structure Document where
  version : Nat
  current : Point
  saved : Point
  disk : String
  deriving DecidableEq, Repr

def dirty (d : Document) : Bool := d.current.key != d.saved.key

def edit (d : Document) (point : Point) : Document :=
  { d with version := d.version + 1, current := point }

/-- Only a serial, successful write with no concurrent mutation is modeled. -/
def save (d : Document) : Document := { d with saved := d.current, disk := d.current.text }

/-- Caller supplies an admitted undo/redo point. This does not implement the
    editor's stack grouping, branching, capacity, or persistence. -/
def historyMove (d : Document) (point : Point) : Document := edit d point

/-- Settled external-file notification: dirty buffers retain their text;
    clean buffers reload. No immediate watcher-delivery guarantee is implied. -/
def externalWrite (d : Document) (point : Point) : Document :=
  if dirty d then { d with disk := point.text }
  else ⟨d.version + 1, point, point, point.text⟩

def revert (d : Document) (key : String) : Document :=
  let point := Point.mk key d.disk
  ⟨d.version + 1, point, point, d.disk⟩

theorem save_preserves_event_version (d : Document) : (save d).version = d.version := rfl
theorem serial_save_aligns_points (d : Document) : (save d).current = (save d).saved := rfl
theorem serial_save_is_clean (d : Document) : dirty (save d) = false := by simp [dirty, save]
theorem history_move_advances_version (d : Document) (p : Point) :
    (historyMove d p).version = d.version + 1 := rfl
theorem history_return_to_saved_is_clean (d : Document) :
    dirty (historyMove d d.saved) = false := by simp [dirty, historyMove, edit]
theorem dirty_external_write_preserves_buffer (d : Document) (p : Point) (h : dirty d = true) :
    (externalWrite d p).current = d.current := by simp [externalWrite, h]
theorem revert_observes_backing (d : Document) (key : String) :
    (revert d key).current.text = d.disk := rfl

end ApplicationStudy.Vscode
