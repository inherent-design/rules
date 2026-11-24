import Base

# Decision projection. index repair is not payload restoration.
type Scope is Data:
  Metadata{}
  All{}
  HalfFirst{}
  HalfSecond{}

def selected(scope: Scope, bucket_one: Bool) -> Bool:
  match scope:
    case Metadata{}: False{}
    case All{}: True{}
    case HalfFirst{}: Bool.not(bucket_one)
    case HalfSecond{}: bucket_one

def check(index_ok: Bool, structure_ok: Bool, data_selected: Bool, data_healthy: Bool) -> Bool:
  Bool.and(Bool.and(index_ok,structure_ok),Bool.or(Bool.not(data_selected),data_healthy))

def rebuilt_index(headers_recoverable: Bool, index_ok: Bool) -> Bool:
  Bool.or(headers_recoverable,index_ok)

def repaired_body(body_healthy: Bool) -> Bool:
  body_healthy

law metadata_pass_is_not_body_pass:
  {check(True{},True{},False{},False{}) == True{} : Bool}
def metadata_pass_is_not_body_pass():
  {==}

law data_fault_is_detected_when_selected:
  {check(True{},True{},True{},False{}) == False{} : Bool}
def data_fault_is_detected_when_selected():
  {==}

law metadata_repair_does_not_restore_data:
  {repaired_body(False{}) == False{} : Bool}
def metadata_repair_does_not_restore_data():
  {==}

law index_rebuild_needs_recoverable_headers:
  {rebuilt_index(False{},False{}) == False{} : Bool}
def index_rebuild_needs_recoverable_headers():
  {==}

def main() -> IO(Unit):
  IO.print("Requested read scope,index reconstruction,and unchanged body integrity.")
