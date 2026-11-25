import Base

# Saved path components and opaque IDs are finite labels admitted by the
# research decoder. Blob kind is part of identity. No hash/codec proof implied.
type CHandle is Data:
  CHandle{tree: Bool,id: Nat}
type CBlob is Data:
  CBlob{handle: CHandle,plain: Nat,cipher: Nat,expanded: Nat,compressed: Bool}
type CNode is Data:
  CNode{path: List<&2,Nat>,location: List<&2,Nat>,directory: Bool,present: Bool,content: List<&2,Nat>,metadata: Nat,subtree: Maybe<&2,Nat>,size: Nat}
type CSnapshot is Data:
  CSnapshot{root: Nat,nodes: List<&2,CNode>}
type CStats is Data:
  CStats{size: Nat,entries: Nat,blobs: Nat,snapshots: Nat,expanded: Nat,compressed: Nat,compressed_expanded: Nat}
type CState is Data:
  CState{seen: List<&2,List<&2,Nat>>,size: Nat,count: Nat}
type CRef is Data:
  CRef{location: List<&2,Nat>,id: Nat}
type CRefState is Data:
  CRefState{seen: List<&2,List<&2,Nat>>,refs: List<&2,CRef>,locations: List<&2,List<&2,Nat>>}

def same_path(a: List<&2,Nat>,b: List<&2,Nat>) -> Bool:
  match a b:
    case Nil{} Nil{}: True{}
    case Con{x,xs} Con{y,ys}: Bool.and(Nat.is_eq(x,y),same_path(xs,ys))
    case _ _: False{}
def prefix(root: List<&2,Nat>,path: List<&2,Nat>) -> Bool:
  match root path:
    case Nil{} _: True{}
    case Con{x,xs} Con{y,ys}: Bool.and(Nat.is_eq(x,y),prefix(xs,ys))
    case _ _: False{}
def below(+root: List<&2,Nat>,+path: List<&2,Nat>) -> Bool:
  Bool.and(prefix(root,path),Bool.not(same_path(root,path)))
def path_member(paths: List<&2,List<&2,Nat>>,+p: List<&2,Nat>) -> Bool:
  match paths:
    case Nil{}: False{}
    case Con{head,tail}: Bool.or(same_path(head,p),path_member(tail,p))
def same_handle(a: CHandle,b: CHandle) -> Bool:
  match a b:
    case CHandle{at,ai} CHandle{bt,bi}: Bool.and(Bool.not(Bool.xor(at,bt)),Nat.is_eq(ai,bi))
def member(handles: List<&2,CHandle>,+h: CHandle) -> Bool:
  match handles:
    case Nil{}: False{}
    case Con{head,tail}: Bool.or(same_handle(head,h),member(tail,h))
def unique(handles: List<&2,CHandle>) -> List<&2,CHandle>:
  match handles:
    case Nil{}: []
    case Con{+head,tail}:
      +rest=unique(tail)
      Bool.pick(List<&2,CHandle>,member(rest,head),rest,Con{head,rest})
def data_refs(ids: List<&2,Nat>) -> List<&2,CHandle>:
  match ids:
    case Nil{}: []
    case Con{id,tail}: Con{CHandle{False{},id},data_refs(tail)}
def node_refs(n: CNode) -> List<&2,CHandle>:
  match n:
    case CNode{_,_,False{},_,ids,_,_,_}: data_refs(ids)
    case CNode{_,_,True{},_,_,_,sub,_}:
      match sub:
        case None{}: []
        case Some{id}: [CHandle{True{},id}]
def nodes_refs(nodes: List<&2,CNode>) -> List<&2,CHandle>:
  match nodes:
    case Nil{}: []
    case Con{head,tail}: List.append(&2,CHandle,node_refs(head),nodes_refs(tail))
def closure(s: CSnapshot) -> List<&2,CHandle>:
  match s:
    case CSnapshot{root,nodes}: unique(Con{CHandle{True{},root},nodes_refs(nodes)})
def difference(handles: List<&2,CHandle>,+other: List<&2,CHandle>) -> List<&2,CHandle>:
  match handles:
    case Nil{}: []
    case Con{+head,tail}:
      +rest=difference(tail,other)
      Bool.pick(List<&2,CHandle>,member(other,head),rest,Con{head,rest})
