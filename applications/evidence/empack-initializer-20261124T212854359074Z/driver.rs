// Fixture adapter around the complete selected association initializer chain.
use serde_json::{json,Value};
use std::{path::Path,io::Write};
fn failure(e:anyhow::Error)->Value {
    let unresolved=e.downcast_ref::<UnassociatedState>().map(|v|v.records.iter().map(|p|p.file_name().unwrap().to_string_lossy().into_owned()).collect::<Vec<_>>());
    json!({"ok":false,"error":format!("{e:#}"),"unassociated":unresolved})
}
pub(crate) fn run(base:&Path,mode:&str)->Result<()> {
    let root=ProjectReadRoot::open(&base.join("project"))?;
    let host=base.join("host");
    let publisher=Publisher{host:Dir::open_ambient_dir(&host,cap_std::ambient_authority())?,location:host};
    let outcome=match mode {
        "initialize"=>match publisher.retain_root_association(&root){
            Ok(())=>{
                super::fixture_phase("completed")?;
                json!({"ok":true,"key":publisher.bound_root_key(&root)?,"root":{
                    "volume":root.binding.volume.to_string(),"object":root.binding.object.to_string(),
                    "created":root.binding.created,"persistent":root.binding.persistent}})
            },Err(e)=>failure(e)
        },
        "lookup"=>match publisher.resolve_project_state(&root){
            Ok(v)=>json!({"ok":true,"selected":v.map(|(k,_)|k),"key":publisher.bound_root_key(&root)?}),Err(e)=>failure(e)
        },
        _=>anyhow::bail!("Unknown fixture action"),
    };
    println!("{}",json!({"event":"result","pid":std::process::id(),"action":mode,"outcome":outcome}));
    std::io::stdout().flush()?;Ok(())
}
