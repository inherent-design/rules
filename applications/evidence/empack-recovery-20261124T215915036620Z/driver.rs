// Fixture association/identity setup only. Recovery itself runs through the CLI.
use serde_json::{json,Value};
use std::path::Path;
fn identity_value(x:ObjectIdentity)->Value {
 json!({"volume":x.volume.to_string(),"object":x.object.to_string(),"created":x.created,"persistent":x.persistent})
}
pub(crate) fn run(base:&Path,_mode:&str)->Result<()> {
 let root=ProjectReadRoot::open(&base.join("project"))?;
 let host=base.join("host");
 let publisher=Publisher{host:Dir::open_ambient_dir(&host,cap_std::ambient_authority())?,location:host};
 publisher.retain_root_association(&root)?;
 let file=std::fs::File::open(base.join("project/pack/rules.txt"))?;
 println!("{}",json!({"key":publisher.bound_root_key(&root)?,"root":identity_value(root.binding),"file":identity_value(native::identity(&file)?)}));
 Ok(())
}
