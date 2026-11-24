//! Actual unchanged-core calls over fictional provider identities and evidence.
//! This is not a resolver, codec, download, or publication test.
use empack_core::{
    digest::{DigestSet, ExpectedDigest},
    identity::{ModrinthProjectId, ModrinthVersionId, PinSelector, ProviderProjectId},
    model::*, path::InstallDestination,
    requirements::{Requirement, Requirements},
    synchronization::{affected_roots, rebind_prior_aliases, runtime_satisfies, SynchronizationResolution},
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
fn update(lock: &mut ResolutionLock, label: &str, selected: u8) {
    let dep=lock.dependencies.get_mut(&key(label)).unwrap();
    dep.selected.as_mut().unwrap().selection=version(selected);
    let mut files=dep.files.clone().into_vec();
    for file in &mut files { if let AcquisitionSpec::Provider{pin,..}=&mut file.acquisition {pin.selection=version(selected);} }
    dep.files=NonEmpty::new(files).unwrap();
}
fn rename(lock: &mut ResolutionLock, old: &str, new: &str) {
    let value=lock.dependencies.remove(&key(old)).unwrap();lock.dependencies.insert(key(new),value);
    let coverage=lock.coverage.remove(&key(old)).unwrap();lock.coverage.insert(key(new),coverage);
    lock.required_edges=lock.required_edges.iter().map(|(from,to)|
        (if from.as_str()==old {key(new)}else{from.clone()},to.iter().map(|to|if to.as_str()==old {key(new)}else{to.clone()}).collect())).collect();
}
// Bounded ASCII research encoding, not a public/general JSON codec.
fn q(s: &str) -> String { assert!(s.is_ascii()&&!s.chars().any(char::is_control));format!("{s:?}") }
fn strings(values: impl IntoIterator<Item=String>) -> String {format!("[{}]",values.into_iter().map(|s|q(&s)).collect::<Vec<_>>().join(","))}
fn snapshot(intent: &ProjectIntent, lock: &ResolutionLock) -> String {
    let roots=intent.roots.iter().map(|(k,r)|format!("{{\"key\":{},\"source\":{},\"selection\":{},\"placement\":{}}}",q(k.as_str()),q(&format!("{:?}",r.source)),q(&format!("{:?}",r.selection)),q(&format!("{:?}",r.placement)))).collect::<Vec<_>>().join(",");
    let nodes=lock.dependencies.iter().map(|(k,n)|format!("{{\"key\":{},\"record\":{},\"coverage\":{},\"edgesPresent\":{},\"edges\":{}}}",q(k.as_str()),q(&format!("{n:?}")),q(&format!("{:?}",lock.coverage.get(k))),lock.required_edges.contains_key(k),strings(lock.required_edges.get(k).into_iter().flatten().map(|k|k.as_str().to_owned())))).collect::<Vec<_>>().join(",");
    format!("{{\"roots\":[{roots}],\"nodes\":[{nodes}],\"requestedRuntime\":{},\"selectedRuntime\":{},\"acceptable\":{}}}",q(&format!("{:?}",intent.runtime)),q(&format!("{:?}",lock.runtime)),q(&format!("{:?}",lock.acceptable_versions)))
}
fn emit(name: &str) {
    let (mut intent,mut prior)=fixture(); let mut next=prior.clone(); let mut revision=SemanticRevision([1;32]);
    intent.metadata.name="Changed metadata".into();
    match name {
        "metadata-retains" => {},
        "unrequested-upgrade" => update(&mut next,"a",2),
        "root-demotion-retains" => intent.roots.clear(),
        "root-demotion-deletes" => {intent.roots.clear();next.dependencies.remove(&key("a"));next.coverage.remove(&key("a"));next.required_edges.remove(&key("a"));},
        "orphan-deletes" => {next.dependencies.remove(&key("c"));next.coverage.remove(&key("c"));},
        "pin-change" | "shared-change" | "retained-dependent" | "new-cycle" | "coverage-inside" => {
            intent.roots.get_mut(&key("a")).unwrap().selection=DependencySelection::ProviderPin(version(2));update(&mut next,"a",2);
            if matches!(name,"shared-change"|"retained-dependent") {update(&mut next,"b",2);}
            if name=="retained-dependent" {prior.required_edges.insert(key("c"),BTreeSet::from([key("b")]));next.required_edges.insert(key("c"),BTreeSet::from([key("b")]));}
            if name=="new-cycle" {next.required_edges.insert(key("b"),BTreeSet::from([key("a")]));}
            if name=="coverage-inside" {next.coverage.insert(key("b"),Coverage::Partial);}
        },
        "explicit-transitive-protected" => {intent.roots.insert(key("b"),root(2));intent.roots.get_mut(&key("a")).unwrap().selection=DependencySelection::ProviderPin(version(2));update(&mut next,"a",2);update(&mut next,"b",2);},
        "new-root" | "unjustified-new" => {intent.roots.insert(key("d"),root(4));next.dependencies.insert(key("d"),dependency(4,1));next.coverage.insert(key("d"),Coverage::CompleteForSelection);next.required_edges.insert(key("d"),BTreeSet::from([key("b")]));
            if name=="unjustified-new" {next.dependencies.insert(key("e"),dependency(5,1));next.coverage.insert(key("e"),Coverage::CompleteForSelection);}},
        "coverage-outside" => {next.coverage.insert(key("c"),Coverage::Partial);},
        "edges-outside" => {next.required_edges.insert(key("c"),BTreeSet::from([key("b")]));},
        "empty-edge-entry" => {next.required_edges.insert(key("c"),BTreeSet::new());},
        "loader-unpinned-upgrade" => next.runtime.loader_version=Some(LoaderVersion::parse("0.17.0").unwrap()),
        "loader-explicit-change" => {intent.runtime.loader_version=Some(LoaderVersion::parse("0.17.0").unwrap());next.runtime.loader_version=intent.runtime.loader_version.clone();},
        "accepted-version-change" => {intent.runtime.acceptable_versions.push(GameVersion::parse("1.21").unwrap());next.acceptable_versions=intent.runtime.acceptable_versions.clone();update(&mut next,"a",2);},
        "search-metadata" | "search-same-revision" => {intent.roots.get_mut(&key("a")).unwrap().source=SourceIntent::Search{query:"Fixture".into(),providers:NonEmpty::new(vec![ProviderKind::Modrinth]).unwrap()};update(&mut next,"a",2);
            if name=="search-same-revision" {revision=prior.intent_revision;intent.metadata.name="Fixture".into();}},
        "rename-root" => {let r=intent.roots.remove(&key("a")).unwrap();intent.roots.insert(key("renamed"),r);rename(&mut next,"a","renamed");},
        "new-label-occupied" => {intent.roots.clear();intent.roots.insert(key("b"),root(1));},
        "two-alias-requests" => {intent.roots.clear();intent.roots.insert(key("x"),root(1));intent.roots.insert(key("y"),root(1));},
        _ => panic!("unknown case"),
    }
    next.intent_revision=revision;
    let before=snapshot(&intent,&prior);let proposed=snapshot(&intent,&next);
    let normalized=rebind_prior_aliases(&intent,&prior);
    let (stage,result,changed,diagnostic)=match &normalized {
        Err(error)=>("rebind","error",BTreeSet::new(),error.to_string()),
        Ok(_normalized)=>match ResolvedProject::validate(intent.clone(),next.clone(),revision) {
            Err(error)=>("proposed","error",BTreeSet::new(),error.to_string()),
            Ok(project)=>match SynchronizationResolution::prepare(&intent,&prior,&project) {
                Err(error)=>("scope","error",BTreeSet::new(),error.to_string()),
                Ok(scope)=>("scope","ok",scope.changed().clone(),String::new()),
            }
        }
    };
    let affected=normalized.as_ref().map(|p|affected_roots(&intent,p,revision)).unwrap_or_default();
    println!("{{\"case\":{},\"before\":{before},\"proposed\":{proposed},\"sameRevision\":{},\"runtimeSatisfied\":{},\"affected\":{},\"normalized\":{},\"stage\":{},\"result\":{},\"changed\":{},\"diagnostic\":{}}}",q(name),revision==prior.intent_revision,runtime_satisfies(&intent.runtime,&prior.runtime),strings(affected.iter().map(|k|k.as_str().to_owned())),normalized.as_ref().map(|p|snapshot(&intent,p)).unwrap_or("null".into()),q(stage),q(result),strings(changed.iter().map(|k|k.as_str().to_owned())),q(&diagnostic));
}
fn main() {
    for name in ["metadata-retains","unrequested-upgrade","root-demotion-retains","root-demotion-deletes","orphan-deletes","pin-change","shared-change","retained-dependent","new-cycle","coverage-inside","explicit-transitive-protected","new-root","unjustified-new","coverage-outside","edges-outside","empty-edge-entry","loader-unpinned-upgrade","loader-explicit-change","accepted-version-change","search-metadata","search-same-revision","rename-root","new-label-occupied","two-alias-requests"] {emit(name);}
}
