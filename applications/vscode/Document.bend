import Base

type DocPoint is Data:
  PointSnapshot{key: String, text: String}

type DocEditor is Data:
  BufferState{version: Nat, current: DocPoint, saved: DocPoint, disk: String}

def point_key(point: DocPoint) -> String:
  match point:
    case PointSnapshot{key, text}: key

def point_text(point: DocPoint) -> String:
  match point:
    case PointSnapshot{key, text}: text

def dirty(editor: DocEditor) -> Bool:
  match editor:
    case BufferState{version, current, saved, disk}:
      Bool.not(String.eq(point_key(current), point_key(saved)))

def edit(editor: DocEditor, point: DocPoint) -> DocEditor:
  match editor:
    case BufferState{version, current, saved, disk}:
      BufferState{Nat.add(version, 1n), point, saved, disk}

def save(editor: DocEditor) -> DocEditor:
  match editor:
    case BufferState{version, +current, saved, disk}:
      BufferState{version, current, current, point_text(current)}

def external_decision(was_dirty: Bool, editor: DocEditor, +point: DocPoint) -> DocEditor:
  match was_dirty:
    case True{}:
      match editor:
        case BufferState{version, current, saved, disk}:
          BufferState{version, current, saved, point_text(point)}
    case False{}:
      match editor:
        case BufferState{version, current, saved, disk}:
          BufferState{Nat.add(version, 1n), point, point, point_text(point)}

def external_write(+editor: DocEditor, point: DocPoint) -> DocEditor:
  external_decision(dirty(editor), editor, point)

def revert(editor: DocEditor, +key: String) -> DocEditor:
  match editor:
    case BufferState{version, current, saved, +disk}:
      BufferState{Nat.add(version, 1n), PointSnapshot{key, disk}, PointSnapshot{key, disk}, disk}

def version(editor: DocEditor) -> Nat:
  match editor:
    case BufferState{version, current, saved, disk}: version

def current_point(editor: DocEditor) -> DocPoint:
  match editor:
    case BufferState{version, current, saved, disk}: current

def saved_point(editor: DocEditor) -> DocPoint:
  match editor:
    case BufferState{version, current, saved, disk}: saved

def disk_text(editor: DocEditor) -> String:
  match editor:
    case BufferState{version, current, saved, disk}: disk

law save_preserves_event_version:
  for +number: Nat
  for current: DocPoint
  for saved: DocPoint
  for disk: String
  {version(save(BufferState{number, current, saved, disk})) == number : Nat}
def save_preserves_event_version(number, current, saved, disk):
  {==}

law serial_save_aligns_points:
  for version: Nat
  for +current: DocPoint
  for saved: DocPoint
  for disk: String
  {current_point(save(BufferState{version, current, saved, disk})) == saved_point(save(BufferState{version, current, saved, disk})) : DocPoint}
def serial_save_aligns_points(version, current, saved, disk):
  {==}

def main() -> IO(Unit):
  IO.print("Serial document model; use retained native comparison.")
