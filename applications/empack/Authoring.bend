import Base

type DraftEditor is Data:
  Editor{epoch: Nat, current: Nat, saved: Maybe<&2, Nat>, saved_revision: Nat}

def image_matches(saved: Maybe<&2, Nat>, current: Nat) -> Bool:
  match saved:
    case None{}: False{}
    case Some{value}: Nat.is_eq(value, current)

def dirty(editor: DraftEditor) -> Bool:
  match editor:
    case Editor{epoch, current, saved, saved_revision}:
      Bool.not(image_matches(saved, current))

def edit_to(editor: DraftEditor, image: Nat) -> DraftEditor:
  match editor:
    case Editor{epoch, current, saved, saved_revision}:
      Editor{Nat.add(epoch, 1n), image, saved, saved_revision}

def complete_decision(newer: Bool, editor: DraftEditor, revision: Nat, image: Nat) -> DraftEditor:
  match newer:
    case False{}: editor
    case True{}:
      match editor:
        case Editor{epoch, current, saved, saved_revision}:
          Editor{epoch, current, Some{image}, revision}

def save_completed(+editor: DraftEditor, +revision: Nat, image: Nat) -> DraftEditor:
  match editor:
    case Editor{epoch, current, saved, +saved_revision}:
      complete_decision(Nat.is_gt(revision, saved_revision), Editor{epoch, current, saved, saved_revision}, revision, image)

def apply_receipt(accepted: Bool, editor: DraftEditor, revision: Nat, image: Nat) -> DraftEditor:
  match accepted:
    case False{}: editor
    case True{}: save_completed(editor, revision, image)

def accept_save(project: Nat, incarnation: Nat, receipt_project: Nat, receipt_incarnation: Nat, confirmed: Bool, editor: DraftEditor, revision: Nat, image: Nat) -> DraftEditor:
  apply_receipt(Bool.and(Bool.and(confirmed, Nat.is_eq(project, receipt_project)), Nat.is_eq(incarnation, receipt_incarnation)), editor, revision, image)

def current_image(editor: DraftEditor) -> Nat:
  match editor:
    case Editor{epoch, current, saved, saved_revision}: current

def epoch(editor: DraftEditor) -> Nat:
  match editor:
    case Editor{epoch, current, saved, saved_revision}: epoch

def saved_image(editor: DraftEditor) -> Maybe<&2, Nat>:
  match editor:
    case Editor{epoch, current, saved, saved_revision}: saved

def saved_revision(editor: DraftEditor) -> Nat:
  match editor:
    case Editor{epoch, current, saved, saved_revision}: saved_revision

def accepts_background(+editor: DraftEditor, basis_epoch: Nat, basis_image: Nat) -> Bool:
  Bool.and(Nat.is_eq(epoch(editor), basis_epoch), Nat.is_eq(current_image(editor), basis_image))

def all_held(required: List<&2, Nat>, +held: List<&2, Nat>) -> Bool:
  match required:
    case Nil{}: True{}
    case Con{head, tail}:
      Bool.and(List.contains(Nat, Nat.is_eq, held, head), all_held(tail, held))

# Validity is deliberately absent: saving raw work does not execute it.
def can_save(available: List<&2, Nat>, held: List<&2, Nat>) -> Bool:
  all_held(available, held)

def can_export(valid: Bool, complete: Bool, capable: Bool, required: List<&2, Nat>, held: List<&2, Nat>) -> Bool:
  Bool.and(Bool.and(Bool.and(valid, complete), capable), all_held(required, held))

law edit_advances_epoch:
  for +number: Nat
  for current: Nat
  for saved: Maybe<&2, Nat>
  for saved_revision: Nat
  for image: Nat
  {epoch(edit_to(Editor{number, current, saved, saved_revision}, image)) == Nat.add(number, 1n) : Nat}
def edit_advances_epoch(number, current, saved, saved_revision, image):
  {==}

law equal_naturals:
  for +number: Nat
  {Nat.is_eq(number, number) == True{} : Bool}
def equal_naturals(number):
  match number:
    case 0n: {==}
    case 1n+previous: equal_naturals(previous)

law undo_to_saved_is_clean:
  for number: Nat
  for current: Nat
  for +saved: Nat
  for saved_revision: Nat
  {dirty(edit_to(Editor{number, current, Some{saved}, saved_revision}, saved)) == False{} : Bool}
def undo_to_saved_is_clean(number, current, saved, saved_revision):
  Equal.cong(Bool, Bool, Bool.not, Nat.is_eq(saved, saved), True{}, equal_naturals(saved))

law invalid_authoring_blocks_export:
  for complete: Bool
  for capable: Bool
  for required: List<&2, Nat>
  for held: List<&2, Nat>
  {can_export(False{}, complete, capable, required, held) == False{} : Bool}
def invalid_authoring_blocks_export(complete, capable, required, held):
  {==}

def main() -> IO(Unit):
  IO.print("Proposed authoring lifecycle; no native or browser empack implementation.")