def lookup(catalog: List<&2,CBlob>,+h: CHandle) -> Maybe<&2,CBlob>:
  match catalog:
    case Nil{}: None{}
    case Con{+head,tail}:
      match head:
        case CBlob{key,_,_,_,_}: Bool.pick(Maybe<&2,CBlob>,same_handle(key,h),Some{head},lookup(tail,h))
def measurement(measure: Nat,plain: Nat,+cipher: Nat,+expanded: Nat,compressed: Bool) -> Nat:
  match measure:
    case 0n: plain
    case 1n: cipher
    case 2n: expanded
    case 3n: Bool.pick(Nat,compressed,cipher,0n)
    case _: Bool.pick(Nat,compressed,expanded,0n)
def weighted_step(blob: Maybe<&2,CBlob>,rest: Maybe<&2,Nat>,measure: Nat) -> Maybe<&2,Nat>:
  match blob rest:
    case Some{CBlob{_,plain,cipher,expanded,compressed}} Some{n}: Some{Nat.add(measurement(measure,plain,cipher,expanded,compressed),n)}
    case _ _: None{}
def weighted(+catalog: List<&2,CBlob>,handles: List<&2,CHandle>,+measure: Nat) -> Maybe<&2,Nat>:
  match handles:
    case Nil{}: Some{0n}
    case Con{head,tail}: weighted_step(lookup(catalog,head),weighted(catalog,tail,measure),measure)
def count(handles: List<&2,CHandle>,+tree: Bool) -> Nat:
  match handles:
    case Nil{}: 0n
    case Con{CHandle{kind,_},tail}: Nat.add(Bool.pick(Nat,Bool.not(Bool.xor(kind,tree)),1n,0n),count(tail,tree))
def all_nodes(ss: List<&2,CSnapshot>) -> List<&2,CNode>:
  match ss:
    case Nil{}: []
    case Con{CSnapshot{_,nodes},tail}: List.append(&2,CNode,nodes,all_nodes(tail))
def size(nodes: List<&2,CNode>) -> Nat:
  match nodes:
    case Nil{}: 0n
    case Con{CNode{_,_,_,_,_,_,_,n},tail}: Nat.add(n,size(tail))
def restore_stats(+ss: List<&2,CSnapshot>) -> CStats:
  +nodes=all_nodes(ss)
  CStats{size(nodes),List.length(&2,CNode,nodes),0n,List.length(&2,CSnapshot,ss),0n,0n,0n}
def content_state(nodes: List<&2,CNode>,s: CState) -> CState:
  match nodes s:
    case Nil{} _: s
    case Con{CNode{_,_,_,_,+content,_,_,bytes},tail} CState{+seen,+total,+count}:
      next=Bool.pick(CState,path_member(seen,content),CState{seen,total,count},CState{Con{content,seen},Nat.add(total,bytes),Nat.add(count,1n)})
      content_state(tail,next)
def content_result(s: CState,snapshots: Nat) -> CStats:
  match s:
    case CState{_,bytes,count}: CStats{bytes,count,0n,snapshots,0n,0n,0n}
def content_stats(+ss: List<&2,CSnapshot>) -> CStats:
  content_result(content_state(all_nodes(ss),CState{[],0n,0n}),List.length(&2,CSnapshot,ss))
def ref_member(refs: List<&2,CRef>,+r: CRef) -> Bool:
  match refs:
    case Nil{}: False{}
    case Con{CRef{p,i},tail}:
      match r:
        case CRef{q,j}: Bool.or(Bool.and(same_path(p,q),Nat.is_eq(i,j)),ref_member(tail,r))
def insert_refs(content: List<&2,Nat>,+path: List<&2,Nat>,+refs: List<&2,CRef>) -> List<&2,CRef>:
  match content:
    case Nil{}: refs
    case Con{id,tail}:
      +r : CRef = CRef{path,id}
      next=Bool.pick(List<&2,CRef>,ref_member(refs,r),refs,Con{r,refs})
      insert_refs(tail,path,next)
def ref_state(+gate: Bool,nodes: List<&2,CNode>,s: CRefState) -> CRefState:
  match nodes s:
    case Nil{} _: s
    case Con{CNode{_,+location,_,_,+content,_,_,_},tail} CRefState{+seen,+refs,+locations}:
      +skip=Bool.and(gate,path_member(seen,content))
      locs=Bool.pick(List<&2,List<&2,Nat>>,Bool.or(List.is_empty(&2,Nat,content),path_member(locations,location)),locations,Con{location,locations})
      next=Bool.pick(CRefState,skip,CRefState{seen,refs,locations},CRefState{Con{content,seen},insert_refs(content,location,refs),locs})
      ref_state(gate,tail,next)
