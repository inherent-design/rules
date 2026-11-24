import Base

# Necessary raw-document gate only, not full native publication authority.
def may_record(valid: Bool, approved: Bool, other: Bool, author_same: Bool, binding_same: Bool, lock_same: Bool) -> Bool:
  Bool.and(Bool.and(Bool.and(valid,approved),other),Bool.and(Bool.and(author_same,binding_same),lock_same))

def current(valid: Bool, semantic_same: Bool) -> Bool:
  Bool.and(valid,semantic_same)

law author_comment_can_refuse_old_work:
  {may_record(True{},True{},True{},False{},True{},True{}) == False{} : Bool}
def author_comment_can_refuse_old_work():
  {==}

law binding_absence_is_a_precondition:
  {may_record(True{},True{},True{},True{},False{},True{}) == False{} : Bool}
def binding_absence_is_a_precondition():
  {==}

law matching_documents_do_not_grant_other_permissions:
  {may_record(True{},True{},False{},True{},True{},True{}) == False{} : Bool}
def matching_documents_do_not_grant_other_permissions():
  {==}

law invalid_input_is_not_current:
  for semantic_same: Bool
  {current(False{},semantic_same) == False{} : Bool}
def invalid_input_is_not_current(semantic_same):
  {==}

def main() -> IO(Unit):
  IO.print("Semantic lock currency and exact raw document preconditions.")
