namespace ApplicationStudy.VscodeWeb

/-- Evidence projection of an unassociated untitled working copy. The resource
    key is an admitted logical reference, not its changing display caption. -/
structure DraftObservation where
  resourceKey : String
  renderedText : String
  dirty : Bool
  fileWriteReceipt : Option String
  deriving DecidableEq, Repr

/-- Successful backup restoration, not a guarantee that backup will be made,
    retained, or available after another browser/process/storage event. -/
def restoredUntitled (resource text : String) : DraftObservation :=
  ⟨resource, text, true, none⟩

theorem restoration_retains_resource (r text : String) :
    (restoredUntitled r text).resourceKey = r := rfl
theorem restoration_retains_rendered_text (r text : String) :
    (restoredUntitled r text).renderedText = text := rfl
theorem restored_untitled_remains_dirty (r text : String) :
    (restoredUntitled r text).dirty = true := rfl
theorem restoration_establishes_no_file_write_receipt (r text : String) :
    (restoredUntitled r text).fileWriteReceipt = none := rfl

end ApplicationStudy.VscodeWeb
