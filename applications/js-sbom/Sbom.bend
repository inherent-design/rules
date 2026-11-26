import Base

# Qualified-success seed + three direct local archives. No general installer,
# graph/format validator, content verifier, or arbitrary source semantics.
type Profile is Data:
  Npm{}
  Pnpm{}
type Format is Data:
  CycloneDx{}
  Spdx{}
  Missing{}
type Operation is Data:
  Install{}
  Query{}
  Report{}
  ReplaceCode{}
  HoldEntry{}
  RestoreEntry{}
  HoldLock{}
type Request is Data:
  Request{operation: Operation,format: Format,lock_only: Bool,runtime_only: Bool}
type ModelContext is Data:
  ModelContext{profile: Profile,declared: String,directory: String,prod: String,dev: String,optional: String}
type Snapshot is Data:
  Snapshot{installed: Bool,lock: Bool,entry: Bool,changed_code: Bool}
type GraphBasis is Data:
  InstalledMetadata{}
  LockGraph{}
type MetadataBasis is Data:
  Installed{}
  Saved{}
  VirtualStore{}
  Unavailable{}
type Document is Data:
  Document{root_display: String,root_package: String,version: String,phase: String,components: String}
type StepResult is Data:
  StepResult{exit: Nat,after: Snapshot,runtime: String,document: Maybe<&2,Document>}
def is_npm(p: Profile) -> Bool:
  match p:
    case Npm{}: True{}
    case _: False{}
def is_spdx(f: Format) -> Bool:
  match f:
    case Spdx{}: True{}
    case _: False{}
def is_missing(f: Format) -> Bool:
  match f:
    case Missing{}: True{}
    case _: False{}
def graph_basis(p: Profile,lock_only: Bool) -> GraphBasis:
  Bool.pick(GraphBasis,Bool.and(is_npm(p),Bool.not(lock_only)),InstalledMetadata{},LockGraph{})
def metadata_basis(p: Profile,lock_only: Bool) -> MetadataBasis:
  match p:
    case Npm{}: Bool.pick(MetadataBasis,lock_only,Saved{},Installed{})
    case Pnpm{}: Bool.pick(MetadataBasis,lock_only,Unavailable{},VirtualStore{})
def code(+p: Profile,s: Snapshot,+f: Format,+lock_only: Bool) -> Nat:
  match s:
    case Snapshot{installed,+lock,entry,_}:
      Bool.pick(Nat,is_missing(f),Bool.pick(Nat,is_npm(p),1n,2n),Bool.pick(Nat,Bool.or(Bool.not(is_npm(p)),lock_only),Bool.pick(Nat,lock,0n,1n),Bool.pick(Nat,Bool.and(installed,Bool.and(entry,lock)),0n,1n)))
def root_name(p: Profile,declared: String,directory: String,f: Format) -> String:
  Bool.pick(String,Bool.and(is_npm(p),Bool.not(is_spdx(f))),directory,declared)
# Proposed identity rule, kept separate from current serialization.
def candidate_root_name(declared: String,directory: String) -> String: declared
def version_text(p: Profile,+f: Format) -> String:
  Bool.pick(String,is_spdx(f),"SPDX-2.3",Bool.pick(String,is_npm(p),"1.5","1.7"))
def phase(f: Format,lock_only: Bool) -> String:
  Bool.pick(String,is_spdx(f),"-",Bool.pick(String,lock_only,"pre-build","build"))
def scope(+p: Profile,f: Format,lock_only: Bool,+dev: Bool,+optional: Bool) -> String:
  Bool.pick(String,is_spdx(f),Bool.pick(String,is_npm(p),Bool.pick(String,dev,"DEV_DEPENDENCY_OF",Bool.pick(String,optional,"OPTIONAL_DEPENDENCY_OF","DEPENDENCY_OF")),"DEPENDS_ON"),Bool.pick(String,is_npm(p),Bool.pick(String,Bool.or(optional,Bool.and(dev,lock_only)),"optional","required"),Bool.pick(String,dev,"excluded","-")))
def component(+p: Profile,+f: Format,+lock_only: Bool,name: String,digest: String,+dev: Bool,optional: Bool) -> String:
  name ++ "," ++ digest ++ "," ++ scope(p,f,lock_only,dev,optional) ++ "," ++ Bool.pick(String,Bool.and(Bool.not(is_spdx(f)),dev),"dev","-") ++ "," ++ Bool.pick(String,Bool.and(Bool.not(is_npm(p)),lock_only),"-","MIT")