def ref_handles(refs: List<&2,CRef>) -> List<&2,CHandle>:
  match refs:
    case Nil{}: []
    case Con{CRef{_,id},tail}: Con{CHandle{False{},id},ref_handles(tail)}
def reference_weight(weight: Maybe<&2,Nat>,locations: Nat,refs: Nat,snapshots: Nat) -> Maybe<&2,CStats>:
  match weight:
    case None{}: None{}
    case Some{bytes}: Some{CStats{bytes,locations,refs,snapshots,0n,0n,0n}}
def reference_result(state: CRefState,catalog: List<&2,CBlob>,snapshots: Nat) -> Maybe<&2,CStats>:
  match state:
    case CRefState{_,+refs,locations}:
      reference_weight(weighted(catalog,ref_handles(refs),0n),List.length(&2,List<&2,Nat>,locations),List.length(&2,CRef,refs),snapshots)
def reference_stats(catalog: List<&2,CBlob>,+ss: List<&2,CSnapshot>,gate: Bool) -> Maybe<&2,CStats>:
  reference_result(ref_state(gate,all_nodes(ss),CRefState{[],[],[]}),catalog,List.length(&2,CSnapshot,ss))
def all_refs(ss: List<&2,CSnapshot>) -> List<&2,CHandle>:
  match ss:
    case Nil{}: []
    case Con{head,tail}: List.append(&2,CHandle,closure(head),all_refs(tail))
def raw_result(bytes: Maybe<&2,Nat>,expanded: Maybe<&2,Nat>,compressed: Maybe<&2,Nat>,compressed_expanded: Maybe<&2,Nat>,refs: Nat,snapshots: Nat) -> Maybe<&2,CStats>:
  match bytes expanded compressed compressed_expanded:
    case Some{bytes} Some{expanded} Some{compressed} Some{compressed_expanded}:
      Some{CStats{bytes,0n,refs,snapshots,expanded,compressed,compressed_expanded}}
    case _ _ _ _: None{}
def raw_stats(+catalog: List<&2,CBlob>,+ss: List<&2,CSnapshot>) -> Maybe<&2,CStats>:
  +refs=unique(all_refs(ss))
  raw_result(weighted(catalog,refs,1n),weighted(catalog,refs,2n),weighted(catalog,refs,3n),weighted(catalog,refs,4n),List.length(&2,CHandle,refs),List.length(&2,CSnapshot,ss))

# Query: 0 listing,1 search,2 statistics,3 payload. Availability:
# 0 present,1 omitted data pack,2 omitted root-tree pack. Post-admission only.
def read_outcome(fix: Bool,+query: Nat,availability: Nat) -> String:
  match availability:
    case 0n: "0|1|1|1"
    case 1n: Bool.pick(String,Nat.is_eq(query,3n),"1|1|0|0","0|1|1|1")
    case _:
      Bool.pick(String,Nat.is_eq(query,1n),Bool.pick(String,fix,"1|1|0|1","0|0|0|0"),Bool.pick(String,Nat.is_eq(query,0n),"1|1|0|1","1|1|0|0"))
def stats_text(s: CStats) -> String:
  match s:
    case CStats{bytes,entries,blobs,snapshots,expanded,compressed,compressed_expanded}:
      Nat.show(bytes) ++ "|" ++ Nat.show(entries) ++ "|" ++ Nat.show(blobs) ++ "|" ++ Nat.show(snapshots) ++ "|" ++ Nat.show(expanded) ++ "|" ++ Nat.show(compressed) ++ "|" ++ Nat.show(compressed_expanded)
def maybe_stats(s: Maybe<&2,CStats>) -> String:
  match s:
    case None{}: "unknown"
    case Some{value}: stats_text(value)
def node_at(nodes: List<&2,CNode>,+path: List<&2,Nat>) -> Maybe<&2,CNode>:
  match nodes:
    case Nil{}: None{}
    case Con{+head,tail}:
      match head:
        case CNode{p,_,_,_,_,_,_,_}: Bool.pick(Maybe<&2,CNode>,same_path(p,path),Some{head},node_at(tail,path))
def type_changed(a: CNode,b: Maybe<&2,CNode>) -> Bool:
  match a b:
    case CNode{_,_,ad,_,_,_,_,_} Some{CNode{_,_,bd,_,_,_,_,_}}: Bool.xor(ad,bd)
    case _ _: False{}
