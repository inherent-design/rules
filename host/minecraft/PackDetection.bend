import Base

# Kind: missing0, regular1, directory2, link3, other4.
# Factory mode: returns0, null1, authored IOException2.
# Pure case-local bindings, not a filesystem resolver or writer.
type PDNode is Data:
  Node{kind: Nat,binding: Nat,zip: Bool,metadata: Bool,links: Nat}
type PDInput is Data:
  Input{entry: PDNode,raw: PDNode,parent: PDNode,absolute: Bool,allow: Bool,mode: Nat}
type PDOutcome is Data:
  Outcome{error: Nat,value: Nat,factory: Nat,binding: Nat,issues: Nat,matchers: Nat}

def pd_none() -> PDOutcome:
  Outcome{0n,0n,0n,0n,0n,0n}
def pd_invoke(+mode: Nat,+kind: Nat,+binding: Nat) -> PDOutcome:
  Bool.pick(PDOutcome,Nat.is_eq(mode,2n),Outcome{2n,0n,kind,binding,0n,0n},
    Outcome{0n,Bool.pick(Nat,Nat.is_eq(mode,1n),0n,kind),kind,binding,0n,0n})
def pd_with_matchers(result: PDOutcome,matchers: Nat) -> PDOutcome:
  match result:
    case Outcome{error,value,factory,binding,issues,previous}: Outcome{error,value,factory,binding,issues,matchers}
def pd_add_matcher(result: PDOutcome) -> PDOutcome:
  match result:
    case Outcome{error,value,factory,binding,issues,previous}: Outcome{error,value,factory,binding,issues,Nat.add(previous,1n)}
def pd_kind(node: PDNode) -> Nat:
  match node:
    case Node{kind,binding,zip,metadata,links}: kind
def pd_classify(node: PDNode,+allow: Bool,+mode: Nat) -> PDOutcome:
  match node:
    case Node{+kind,+binding,zip,metadata,+links}:
      +issues=Bool.pick(Nat,allow,0n,links)
      Bool.pick(PDOutcome,Nat.is_eq(kind,2n),
        Bool.pick(PDOutcome,Nat.is_eq(issues,0n),
          pd_with_matchers(Bool.pick(PDOutcome,metadata,pd_invoke(mode,2n,binding),pd_none()),links),
          Outcome{0n,0n,0n,0n,issues,links}),
        Bool.pick(PDOutcome,Bool.and(Nat.is_eq(kind,1n),zip),pd_invoke(mode,1n,binding),pd_none()))
def pd_follow(+target: PDNode,+allow: Bool,mode: Nat) -> PDOutcome:
  Bool.pick(PDOutcome,allow,
    Bool.pick(PDOutcome,Nat.is_eq(pd_kind(target),0n),Outcome{1n,0n,0n,0n,0n,1n},pd_add_matcher(pd_classify(target,allow,mode))),
    Outcome{0n,0n,0n,0n,1n,1n})
def pd_run(input: PDInput,parentAnchored: Bool) -> PDOutcome:
  match input:
    case Input{+entry,raw,parent,absolute,+allow,+mode}:
      target=Bool.pick(PDNode,Bool.and(parentAnchored,Bool.not(absolute)),parent,raw)
      Bool.pick(PDOutcome,Nat.is_eq(pd_kind(entry),3n),pd_follow(target,allow,mode),pd_classify(entry,allow,mode))

law pd_missing_has_no_factory:
  {pd_classify(Node{0n,0n,False{},False{},0n},True{},2n) == Outcome{0n,0n,0n,0n,0n,0n} : PDOutcome}
def pd_missing_has_no_factory():
  {==}
law pd_suffix_refusal_has_no_factory:
  {pd_classify(Node{1n,1n,False{},False{},0n},True{},0n) == Outcome{0n,0n,0n,0n,0n,0n} : PDOutcome}
def pd_suffix_refusal_has_no_factory():
  {==}
law pd_metadata_absent_still_validates_links:
  {pd_classify(Node{2n,1n,False{},False{},1n},True{},0n) == Outcome{0n,0n,0n,0n,0n,1n} : PDOutcome}
def pd_metadata_absent_still_validates_links():
  {==}
law pd_forbidden_directory_stops:
  {pd_classify(Node{2n,1n,False{},True{},1n},False{},0n) == Outcome{0n,0n,0n,0n,1n,1n} : PDOutcome}
def pd_forbidden_directory_stops():
  {==}
law pd_denied_top_link_does_not_read_target:
  {pd_follow(Node{0n,0n,False{},False{},0n},False{},2n) == Outcome{0n,0n,0n,0n,1n,1n} : PDOutcome}
def pd_denied_top_link_does_not_read_target():
  {==}
law pd_null_is_not_no_invocation:
  {pd_invoke(1n,1n,1n) == Outcome{0n,0n,1n,1n,0n,0n} : PDOutcome}
def pd_null_is_not_no_invocation():
  {==}
law pd_factory_failure_retains_attempt:
  {pd_invoke(2n,1n,1n) == Outcome{2n,0n,1n,1n,0n,0n} : PDOutcome}
def pd_factory_failure_retains_attempt():
  {==}
law pd_current_relative_shadow:
  {pd_run(Input{Node{3n,1n,False{},False{},0n},Node{1n,3n,True{},False{},0n},Node{1n,2n,True{},False{},0n},False{},True{},0n},False{}) == Outcome{0n,1n,1n,3n,0n,1n} : PDOutcome}
def pd_current_relative_shadow():
  {==}
law pd_proposed_parent_changes_binding:
  {pd_run(Input{Node{3n,1n,False{},False{},0n},Node{1n,3n,True{},False{},0n},Node{1n,2n,True{},False{},0n},False{},True{},0n},True{}) == Outcome{0n,1n,1n,2n,0n,1n} : PDOutcome}
def pd_proposed_parent_changes_binding():
  {==}
law pd_current_missing_cwd_target:
  {pd_run(Input{Node{3n,1n,False{},False{},0n},Node{0n,0n,False{},False{},0n},Node{1n,2n,True{},False{},0n},False{},True{},0n},False{}) == Outcome{1n,0n,0n,0n,0n,1n} : PDOutcome}
def pd_current_missing_cwd_target():
  {==}