def document(c: ModelContext,r: Request) -> Document:
  match c r:
    case ModelContext{+p,+declared,directory,prod,dev,optional} Request{_,+f,+lock_only,runtime_only}:
      +prod_text=component(p,f,lock_only,"rules-sbom-prod",prod,False{},False{})
      +other=component(p,f,lock_only,"rules-sbom-dev",dev,True{},False{}) ++ ";" ++ component(p,f,lock_only,"rules-sbom-optional",optional,False{},True{}) ++ ";" ++ prod_text
      Document{root_name(p,declared,directory,f),declared,version_text(p,f),phase(f,lock_only),Bool.pick(String,runtime_only,prod_text,other)}
def verifies_installed_bytes(d: Document) -> Bool: False{}
def runtime_value(entry: Bool,changed: Bool) -> String:
  Bool.pick(String,entry,Bool.pick(String,changed,"changed","original"),"missing")
def report_result(+c: ModelContext,+s: Snapshot,+r: Request) -> StepResult:
  match c r:
    case ModelContext{p,_,_,_,_,_} Request{_,f,lock_only,_}:
      +status=code(p,s,f,lock_only)
      StepResult{status,s,"-",Bool.pick(Maybe<&2,Document>,Nat.is_eq(status,0n),Some{document(c,r)},None{})}
def step(c: ModelContext,+s: Snapshot,+r: Request) -> StepResult:
  match s r:
    case _ Request{Install{},_,_,_}: StepResult{0n,Snapshot{True{},True{},True{},False{}},"-",None{}}
    case Snapshot{installed,lock,entry,_} Request{ReplaceCode{},_,_,_}: StepResult{0n,Snapshot{installed,lock,entry,True{}},"-",None{}}
    case Snapshot{installed,lock,_,changed} Request{HoldEntry{},_,_,_}: StepResult{0n,Snapshot{installed,lock,False{},changed},"-",None{}}
    case Snapshot{installed,lock,_,changed} Request{RestoreEntry{},_,_,_}: StepResult{0n,Snapshot{installed,lock,True{},changed},"-",None{}}
    case Snapshot{installed,_,entry,changed} Request{HoldLock{},_,_,_}: StepResult{0n,Snapshot{installed,False{},entry,changed},"-",None{}}
    case Snapshot{_,_,entry,changed} Request{Query{},_,_,_}: StepResult{0n,s,runtime_value(entry,changed),None{}}
    case _ Request{Report{},_,_,_}: report_result(c,s,r)
def after_state(r: StepResult) -> Snapshot:
  match r:
    case StepResult{_,s,_,_}: s
def trace(rs: List<&2,Request>,+c: ModelContext,s: Snapshot) -> List<&2,StepResult>:
  match rs:
    case Nil{}: Nil{}
    case Con{r,tail}:
      +result=step(c,s,r)
      Con{result,trace(tail,c,after_state(result))}
def document_text(d: Document) -> String:
  match d:
    case Document{display,identity,version,phase,components}: display ++ "|" ++ identity ++ "|" ++ version ++ "|" ++ phase ++ "|" ++ components
def maybe_document(d: Maybe<&2,Document>) -> String:
  match d:
    case None{}: "-"
    case Some{value}: document_text(value)
def text(r: StepResult) -> String:
  match r:
    case StepResult{exit,_,runtime,d}: Nat.show(exit) ++ "/" ++ runtime ++ "/" ++ maybe_document(d)
def lines(rs: List<&2,StepResult>) -> String:
  match rs:
    case Nil{}: ""
    case Con{h,t}: text(h) ++ "\n" ++ lines(t)
def installed() -> Snapshot: Snapshot{True{},True{},True{},False{}}
def npm() -> ModelContext: ModelContext{Npm{},"declared-root","physical-root","prod","dev","optional"}
def pnpm() -> ModelContext: ModelContext{Pnpm{},"declared-root","physical-root","prod","dev","optional"}
def request() -> Request: Request{Report{},CycloneDx{},False{},False{}}
law report_keeps_snapshot:
  {after_state(step(npm(),installed(),request())) == installed() : Snapshot}
