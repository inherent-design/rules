import Base
import ./Authoring.bend as A

type PStored is Data:
  PStored{revision: Nat, image: Maybe<&2,Nat>}
type PResult is Data:
  PResult{stored: PStored, editor: A.DraftEditor, status: Nat}
def complete(+s: PStored,+e: A.DraftEditor,+image: Nat,reply: Bool) -> PResult:
  match s:
    case PStored{r,_}:
      +next=Nat.add(1n,r)
      Bool.pick(PResult,reply,PResult{PStored{next,Some{image}},A.save_completed(e,next,image),1n},PResult{PStored{next,Some{image}},e,2n})
def admitted(+s: PStored,+e: A.DraftEditor,+expected: Nat,+image: Nat,+boundary: Nat) -> PResult:
  match s:
    case PStored{r,_}:
      after_cas=Bool.pick(PResult,Nat.is_eq(expected,r),complete(s,e,image,Bool.not(Nat.is_eq(boundary,2n))),PResult{s,e,3n})
      Bool.pick(PResult,Nat.is_eq(boundary,1n),PResult{s,e,2n},after_cas)
def save(+s: PStored,+e: A.DraftEditor,expected: Nat,image: Nat,available: List<&2,Nat>,held: List<&2,Nat>,+boundary: Nat) -> PResult:
  verified=Bool.pick(PResult,A.can_save(available,held),admitted(s,e,expected,image,boundary),PResult{s,e,4n})
  Bool.pick(PResult,Nat.is_eq(boundary,0n),PResult{s,e,2n},verified)
def reopen(+s: PStored,+e: A.DraftEditor,verified: Bool) -> PResult:
  match s:
    case PStored{_,None{}}: PResult{s,e,4n}
    case PStored{+revision,Some{+image}}:
      epoch=Nat.add(1n,A.epoch(e))
      Bool.pick(PResult,verified,PResult{s,A.Editor{epoch,image,Some{image},revision},5n},PResult{s,e,4n})
def has_image(value: Maybe<&2,Nat>) -> Bool:
  match value:
    case None{}: False{}
    case Some{_}: True{}
def backup(+s: PStored,e: A.DraftEditor,verified: Bool,finalized: Bool) -> PResult:
  match s:
    case PStored{_,image}:
      available=has_image(image)
      PResult{s,e,Bool.pick(Nat,Bool.and(available,Bool.and(verified,finalized)),6n,4n)}
def after_reopen(r: PResult,available: List<&2,Nat>,held: List<&2,Nat>,boundary: Nat) -> PResult:
  match r:
    case PResult{s,+e,_}: save(s,e,A.saved_revision(e),A.current_image(e),available,held,boundary)
def reopen_then_save(s: PStored,e: A.DraftEditor,verified: Bool,available: List<&2,Nat>,held: List<&2,Nat>,boundary: Nat) -> PResult:
  after_reopen(reopen(s,e,verified),available,held,boundary)
def observe(s: PStored,e: A.DraftEditor) -> PResult:
  PResult{s,e,0n}
def maybe_text(v: Maybe<&2,Nat>) -> String:
  match v:
    case None{}: "-"
    case Some{n}: Nat.show(n)
def render(r: PResult) -> String:
  match r:
    case PResult{PStored{rev,image},+e,status}:
      Nat.show(rev) ++ "/" ++ maybe_text(image) ++ "/" ++ Nat.show(A.epoch(e)) ++ "/" ++ Nat.show(A.current_image(e)) ++ "/" ++ maybe_text(A.saved_image(e)) ++ "/" ++ Nat.show(A.saved_revision(e)) ++ "/" ++ Nat.show(status)

law after_commit_without_reply_keeps_UI_basis:
  {render(save(PStored{2n,Some{10n}},A.Editor{5n,20n,Some{10n},2n},2n,20n,[1n],[1n],2n)) == "3/20/5/20/10/2/2" : String}
def after_commit_without_reply_keeps_UI_basis():
  {==}
law retained_before_metadata_keeps_old_root:
  {render(save(PStored{2n,Some{10n}},A.Editor{5n,20n,Some{10n},2n},2n,20n,[1n],[1n],1n)) == "2/10/5/20/10/2/2" : String}
def retained_before_metadata_keeps_old_root():
  {==}
law stale_request_preserves_state:
  {render(save(PStored{2n,Some{10n}},A.Editor{5n,20n,Some{10n},1n},1n,20n,[1n],[1n],3n)) == "2/10/5/20/10/1/3" : String}
def stale_request_preserves_state():
  {==}
law missing_backing_refuses_without_metadata:
  {render(save(PStored{2n,Some{10n}},A.Editor{5n,20n,Some{10n},2n},2n,20n,[1n,2n],[1n],3n)) == "2/10/5/20/10/2/4" : String}
def missing_backing_refuses_without_metadata():
  {==}
law same_image_later_revision:
  {render(save(PStored{1n,Some{10n}},A.Editor{5n,10n,Some{10n},1n},1n,10n,[1n],[1n],3n)) == "2/10/5/10/10/2/1" : String}
def same_image_later_revision():
  {==}
law reopen_uses_current_storage:
  {render(reopen(PStored{4n,Some{20n}},A.Editor{8n,30n,Some{10n},3n},True{})) == "4/20/9/20/20/4/5" : String}
def reopen_uses_current_storage():
  {==}
