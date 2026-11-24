//! Actual unchanged-core removal and request-merge calls over fictional values.
//! This is not a resolver, codec, download, or publication test.
use empack_core::{
    digest::{DigestSet, ExpectedDigest},
    identity::{ModrinthProjectId, ModrinthVersionId, PinSelector, ProviderProjectId},
    model::*, path::InstallDestination,
    requirements::{Requirement, Requirements},
    removal::{RemovalMode, RemovalEvidencePolicy, RemovalPlan, RemovalError},
    addition::{AdditionGroup, AdditionPlan},
};
use std::collections::{BTreeMap, BTreeSet};

fn key(s: &str) -> DependencyKey { DependencyKey::parse(s).unwrap() }
fn version(n: u8) -> PinSelector { PinSelector::ModrinthVersion(ModrinthVersionId::parse(&format!("Version{n}")).unwrap()) }
fn project(n: u8) -> ProviderProjectId { ProviderProjectId::Modrinth(ModrinthProjectId::parse(&format!("Project{n}")).unwrap()) }
fn required() -> Requirements { Requirements {client: Requirement::Required, server: Requirement::Required} }
fn dependency(n: u8, selected: u8) -> LockedDependency {
    let pin = ResolvedPin {project: project(n), selection: version(selected)};
    let digest = DigestSet::new(vec![ExpectedDigest::Sha256([n;32])]).unwrap();
    LockedDependency {source_selector: None, title: format!("Fixture{n}"), kind: ContentKind::Mod,
        identity: ResolvedIdentity::Provider(project(n)), selected: Some(pin.clone()), incompatibilities: vec![],
        files: NonEmpty::new(vec![ResolvedFile {slot: FileSlot::parse("main").unwrap(),
            acquisition: AcquisitionSpec::Provider {pin,slot:FileSlot::parse("fixture.jar").unwrap(),alternatives:vec![]},
            expected: ExpectedContent {digests:Some(digest.clone()),size:Some(1),accepted_observation:None},
            provenance: Provenance {source:"research-fixture".into(),location:None,declared_digests:Some(digest),conversions:vec![]},
            placements: NonEmpty::new(vec![Placement {destination:InstallDestination::parse(&format!("mods/{n}.jar")).unwrap(),layer:ContentLayer::Common,requirements:required()}]).unwrap()}]).unwrap()}
}
fn root(n: u8) -> DependencyIntent { DependencyIntent {releases:None,source:SourceIntent::Provider(project(n)),kind:ContentKind::Mod,selection:DependencySelection::Automatic,placement:PlacementIntent::Automatic,requirements:required()} }
fn fixture() -> (ProjectIntent, ResolutionLock) {
    let intent = ProjectIntent {dependency_policy:ReleasePolicy::PreferStable,installation_policies:BTreeMap::new(),source_excludes:vec![],
        metadata:PackMetadata{id:"sync-fixture".into(),name:"Fixture".into(),version:"one".into(),authors:vec![],description:None},
        runtime:RuntimeIntent {java_major:21,minecraft:GameVersion::parse("1.21.1").unwrap(),acceptable_versions:vec![],loader:LoaderKind::Fabric,loader_version:None},
        roots:BTreeMap::from([(key("a"),root(1))]),layout:BTreeMap::new(),distribution:DistributionIntent{profiles:BTreeMap::new(),defaults:vec![]},extensions:BTreeMap::new()};
    let lock = ResolutionLock {acceptable_versions:vec![],intent_revision:SemanticRevision([0;32]),resolver:"research".into(),
        dependencies:BTreeMap::from([(key("a"),dependency(1,1)),(key("b"),dependency(2,1)),(key("c"),dependency(3,1))]),
        required_edges:BTreeMap::from([(key("a"),BTreeSet::from([key("b")]))]),
        coverage:BTreeMap::from([(key("a"),Coverage::CompleteForSelection),(key("b"),Coverage::CompleteForSelection),(key("c"),Coverage::CompleteForSelection)]),
        runtime:RuntimeResolution {minecraft:intent.runtime.minecraft.clone(),loader:LoaderKind::Fabric,loader_version:Some(LoaderVersion::parse("0.16.0").unwrap())}};
    ResolvedProject::validate(intent.clone(),lock.clone(),lock.intent_revision).unwrap();
    (intent,lock)
}
// ASCII fixture names only; this is not a production codec.
fn q(s: &str) -> String { assert!(s.is_ascii()&&!s.chars().any(char::is_control));format!("{s:?}") }
fn strings(values: impl IntoIterator<Item=String>) -> String {format!("[{}]",values.into_iter().map(|s|q(&s)).collect::<Vec<_>>().join(","))}
fn keys<'a>(values: impl IntoIterator<Item=&'a DependencyKey>) -> String {strings(values.into_iter().map(|k|k.as_str().to_owned()))}
fn snapshot(project: &ResolvedProject) -> String {
    let lock=project.lock();
    let nodes=lock.dependencies.iter().map(|(k,n)|format!("{{\"key\":{},\"record\":{},\"coverage\":{},\"edgesPresent\":{},\"edges\":{}}}",q(k.as_str()),q(&format!("{n:?}")),q(&format!("{:?}",lock.coverage[k])),lock.required_edges.contains_key(k),keys(lock.required_edges.get(k).into_iter().flatten()))).collect::<Vec<_>>().join(",");
    format!("{{\"roots\":{},\"nodes\":[{nodes}]}}",keys(project.intent().roots.keys()))
}
fn error(e:&RemovalError)->String {
    let (kind,values)=match e {
        RemovalError::UnknownSelection(k)=>("unknown",vec![k]),
        RemovalError::DuplicateSelection(k)=>("duplicate",vec![k]),
        RemovalError::NotExplicitRoot(k)=>("not-root",vec![k]),
        RemovalError::RequiredBy(v)=>("required",v.iter().collect()),
        RemovalError::IncompleteEvidence(v)=>("incomplete",v.iter().collect()),
    };
    format!("{{\"kind\":{},\"keys\":{},\"message\":{}}}",q(kind),keys(values),q(&e.to_string()))
}
fn removal(name:&str) {
    let (intent,mut lock)=fixture();
    let mut names=vec!["a"];let mut mode=RemovalMode::RemoveContent;let mut policy=RemovalEvidencePolicy::RequireComplete;
    match name {
        "remove-root"=>{},
        "forget-root"=>mode=RemovalMode::ForgetRoots,
        "forget-transitive"=>{mode=RemovalMode::ForgetRoots;names=vec!["b"];},
        "forget-mixed"=>{mode=RemovalMode::ForgetRoots;names=vec!["a","b"];},
        "required"|"required-ack"=>{names=vec!["b"];if name=="required-ack"{policy=RemovalEvidencePolicy::AcknowledgeUnknown;}},
        "partial-retained"|"partial-ack"|"forget-partial"=>{
            lock.coverage.insert(key("c"),Coverage::Partial);
            if name=="partial-ack"{policy=RemovalEvidencePolicy::AcknowledgeUnknown;}
            if name=="forget-partial"{mode=RemovalMode::ForgetRoots;}
        },
        "unknown-retained"=>{lock.coverage.insert(key("c"),Coverage::Unknown);},
        "selected-partial"=>{lock.coverage.insert(key("a"),Coverage::Partial);},
        "known-before-unknown"=>{names=vec!["b"];lock.coverage.insert(key("c"),Coverage::Unknown);},
        "cycle-part"|"cycle-whole"=>{lock.required_edges.insert(key("b"),BTreeSet::from([key("a")]));if name=="cycle-whole"{names=vec!["a","b"];}},
        "duplicate"=>names=vec!["a","a"],
        "unknown-key"=>names=vec!["d"],
        "mixed-unknown"=>names=vec!["a","d"],
        "remove-unlisted"=>names=vec!["c"],
        "remove-all-unknown"=>{names=vec!["a","b","c"];for coverage in lock.coverage.values_mut(){*coverage=Coverage::Unknown;}},
        _=>panic!("unknown case")
    }
    let project=ResolvedProject::validate(intent,lock,SemanticRevision([0;32])).unwrap();
    let selected=NonEmpty::new(names.iter().map(|n|key(n)).collect()).unwrap();
    let before=snapshot(&project);
    let result=match RemovalPlan::prepare_with_policy(&project,&selected,mode,policy) {
        Err(e)=>format!("{{\"error\":{},\"after\":null}}",error(&e)),
        Ok(plan)=>{
            let exact=keys(plan.selected().keys());let removed=keys(&plan.removed());let incomplete=keys(plan.incomplete_evidence());
            let next=plan.resolve(SemanticRevision([1;32])).unwrap();
            format!("{{\"error\":null,\"selected\":{exact},\"removed\":{removed},\"incomplete\":{incomplete},\"after\":{}}}",snapshot(&next))
        }
    };
    assert_eq!(before,snapshot(&project));
    println!("{{\"case\":{},\"operation\":\"remove\",\"mode\":{},\"acknowledge\":{},\"selection\":{},\"before\":{before},\"result\":{result},\"inputUnchanged\":true}}",q(name),q(if mode==RemovalMode::ForgetRoots{"forget"}else{"content"}),policy==RemovalEvidencePolicy::AcknowledgeUnknown,strings(names.into_iter().map(str::to_owned)));
}
fn readopt(name:&str) {
    let (intent,lock)=fixture();let original=ResolvedProject::validate(intent,lock,SemanticRevision([0;32])).unwrap();
    let forget=name.starts_with("forgotten");
    let before=RemovalPlan::prepare(&original,&NonEmpty::new(vec![key("a")]).unwrap(),if forget{RemovalMode::ForgetRoots}else{RemovalMode::RemoveContent}).unwrap().resolve(SemanticRevision([1;32])).unwrap();
    let (request,mut evidence)=fixture();evidence.dependencies.remove(&key("c"));evidence.coverage.remove(&key("c"));
    let group=AdditionGroup::from_resolved(&ResolvedProject::validate(request,evidence,SemanticRevision([0;32])).unwrap()).unwrap();
    let operation=name.split('-').last().unwrap();
    let plan=match operation {"add"=>AdditionPlan::prepare(&before,&group),"adopt"=>AdditionPlan::prepare_adoption(&before,&group),"update"=>AdditionPlan::prepare_update(&before,&group),_=>panic!("unknown operation")};
    let result=match plan {
        Err(e)=>format!("{{\"error\":{},\"after\":null}}",q(&e.to_string())),
        Ok(plan)=>{
            let existing=keys(plan.existing_roots());let changed=keys(plan.changed());
            let reject_existing_would_allow=plan.existing_roots().is_empty();
            let next=plan.resolve(SemanticRevision([2;32])).unwrap();
            format!("{{\"error\":null,\"existingRequests\":{existing},\"changedRecords\":{changed},\"rejectExistingWouldAllow\":{reject_existing_would_allow},\"after\":{}}}",snapshot(&next))
        }
    };
    println!("{{\"case\":{},\"operation\":{},\"priorAction\":{},\"before\":{},\"result\":{result}}}",q(name),q(operation),q(if forget{"forget"}else{"content"}),snapshot(&before));
}
fn main() {
    for name in ["remove-root","forget-root","forget-transitive","forget-mixed","required","required-ack","partial-retained","partial-ack","forget-partial","unknown-retained","selected-partial","known-before-unknown","cycle-part","cycle-whole","duplicate","unknown-key","mixed-unknown","remove-unlisted","remove-all-unknown"] {removal(name);}
    for name in ["forgotten-add","forgotten-adopt","forgotten-update","removed-add","removed-adopt","removed-update"] {readopt(name);}
}