def under_boundary(nodes: List<&2,CNode>,+other: List<&2,CNode>,+path: List<&2,Nat>) -> Bool:
  match nodes:
    case Nil{}: False{}
    case Con{+head,tail}:
      match head:
        case CNode{+p,_,_,_,_,_,_,_}:
          Bool.or(Bool.and(below(p,path),type_changed(head,node_at(other,p))),under_boundary(tail,other,path))
def visible(nodes: List<&2,CNode>,+a: List<&2,CNode>,+b: List<&2,CNode>) -> List<&2,CNode>:
  match nodes:
    case Nil{}: []
    case Con{+head,tail}:
      match head:
        case CNode{path,_,_,_,_,_,_,_}:
          +rest=visible(tail,a,b)
          Bool.pick(List<&2,CNode>,under_boundary(a,b,path),rest,Con{head,rest})
def same_content(a: CNode,b: CNode) -> Bool:
  match a b:
    case CNode{_,_,_,ap,ac,_,_,_} CNode{_,_,_,bp,bc,_,_,_}: Bool.and(Bool.not(Bool.xor(ap,bp)),same_path(ac,bc))
def changed_file(+a: CNode,+b: CNode) -> Bool:
  match a b:
    case CNode{_,_,ad,_,_,_,_,_} CNode{_,_,bd,_,_,_,_,_}:
      Bool.and(Bool.not(Bool.or(ad,bd)),Bool.not(same_content(a,b)))
def both_changed(a: CNode,b: Maybe<&2,CNode>) -> Bool:
  match b:
    case None{}: False{}
    case Some{n}: changed_file(a,n)
def changed_count(nodes: List<&2,CNode>,+other: List<&2,CNode>) -> Nat:
  match nodes:
    case Nil{}: 0n
    case Con{+head,tail}:
      match head:
        case CNode{path,_,_,_,_,_,_,_}: Nat.add(Bool.pick(Nat,both_changed(head,node_at(other,path)),1n,0n),changed_count(tail,other))
def absent(n: Maybe<&2,CNode>) -> Bool:
  match n:
    case None{}: True{}
    case Some{_}: False{}
def added_count(nodes: List<&2,CNode>,+other: List<&2,CNode>,+directory: Bool) -> Nat:
  match nodes:
    case Nil{}: 0n
    case Con{CNode{path,_,kind,_,_,_,_,_},tail}:
      Nat.add(Bool.pick(Nat,Bool.and(absent(node_at(other,path)),Bool.not(Bool.xor(kind,directory))),1n,0n),added_count(tail,other,directory))
def weight_text(n: Maybe<&2,Nat>) -> String:
  match n:
    case None{}: "unknown"
    case Some{v}: Nat.show(v)
def delta_text(catalog: List<&2,CBlob>,+nodes: List<&2,CNode>,+other: List<&2,CNode>,+refs: List<&2,CHandle>) -> String:
  Nat.show(added_count(nodes,other,False{})) ++ "|" ++ Nat.show(added_count(nodes,other,True{})) ++ "|" ++ Nat.show(count(refs,False{})) ++ "|" ++ Nat.show(count(refs,True{})) ++ "|" ++ weight_text(weighted(catalog,refs,0n))
def selected_refs(full: Bool,root: Nat,all: List<&2,CNode>,visible: List<&2,CNode>) -> List<&2,CHandle>:
  unique(Con{CHandle{True{},root},nodes_refs(Bool.pick(List<&2,CNode>,full,all,visible))})
def diff_text(+catalog: List<&2,CBlob>,+full: Bool,a: CSnapshot,b: CSnapshot) -> String:
  match a b:
    case CSnapshot{ar,+an} CSnapshot{br,+bn}:
      +av=visible(an,an,bn)
      +bv=visible(bn,an,bn)
      +arefs=selected_refs(full,ar,an,av)
      +brefs=selected_refs(full,br,bn,bv)
      Nat.show(changed_count(av,bn)) ++ "|" ++ delta_text(catalog,bv,an,difference(brefs,arefs)) ++ "|" ++ delta_text(catalog,av,bn,difference(arefs,brefs))