def report_keeps_snapshot(): {==}
law query_keeps_snapshot:
  {after_state(step(npm(),installed(),Request{Query{},CycloneDx{},False{},False{}})) == installed() : Snapshot}
def query_keeps_snapshot(): {==}
law changed_code_keeps_document:
  {text(step(npm(),Snapshot{True{},True{},True{},True{}},request())) == text(step(npm(),installed(),request())) : String}
def changed_code_keeps_document(): {==}
law inventory_is_not_file_verification:
  {verifies_installed_bytes(document(npm(),request())) == False{} : Bool}
def inventory_is_not_file_verification(): {==}
law missing_entry_refuses_npm_default:
  {code(Npm{},Snapshot{True{},True{},False{},True{}},CycloneDx{},False{}) == 1n : Nat}
def missing_entry_refuses_npm_default(): {==}
law missing_entry_does_not_erase_pnpm_lock:
  {code(Pnpm{},Snapshot{True{},True{},False{},True{}},CycloneDx{},False{}) == 0n : Nat}
def missing_entry_does_not_erase_pnpm_lock(): {==}
law explicit_lock_does_not_need_entry:
  {code(Npm{},Snapshot{True{},True{},False{},True{}},CycloneDx{},True{}) == 0n : Nat}
def explicit_lock_does_not_need_entry(): {==}
law missing_lock_refuses_npm_explicit:
  {code(Npm{},Snapshot{True{},False{},True{},True{}},CycloneDx{},True{}) == 1n : Nat}
def missing_lock_refuses_npm_explicit(): {==}
law missing_lock_refuses_pnpm_explicit:
  {code(Pnpm{},Snapshot{True{},False{},True{},True{}},CycloneDx{},True{}) == 1n : Nat}
def missing_lock_refuses_pnpm_explicit(): {==}
law tarball_location_witness_matters:
  {code(Npm{},Snapshot{True{},False{},True{},True{}},CycloneDx{},False{}) == 1n : Nat}
def tarball_location_witness_matters(): {==}
law npm_missing_format_exit:
  {code(Npm{},installed(),Missing{},False{}) == 1n : Nat}
def npm_missing_format_exit(): {==}
law pnpm_missing_format_exit:
  {code(Pnpm{},installed(),Missing{},False{}) == 2n : Nat}
def pnpm_missing_format_exit(): {==}
law npm_actual_graph:
  {graph_basis(Npm{},False{}) == InstalledMetadata{} : GraphBasis}
def npm_actual_graph(): {==}
law npm_explicit_lock_graph:
  {graph_basis(Npm{},True{}) == LockGraph{} : GraphBasis}
def npm_explicit_lock_graph(): {==}
law pnpm_default_lock_graph:
  {graph_basis(Pnpm{},False{}) == LockGraph{} : GraphBasis}
def pnpm_default_lock_graph(): {==}
law pnpm_lock_only_omits_enrichment:
  {metadata_basis(Pnpm{},True{}) == Unavailable{} : MetadataBasis}
def pnpm_lock_only_omits_enrichment(): {==}
law npm_root_uses_placement:
  {root_name(Npm{},"declared","physical",CycloneDx{}) == "physical" : String}
def npm_root_uses_placement(): {==}
law spdx_root_uses_package_identity:
  {root_name(Npm{},"declared","physical",Spdx{}) == "declared" : String}
def spdx_root_uses_package_identity(): {==}
law proposed_root_ignores_placement:
  {candidate_root_name("declared","physical-a") == candidate_root_name("declared","physical-b") : String}
def proposed_root_ignores_placement(): {==}
law pnpm_spdx_edges_use_depends_on:
  {scope(Pnpm{},Spdx{},False{},True{},False{}) == "DEPENDS_ON" : String}
def pnpm_spdx_edges_use_depends_on(): {==}
law npm_spdx_preserves_dev_edge:
  {scope(Npm{},Spdx{},False{},True{},False{}) == "DEV_DEPENDENCY_OF" : String}
def npm_spdx_preserves_dev_edge(): {==}
law npm_actual_virtual_dev_scopes_differ:
  {scope(Npm{},CycloneDx{},False{},True{},False{}) == "required" : String}
def npm_actual_virtual_dev_scopes_differ(): {==}
law npm_virtual_dev_scope_optional:
  {scope(Npm{},CycloneDx{},True{},True{},False{}) == "optional" : String}
def npm_virtual_dev_scope_optional(): {==}
