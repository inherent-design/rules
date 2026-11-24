// Authored fixtures and observation wrappers; not production state/journals.
use serde_json::{json,Value};
use sha2::{Digest,Sha256};
use std::{collections::BTreeMap,fs,path::{Path,PathBuf},os::unix::{ffi::OsStrExt,fs::{MetadataExt,PermissionsExt,symlink}}};
fn hex(raw:&[u8])->String {raw.iter().map(|b|format!("{b:02x}")).collect()}
fn object(o:ObjectIdentity)->Value {json!({"volume":o.volume.to_string(),"object":o.object.to_string(),"created":o.created,"persistent":o.persistent})}
fn image(base:&Path)->Result<BTreeMap<String,Value>> {
    fn visit(base:&Path,path:&Path,out:&mut BTreeMap<String,Value>)->Result<()> {
        let m=fs::symlink_metadata(path)?;let relative=path.strip_prefix(base)?;
        let mut row=json!({"mode":m.mode(),"inode":m.ino().to_string(),"device":m.dev().to_string(),
            "mtime":[m.mtime(),m.mtime_nsec()],"bytes":m.len()});
        if m.file_type().is_symlink(){row["kind"]=json!("symlink");row["targetHex"]=json!(hex(fs::read_link(path)?.as_os_str().as_bytes()));}
        else if m.is_file(){row["kind"]=json!("file");let data=fs::read(path)?;row["contentHex"]=json!(hex(&data));}
        else if m.is_dir(){row["kind"]=json!("directory");}
        else {row["kind"]=json!("special");}
        out.insert(hex(relative.as_os_str().as_bytes()),row);
        if m.is_dir(){for e in fs::read_dir(path)?{visit(base,&e?.path(),out)?;}}
        Ok(())
    }
    let mut result=BTreeMap::new();visit(base,base,&mut result)?;Ok(result)
}
fn record(root:&ProjectReadRoot,kind:&str)->Result<(String,Vec<u8>)> {
    let mut original=Binding::from(root.binding);
    if kind=="prior" {original.volume^=1;}
    let name=binding_key(&original)?;
    let value=json!({"schema":1,"persistent":root.binding.persistent.context("Fixture needs persistent identity")?,"original":original});
    Ok((name,serde_json::to_vec(&value)?))
}
fn put(host:&Path,name:&str,wire:Option<&[u8]>,sentinel:Option<&str>)->Result<PathBuf> {
    let path=host.join(name);fs::create_dir(&path)?;
    if let Some(bytes)=wire{fs::write(path.join(ASSOCIATION),bytes)?;}
    if let Some(name)=sentinel{fs::write(path.join(name),b"retained fixture evidence;not a real operation")?;}
    Ok(path)
}
fn error(e:&anyhow::Error)->Value {
    let unresolved=e.downcast_ref::<UnassociatedState>().map(|u|u.records.iter().map(|p|p.file_name().unwrap().to_string_lossy().into_owned()).collect::<Vec<_>>());
    json!({"message":format!("{e:#}"),"unassociated":unresolved})
}
fn observe(id:&str,kind:&str,base:&Path,root:&ProjectReadRoot,publisher:&Publisher,images:&Path)->Result<()> {
    let before=image(base)?;let raw=serde_json::to_vec(&before)?;let digest=hex(&Sha256::digest(&raw));
    let image_name=format!("{id}.image.json");fs::write(images.join(&image_name),&raw)?;
    let resolved=match publisher.resolve_project_state(root){Ok(v)=>json!({"ok":true,"selected":v.map(|(name,_)|name),"error":null}),Err(e)=>json!({"ok":false,"selected":null,"error":error(&e)})};
    let found=match publisher.find_project_state(root){Ok(v)=>json!({"ok":true,"found":v.is_some(),"error":null}),Err(e)=>json!({"ok":false,"found":null,"error":error(&e)})};
    let bound=match publisher.bound_root_key(root){Ok(v)=>json!({"ok":true,"key":v,"error":null}),Err(e)=>json!({"ok":false,"key":null,"error":error(&e)})};
    let after=image(base)?;let after_raw=serde_json::to_vec(&after)?;
    println!("{}",json!({"id":id,"setup":kind,"fixture":base.file_name().unwrap().to_string_lossy(),
        "root":object(root.binding),"rootLocationHex":hex(root.selected().strip_prefix(base)?.as_os_str().as_bytes()),
        "currentKey":root_key(root).ok(),"image":image_name,"beforeSha256":digest,"afterSha256":hex(&Sha256::digest(&after_raw)),
        "entries":before.len(),"resolved":resolved,"found":found,"bound":bound}));
    ensure!(before==after,"Read-only discovery changed fixture {id}");Ok(())
}
pub(crate) fn run(cases:&Path)->Result<()> {
    fs::create_dir(cases)?;let images=cases.parent().unwrap().parent().unwrap().join("images");fs::create_dir(&images)?;
    let kinds=["empty","current-empty","current-state-lock","current-operation-lock","current-unassociated",
        "prior-empty","prior-unassociated","valid-current","valid-prior-device","duplicate","selected-plus-unassociated",
        "foreign-prior","foreign-current","misnamed-association","schema","malformed","oversized","exact-limit",
        "missing-field","unknown-field","duplicate-field","nested-unknown","record-link","record-directory","record-fifo",
        "state-symlink","state-file","unrelated-bad","nonutf8","root-moved","root-replaced","locked-discovery","escaped-coordinates","limit4096"];
    for kind in kinds {
        let base=cases.join(kind);fs::create_dir(&base)?;
        let project=base.join(if kind=="escaped-coordinates"{"project 日本\nfalse heading"}else{"project"});fs::create_dir(&project)?;
        fs::write(project.join("document.txt"),b"unchanged author input")?;
        let host=base.join("host");fs::create_dir(&host)?;
        let root=ProjectReadRoot::open(&project)?;
        let publisher=Publisher{host:Dir::open_ambient_dir(&host,cap_std::ambient_authority())?,location:host.clone()};
        let (current,current_wire)=record(&root,"current")?;let (prior,prior_wire)=record(&root,"prior")?;
        let mut held_lock=None;
        match kind {
            "empty"=>{},
            "current-empty"=>{put(&host,&current,None,None)?;},
            "current-state-lock"=>{put(&host,&current,None,Some("state.lock"))?;},
            "current-operation-lock"=>{put(&host,&current,None,Some("operation.lock"))?;},
            "current-unassociated"|"escaped-coordinates"=>{put(&host,&current,None,Some("journal.json"))?;},
            "prior-empty"=>{put(&host,&prior,None,None)?;},
            "prior-unassociated"=>{put(&host,&prior,None,Some("runtime.json"))?;},
            "valid-current"|"locked-discovery"|"limit4096"=>{
                let path=put(&host,&current,Some(&current_wire),None)?;
                if kind=="locked-discovery"{let file=fs::File::create(path.join("operation.lock"))?;file.try_lock()?;held_lock=Some(file);}
                if kind=="limit4096"{for i in 0..4095{fs::write(host.join(format!("entry-{i:04}")),b"")?;}}
            },
            "valid-prior-device"=>{put(&host,&prior,Some(&prior_wire),Some("journal.json"))?;},
            "duplicate"=>{put(&host,&current,Some(&current_wire),None)?;put(&host,&prior,Some(&prior_wire),None)?;},
            "selected-plus-unassociated"=>{put(&host,&current,Some(&current_wire),None)?;put(&host,&prior,None,None)?;},
            "foreign-prior"|"foreign-current"=>{
                let (name,wire)=if kind=="foreign-prior"{(&prior,&prior_wire)}else{(&current,&current_wire)};
                let mut value:Value=serde_json::from_slice(wire)?;let byte=value["persistent"][0].as_u64().unwrap();value["persistent"][0]=json!(byte^1);
                put(&host,name,Some(&serde_json::to_vec(&value)?),None)?;
            },
            "misnamed-association"=>{put(&host,&current,Some(&prior_wire),None)?;},
            "schema"|"missing-field"|"unknown-field"|"nested-unknown"=>{
                let mut value:Value=serde_json::from_slice(&current_wire)?;
                match kind{"schema"=>value["schema"]=json!(2),"missing-field"=>{value.as_object_mut().unwrap().remove("persistent");},
                    "unknown-field"=>value["adopt"]=json!(true),"nested-unknown"=>value["original"]["extra"]=json!(0),_=>unreachable!()}
                put(&host,&current,Some(&serde_json::to_vec(&value)?),None)?;
            },
            "malformed"=>{put(&host,&current,Some(b"{ truncated association"),None)?;},
            "oversized"=>{put(&host,&current,Some(&vec![b' ';1025]),None)?;},
            "exact-limit"=>{let mut wire=current_wire.clone();ensure!(wire.len()<1024);wire.resize(1024,b' ');put(&host,&current,Some(&wire),None)?;},
            "duplicate-field"=>{let mut wire=String::from_utf8(current_wire.clone())?;ensure!(wire.ends_with('}'));wire.pop();wire.push_str(",\"schema\":1}");put(&host,&current,Some(wire.as_bytes()),None)?;},
            "record-link"=>{let path=put(&host,&current,None,None)?;fs::write(base.join("external-record"),&current_wire)?;symlink(base.join("external-record"),path.join(ASSOCIATION))?;},
            "record-directory"=>{let path=put(&host,&current,None,None)?;fs::create_dir(path.join(ASSOCIATION))?;},
            "record-fifo"=>{let path=put(&host,&current,None,None)?.join(ASSOCIATION);let path=std::ffi::CString::new(path.as_os_str().as_bytes())?;ensure!(unsafe{libc::mkfifo(path.as_ptr(),0o600)}==0,"Fixture mkfifo failed");},
            "state-symlink"=>{let target=base.join("outside-state");fs::create_dir(&target)?;fs::write(target.join(ASSOCIATION),&current_wire)?;symlink(target,host.join(&current))?;},
            "state-file"=>{fs::write(host.join(&current),&current_wire)?;},
            "unrelated-bad"=>{put(&host,"unrelated-corrupt",Some(b"invalid"),None)?;symlink(base.join("missing"),host.join("unrelated-link"))?;},
            "nonutf8"=>{use std::os::unix::ffi::OsStringExt;
                if let Err(e)=fs::write(host.join(std::ffi::OsString::from_vec(vec![0xff])),b"opaque"){
                    let state=image(&base)?;let raw=serde_json::to_vec(&state)?;let image_name="nonutf8.image.json";
                    fs::write(images.join(image_name),&raw)?;
                    println!("{}",json!({"id":kind,"setup":kind,"setupUnavailable":true,"sourceCalls":0,
                        "error":e.to_string(),"errno":e.raw_os_error(),"fixture":kind,"image":image_name,"imageSha256":hex(&Sha256::digest(&raw))}));
                    continue;
                }
            },
            "root-moved"=>{fs::rename(&project,base.join("moved-project"))?;},
            "root-replaced"=>{fs::rename(&project,base.join("old-project"))?;fs::create_dir(&project)?;fs::write(project.join("document.txt"),b"unchanged author input")?;},
            _=>anyhow::bail!("Unknown fixture setup"),
        }
        observe(kind,kind,&base,&root,&publisher,&images)?;
        if kind=="limit4096"{fs::write(host.join("one-extra-entry"),b"")?;observe("limit4097","limit4097",&base,&root,&publisher,&images)?;}
        drop(held_lock);
    }
    Ok(())
}