def paired_modifier(metadata: Bool,+a: CNode,+b: CNode) -> String:
  match a b:
    case CNode{_,_,+ad,_,_,+am,_,_} CNode{_,_,+bd,_,_,+bm,_,_}:
      type_flag=Bool.pick(String,Bool.xor(ad,bd),"T","")
      modify=Bool.pick(String,changed_file(a,b),"M" ++ Bool.pick(String,Nat.is_eq(am,bm),"?",""),Bool.pick(String,Bool.and(metadata,Bool.or(Bool.xor(ad,bd),Bool.or(Bool.not(Nat.is_eq(am,bm)),Bool.not(same_content(a,b))))),"U",""))
      type_flag ++ modify
def direct_modifier(metadata: Bool,a: Maybe<&2,CNode>,b: Maybe<&2,CNode>) -> String:
  match a b:
    case None{} None{}: ""
    case None{} Some{_}: "+"
    case Some{_} None{}: "-"
    case Some{x} Some{y}: paired_modifier(metadata,x,y)
def event_modifier(metadata: Bool,a: CSnapshot,b: CSnapshot,+path: List<&2,Nat>) -> String:
  match a b:
    case CSnapshot{_,+an} CSnapshot{_,+bn}:
      Bool.pick(String,under_boundary(an,bn,path),"",direct_modifier(metadata,node_at(an,path),node_at(bn,path)))
def sample_file(+path: Nat) -> CNode:
  CNode{[path],[path,path],False{},True{},[1n],0n,None{},2n}
def sample() -> CSnapshot:
  CSnapshot{10n,[sample_file(1n),sample_file(2n)]}
def sample_catalog() -> List<&2,CBlob>:
  [CBlob{CHandle{False{},1n},2n,4n,4n,False{}},CBlob{CHandle{True{},10n},1n,3n,3n,False{}}]

law typed_identity_does_not_alias:
  {same_handle(CHandle{False{},1n},CHandle{True{},1n}) == False{} : Bool}
def typed_identity_does_not_alias(): {==}
law missing_weight_is_unknown:
  {weighted([],[CHandle{False{},1n}],0n) == None{} : Maybe<&2,Nat>}
def missing_weight_is_unknown(): {==}
law metadata_scope_differs_from_payload:
  {read_outcome(False{},0n,1n) == "0|1|1|1" : String}
def metadata_scope_differs_from_payload(): {==}
law omitted_payload_fails:
  {read_outcome(False{},3n,1n) == "1|1|0|0" : String}
def omitted_payload_fails(): {==}
law source_search_can_succeed_with_invalid_protocol:
  {read_outcome(False{},1n,2n) == "0|0|0|0" : String}
def source_search_can_succeed_with_invalid_protocol(): {==}
law proposed_search_preserves_partial_result:
  {read_outcome(True{},1n,2n) == "1|1|0|1" : String}
def proposed_search_preserves_partial_result(): {==}
law source_gate_merges_distinct_paths:
  {maybe_stats(reference_stats(sample_catalog(),[sample()],True{})) == "2|1|1|1|0|0|0" : String}
def source_gate_merges_distinct_paths(): {==}
law alternative_path_refs_count_both:
  {maybe_stats(reference_stats(sample_catalog(),[sample()],False{})) == "4|2|2|1|0|0|0" : String}
def alternative_path_refs_count_both(): {==}
law restore_counts_two_copies:
  {stats_text(restore_stats([sample()])) == "4|2|0|1|0|0|0" : String}
def restore_counts_two_copies(): {==}
law repeated_snapshot_shares_raw_refs:
  {maybe_stats(raw_stats(sample_catalog(),[sample(),sample()])) == "7|0|2|2|7|0|0" : String}
def repeated_snapshot_shares_raw_refs(): {==}
law changed_type_suppresses_descendant_event:
  {event_modifier(False{},CSnapshot{10n,[sample_file(1n)]},CSnapshot{11n,[CNode{[1n],[1n,1n],True{},False{},[],0n,Some{12n},0n},CNode{[1n,2n],[1n,2n,2n],False{},True{},[2n],0n,None{},1n}]},[1n,2n]) == "" : String}
def changed_type_suppresses_descendant_event(): {==}
law changed_type_is_one_event:
  {event_modifier(False{},CSnapshot{10n,[sample_file(1n)]},CSnapshot{11n,[CNode{[1n],[1n,1n],True{},False{},[],0n,Some{12n},0n}]},[1n]) == "T" : String}
def changed_type_is_one_event(): {==}
law equal_metadata_content_change_is_suspect:
  {paired_modifier(False{},sample_file(1n),CNode{[1n],[1n,1n],False{},True{},[2n],0n,None{},2n}) == "M?" : String}
def equal_metadata_content_change_is_suspect(): {==}
