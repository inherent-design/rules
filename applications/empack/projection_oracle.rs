//! Actual pure core API; fictional content IDs exercise planning, not file verification.
use empack_core::{
    digest::ContentId,
    distribution::{Consumer, Delivery, Recipe},
    files::FilePermissions,
    inventory::{BuildSelection, ContentOwner, DownloadOrigins, InventoryError, InventoryInput, OptionalPolicy, ProjectedEntry, Representation},
    model::{ContentLayer, ExpectedContent, NonEmpty},
    path::InstallDestination,
    requirements::{ChoiceKey, Environments, OptionalChoice, Requirement, Requirements},
};
use std::collections::BTreeMap;

// owner, layer, destination, client requirement, server requirement, representation, asset label
#[derive(Clone, Copy)]
struct Spec(u8, u8, u8, u8, u8, u8, u8);
fn layer(n: u8) -> ContentLayer { match n { 0 => ContentLayer::Common, 1 => ContentLayer::CommonOverride, 2 => ContentLayer::Client, 3 => ContentLayer::Server, _ => panic!("bad layer") } }
fn layer_id(value: ContentLayer) -> u8 { match value { ContentLayer::Common => 0, ContentLayer::CommonOverride => 1, ContentLayer::Client => 2, ContentLayer::Server => 3 } }
fn requirement(n: u8) -> Requirement { match n {
    0 => Requirement::Unsupported, 1 => Requirement::Required,
    2 | 3 => Requirement::Optional(OptionalChoice { key: ChoiceKey::parse("extra").unwrap(), default_enabled: n == 3, description: Some("Fixture optional".into()) }),
    _ => panic!("bad requirement")
} }
fn req_id(r: &Requirement) -> u8 { match r { Requirement::Unsupported => 0, Requirement::Required => 1, Requirement::Optional(c) => if c.default_enabled { 3 } else { 2 } } }
fn expected(asset: u8, observed: bool) -> ExpectedContent { ExpectedContent { digests: None, size: Some(1), accepted_observation: observed.then_some(ContentId::from_sha256([asset;32])) } }
fn make(s: Spec) -> InventoryInput {
    let Spec(owner, level, path, client, server, repr, asset) = s;
    InventoryInput { owner: ContentOwner::Source(format!("s{owner}")), layer: layer(level), destination: InstallDestination::parse(&format!("config/p{path}.cfg")).unwrap(), requirements: Requirements { client: requirement(client), server: requirement(server) }, representation: match repr {
        0 => Representation::Embedded { content: ContentId::from_sha256([asset;32]), bytes: 1, permissions: FilePermissions { readonly: false, executable: true } },
        1 => Representation::Unacquired { expected: expected(asset, false) },
        2..=4 => Representation::Download { expected: expected(asset, repr != 3), allowed: DownloadOrigins::Urls(NonEmpty::new(vec![if repr == 4 { "".into() } else { "https://example.invalid/fixture".into() }]).unwrap()) },
        _ => panic!("bad representation")
    } }
}
fn recipe(n: u8) -> Recipe { match n {
    0 => Recipe::PRISM_BUNDLED, 1 => Recipe::SERVER_BUNDLED, 2 => Recipe::PRISM_REFERENCES,
    3 => Recipe::MODRINTH, 4 => Recipe::EMPACK_REFERENCES, 5 => Recipe::EMPACK_BUNDLED,
    6 => Recipe::new(Consumer::Empack, Delivery::References, Environments::Client).unwrap(),
    7 => Recipe::CURSEFORGE, _ => panic!("bad recipe")
} }
fn policy(n: u8) -> OptionalPolicy { match n {
    0 => OptionalPolicy::Preserve,
    1 => OptionalPolicy::Resolve { choices: BTreeMap::new(), use_defaults: false },
    2 | 3 => OptionalPolicy::Resolve { choices: BTreeMap::from([("extra".into(), n == 2)]), use_defaults: false },
    4 => OptionalPolicy::Resolve { choices: BTreeMap::new(), use_defaults: true },
    5 => OptionalPolicy::Resolve { choices: BTreeMap::from([("ghost".into(), true)]), use_defaults: false },
    _ => panic!("bad policy")
} }
fn error(e: InventoryError) -> &'static str { match e {
    InventoryError::DuplicateDestination(_) => "duplicate", InventoryError::ConflictingChoice(_) => "conflicting-choice",
    InventoryError::ChoiceRequired(_) => "choice-required", InventoryError::UnknownChoice(_) => "unknown-choice",
    InventoryError::InvalidEnvironment(_) => "invalid-environment", InventoryError::MaterializationRequired(_) => "materialization",
    InventoryError::InvalidReference(_) => "invalid-reference", InventoryError::ReferenceChoicesMustBePreserved => "preserve-required",
    InventoryError::OptionalOverlayNeedsSelection(_) => "overlay-needs-choice"
} }
fn owner(o: &ContentOwner) -> &str { match o { ContentOwner::Source(s) => s, _ => panic!("unexpected owner") } }
fn entry(e: &ProjectedEntry) -> String {
    let (repr, asset) = match &e.representation {
        Representation::Embedded { content, bytes, permissions } => { assert_eq!(*bytes,1); assert!(!permissions.readonly && permissions.executable); (0, content.bytes()[0]) },
        Representation::Unacquired {..} => (1,0),
        Representation::Download { expected, allowed: _ } => (if expected.accepted_observation.is_some() {2} else {3}, expected.accepted_observation.as_ref().map_or(0,|c|c.bytes()[0]))
    };
    format!("{}:{}:{}:{}:{}:{}:{}",owner(&e.owner),layer_id(e.layer),e.destination.relative().as_str(),req_id(&e.requirements.client),req_id(&e.requirements.server),repr,asset)
}
fn emit(name: &str, target: u8, mode: u8, specs: Vec<Spec>) {
    let inputs: Vec<_> = specs.iter().copied().map(make).collect(); let before = inputs.clone();
    let encoded = specs.iter().map(|s|format!("{},{},{},{},{},{},{}",s.0,s.1,s.2,s.3,s.4,s.5,s.6)).collect::<Vec<_>>().join(";");
    let (status, selected, precedence, choices) = match BuildSelection::select(&inputs,recipe(target),&policy(mode)) {
        Err(e) => (format!("select/{}",error(e)),String::new(),String::new(),String::new()),
        Ok(selection) => {
            let selected = selection.entries().iter().map(entry).collect::<Vec<_>>().join(";");
            match selection.finish() {
                Err(e) => (format!("finish/{}",error(e)),selected,String::new(),String::new()),
                Ok(done) => {
                    assert_eq!(selected,done.entries().iter().map(entry).collect::<Vec<_>>().join(";"));
                    let precedence = done.precedence().iter().map(|p|format!("{}>{}@{}",owner(&p.replacement),owner(&p.replaced),p.destination.relative().as_str())).collect::<Vec<_>>().join(";");
                    let choices = done.choices().iter().map(|c|format!("{}:{}:{}",c.choice.key.as_str(),c.enabled,c.used_default)).collect::<Vec<_>>().join(";");
                    ("ok".into(),selected,precedence,choices)
                }
            }
        }
    };
    assert_eq!(inputs,before);
    println!("{name}\t{target}\t{mode}\t{encoded}\t{status}\t{selected}\t{precedence}\t{choices}");
}
fn main() {
    let common=Spec(1,0,0,1,1,0,1); let over=Spec(4,1,0,1,1,0,4);
    let client=Spec(2,2,0,1,0,0,2); let server=Spec(3,3,0,0,1,0,3);
    let all=vec![common,client,server,over];
    for (label,target) in [("four-layers-client",0),("four-layers-server",1),("four-layers-mrpack",3),("four-layers-native",4),("native-bundled-layers",5),("native-client-layers",6)] { emit(label,target,0,all.clone()); }
    let mut reversed=all.clone();reversed.reverse();emit("reversed-client",0,0,reversed);
    emit("common-override-fallback",0,0,vec![common,over,server]);
    let optional=Spec(2,2,0,2,0,0,2);
    for (label,mode) in [("optional-preserve-full",0),("optional-unknown",1),("optional-enabled",2),("optional-disabled",3),("optional-default",4)] {emit(label,0,mode,vec![common,optional]);}
    emit("shadowed-optional-not-asked",0,1,vec![Spec(1,0,0,2,1,0,1),client]);
    emit("optional-alone-reference",2,0,vec![optional]);
    emit("optional-overlay-reference",2,0,vec![common,optional]);
    emit("optional-layers-mrpack",3,0,vec![common,optional]);
    emit("mrpack-resolve-refused",3,4,vec![common,optional]);
    emit("duplicate-layer-path",0,0,vec![common,Spec(5,0,0,1,1,0,5)]);
    emit("invalid-side-requirement",0,0,vec![Spec(2,2,0,1,1,0,2)]);
    emit("conflicting-choice-before-shadow",0,1,vec![Spec(1,0,0,2,1,0,1),Spec(2,2,0,3,0,0,2)]);
    emit("unknown-choice",0,5,vec![common]);
    emit("unacquired-selected",0,0,vec![Spec(2,2,0,1,0,1,2)]);
    emit("unacquired-shadowed",0,0,vec![Spec(1,0,0,1,1,1,1),client]);
    emit("unacquired-opposite-side",0,0,vec![Spec(3,3,0,0,1,1,3)]);
    emit("unacquired-native-excluded",6,0,vec![common,Spec(3,3,0,0,1,1,3)]);
    emit("same-bytes-distinct-placements",0,0,vec![Spec(2,2,0,1,0,0,7),Spec(5,2,1,1,0,0,7)]);
    emit("download-reference",2,0,vec![Spec(1,0,0,1,1,2,1)]);
    emit("download-full",0,0,vec![Spec(1,0,0,1,1,2,1)]);
    emit("download-no-evidence",2,0,vec![Spec(1,0,0,1,1,3,1)]);
    emit("download-empty-origin",2,0,vec![Spec(1,0,0,1,1,4,1)]);
    emit("optional-default-enabled",0,4,vec![common,Spec(2,2,0,3,0,0,2)]);
}
