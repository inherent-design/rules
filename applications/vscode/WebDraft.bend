import Base

type UntitledObservation is Data:
  UntitledView{resource: String, text: String, dirty: Bool, file_receipt: Maybe<&2, String>}

def restored_untitled(resource: String, text: String) -> UntitledObservation:
  UntitledView{resource, text, True{}, None{}}

def rendered_text(observation: UntitledObservation) -> String:
  match observation:
    case UntitledView{resource, text, dirty, file_receipt}: text

def receipt(observation: UntitledObservation) -> Maybe<&2, String>:
  match observation:
    case UntitledView{resource, text, dirty, file_receipt}: file_receipt

law restoration_retains_text:
  for resource: String
  for +text: String
  {rendered_text(restored_untitled(resource, text)) == text : String}
def restoration_retains_text(resource, text):
  {==}

law restoration_establishes_no_file_receipt:
  for resource: String
  for text: String
  {receipt(restored_untitled(resource, text)) == None{} : Maybe<&2, String>}
def restoration_establishes_no_file_receipt(resource, text):
  {==}

def main() -> IO(Unit):
  IO.print("Restored untitled evidence is distinct from a file-write receipt.")
