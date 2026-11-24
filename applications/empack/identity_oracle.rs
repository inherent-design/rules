// Fixture adapters and source-function calls. Not a project root/capture API.
fn object_value(x: ObjectIdentity) -> Value {
    json!({"volume":x.volume.to_string(),"object":x.object.to_string(),"created":x.created,"persistent":x.persistent})
}
fn emit(id:&str,kind:&str,origin:&str,input:Value,outcome:Value) {
    println!("{}",json!({"id":id,"kind":kind,"origin":origin,"input":input,"outcome":outcome}));
}
fn pair(id:&str,origin:&str,left:ObjectIdentity,right:ObjectIdentity) {
    emit(id,"identity",origin,json!({"left":object_value(left),"right":object_value(right)}),
        json!({"liveEqual":left==right,"durableEqual":left.persistent.is_some()&&left.persistent==right.persistent,
        "journal":publication::journal_result(Some(left),Some(right))}));
}
fn journal_case(id:&str,saved:Option<ObjectIdentity>,observed:Option<ObjectIdentity>) {
    emit(id,"journal-optional","controlled-values",json!({"saved":saved.map(object_value),"observed":observed.map(object_value)}),
        publication::journal_result(saved,observed));
}
fn observed_file(file:&File)->Result<FileObservation> {
    let mut reader=file.try_clone()?;reader.seek(SeekFrom::Start(0))?;
    let mut bytes=Vec::new();reader.read_to_end(&mut bytes)?;
    let metadata=file.metadata()?;
    Ok(FileObservation{content:Sha256::digest(&bytes).into(),bytes:bytes.len() as u64,
        readonly:metadata.permissions().readonly(),mode:metadata.permissions().mode(),object:native::identity(file)?})
}
fn path(s:&str)->PortableRelPath {PortableRelPath::parse(s,PathSyntax::ProjectContent).unwrap()}
fn clone_snapshot(s:&NativeSnapshot)->NativeSnapshot {NativeSnapshot{root:s.root,groups:vec![],entries:s.entries.clone()}}
fn dump(s:&NativeSnapshot)->Value {
    let entries:Vec<_>=s.entries.iter().map(|(p,o)|{
        let data=match o {
            Observation::Absent=>json!({"tag":"absent"}),
            Observation::Ancestor(binding)=>json!({"tag":"ancestor","object":object_value(binding.0)}),
            Observation::File(f)=>json!({"tag":"file","object":object_value(f.object),"content":f.content,
                "bytes":f.bytes,"readonly":f.readonly,"mode":f.mode}),
            Observation::Directory{members,binding}=>json!({"tag":"directory","object":object_value(binding.0),"members":members}),
        };json!({"path":p.as_str(),"observation":data})
    }).collect();json!({"root":object_value(s.root),"entries":entries})
}
fn fingerprint_case(id:&str,origin:&str,left:&NativeSnapshot,right:&NativeSnapshot) {
    let a=left.fingerprint();let b=right.fingerprint();
    emit(id,"fingerprint",origin,json!({"left":dump(left),"right":dump(right)}),json!({
        "leftOk":a.is_ok(),"rightOk":b.is_ok(),"equal":match(&a,&b){(Ok(a),Ok(b))=>Some(a==b),_=>None},
        "left":a.as_ref().ok(),"right":b.as_ref().ok(),"leftError":a.err().map(|e|format!("{e:#}")),"rightError":b.err().map(|e|format!("{e:#}")),
        "rootIdentityEqual":left.root==right.root,"entriesEqual":left.entries==right.entries}));
}
fn association_case(id:&str,origin:&str,saved:ObjectIdentity,current:ObjectIdentity,wrong_name:bool)->Result<()> {
    emit(id,"association-predicate",origin,json!({"saved":object_value(saved),"observed":object_value(current),"wrongName":wrong_name}),
        publication::association_result(saved,current,wrong_name)?);Ok(())
}

pub(crate) fn run(root:&Path)->Result<()> {
    fs::create_dir(root)?;fs::create_dir(root.join("folder"))?;fs::create_dir(root.join("parent"))?;
    fs::write(root.join("folder/a"),b"member")?;fs::write(root.join("original"),b"identical\n")?;
    let original=File::open(root.join("original"))?;let root_file=File::open(root)?;
    let folder_file=File::open(root.join("folder"))?;let parent_file=File::open(root.join("parent"))?;
    let r=native::identity(&root_file)?;let a=native::identity(&original)?;
    ensure!(r.persistent.is_some()&&a.persistent.is_some(),"Fixture filesystem does not expose durable object identity");
    let initial=observed_file(&original)?;
    let baseline=NativeSnapshot{root:r,groups:vec![],entries:BTreeMap::from([
        (path("original"),Observation::File(initial.clone())),
        (path("folder"),Observation::Directory{members:BTreeSet::from(["a".into()]),binding:DirectoryBinding(native::identity(&folder_file)?)}),
        (path("parent"),Observation::Ancestor(DirectoryBinding(native::identity(&parent_file)?))),
        (path("not-present"),Observation::Absent)])};
    pair("original-self","native-files",a,a);
    fs::rename(root.join("original"),root.join("renamed"))?;
    let renamed=File::open(root.join("renamed"))?;let moved=native::identity(&renamed)?;
    pair("retained-handle-after-rename","native-files",a,native::identity(&original)?);
    pair("reopened-after-rename","native-files",a,moved);
    fs::write(root.join("original"),b"identical\n")?;
    let replacement=File::open(root.join("original"))?;let replaced=native::identity(&replacement)?;
    pair("same-path-same-byte-replacement","native-files",a,replaced);
    fs::copy(root.join("renamed"),root.join("copy"))?;
    let copied=File::open(root.join("copy"))?;pair("copied-same-bytes","native-files",a,native::identity(&copied)?);
    fs::write(root.join("renamed"),b"changed!\n")?;let edited=observed_file(&renamed)?;
    pair("content-edit-same-object","native-files",a,edited.object);
    fs::set_permissions(root.join("renamed"),fs::Permissions::from_mode(0o600))?;let mode=observed_file(&renamed)?;
    pair("mode-edit-same-object","native-files",a,mode.object);
    fs::set_permissions(root.join("renamed"),fs::Permissions::from_mode(0o400))?;let readonly=observed_file(&renamed)?;
    pair("readonly-edit-same-object","native-files",a,readonly.object);
    let boot=native::retokenize(&original,a,"volume")?;
    pair("boot-device-counterfactual","synthetic-field",a,boot);
    let unavailable=native::retokenize(&original,a,"missing-created")?;
    pair("missing-created-counterfactual","synthetic-field",a,unavailable);
    pair("different-object-counterfactual","synthetic-field",a,native::retokenize(&original,a,"object")?);
    pair("different-birth-counterfactual","synthetic-field",a,native::retokenize(&original,a,"created")?);
    journal_case("journal-both-absent",None,None);
    journal_case("journal-absence-versus-present",None,Some(a));
    journal_case("journal-present-versus-absent",Some(a),None);
    journal_case("journal-same-object",Some(a),Some(a));
    journal_case("journal-device-counterfactual",Some(a),Some(boot));
    journal_case("journal-observation-unavailable",Some(a),Some(unavailable));
    journal_case("journal-same-bytes-replacement",Some(a),Some(replaced));
    journal_case("journal-capture-unavailable",Some(unavailable),Some(a));
    journal_case("journal-content-is-separate",Some(a),Some(edited.object));

    let valid=publication::wire(a)?;let value:Value=serde_json::from_slice(&valid)?;
    let token=serde_json::to_string(&value["persistent"])?;
    let mut codec:Vec<(&str,Vec<u8>)>=vec![("binding-valid",valid.clone()),("binding-missing",b"{}".to_vec()),
        ("binding-null",b"{\"persistent\":null}".to_vec()),("binding-legacy",serde_json::to_vec(&json!({"volume":a.volume,"object":a.object.to_le_bytes(),"created":a.created}))?),
        ("binding-duplicate",format!("{{\"persistent\":{token},\"persistent\":{token}}}").into_bytes())];
    for(label,field,data)in[("binding-extra-live-field","volume",json!(a.volume)),("binding-extra-schema","schema",json!(5))]{
        let mut v=value.clone();v[field]=data;codec.push((label,serde_json::to_vec(&v)?));
    }
    for(label,size)in[("binding-short",31usize),("binding-long",33usize)]{
        codec.push((label,serde_json::to_vec(&json!({"persistent":vec![0u8;size]}))?));
    }
    for(label,byte)in[("binding-negative",json!(-1)),("binding-out-of-range",json!(256)),("binding-wrong-type",json!("x"))]{
        let mut v=value.clone();v["persistent"][0]=byte;codec.push((label,serde_json::to_vec(&v)?));
    }
    for(id,wire)in codec{emit(id,"journal-codec","supplied-wire",json!({"wire":wire}),publication::decode(&wire));}

    fingerprint_case("snapshot-identical","assembled-observations",&baseline,&baseline);
    let mut volumes=clone_snapshot(&baseline);volumes.root.volume^=1;
    for observation in volumes.entries.values_mut(){match observation{
        Observation::Absent=>(),Observation::File(f)=>f.object.volume^=1,
        Observation::Ancestor(b)|Observation::Directory{binding:b,..}=>b.0.volume^=1,
    }}
    fingerprint_case("snapshot-device-counterfactual","synthetic-field",&baseline,&volumes);
    let mut positioned=clone_snapshot(&baseline);let file=positioned.entries.remove(&path("original")).unwrap();positioned.entries.insert(path("renamed"),file);
    fingerprint_case("snapshot-path-change","assembled-native-observations",&baseline,&positioned);
    let mut replaced_snapshot=clone_snapshot(&baseline);replaced_snapshot.entries.insert(path("original"),Observation::File(observed_file(&replacement)?));
    fingerprint_case("snapshot-same-byte-replacement","assembled-native-observations",&baseline,&replaced_snapshot);
    let mut edited_snapshot=clone_snapshot(&baseline);edited_snapshot.entries.insert(path("original"),Observation::File(edited.clone()));
    fingerprint_case("snapshot-content-edit","assembled-native-observations",&baseline,&edited_snapshot);
    let mut mode_snapshot=clone_snapshot(&baseline);mode_snapshot.entries.insert(path("original"),Observation::File(mode));
    fingerprint_case("snapshot-mode-edit","assembled-native-observations",&edited_snapshot,&mode_snapshot);
    let mut readonly_snapshot=clone_snapshot(&baseline);readonly_snapshot.entries.insert(path("original"),Observation::File(readonly));
    fingerprint_case("snapshot-readonly-edit","assembled-native-observations",&mode_snapshot,&readonly_snapshot);
    fs::write(root.join("folder/b"),b"new member")?;
    let mut membership=clone_snapshot(&baseline);
    if let Observation::Directory{members,..}=membership.entries.get_mut(&path("folder")).unwrap(){
        *members=fs::read_dir(root.join("folder"))?.map(|e|e.map(|e|e.file_name().into_string().expect("fixture ASCII"))).collect::<std::io::Result<_>>()?;
    }
    fingerprint_case("snapshot-directory-membership","assembled-native-observations",&baseline,&membership);
    fs::write(root.join("not-present"),b"new occupant")?;
    let mut occupied=clone_snapshot(&baseline);occupied.entries.insert(path("not-present"),Observation::File(observed_file(&File::open(root.join("not-present"))?)?));
    fingerprint_case("snapshot-new-occupant","assembled-native-observations",&baseline,&occupied);
    let mut missing_root=clone_snapshot(&baseline);missing_root.root.persistent=None;
    fingerprint_case("snapshot-root-unavailable","synthetic-field",&baseline,&missing_root);
    let mut missing_file=clone_snapshot(&baseline);
    if let Observation::File(f)=missing_file.entries.get_mut(&path("original")).unwrap(){f.object.persistent=None;}
    fingerprint_case("snapshot-file-unavailable","synthetic-field",&baseline,&missing_file);
    let mut reinserted=clone_snapshot(&baseline);reinserted.entries=baseline.entries.iter().rev().map(|(p,o)|(p.clone(),o.clone())).collect();
    fingerprint_case("snapshot-insertion-order","assembled-observations",&baseline,&reinserted);

    association_case("association-self","controlled-root-adapter",r,r,false)?;
    let boot_root=native::retokenize(&root_file,r,"volume")?;
    association_case("association-device-counterfactual","synthetic-field",r,boot_root,false)?;
    association_case("association-wrong-name","controlled-root-adapter",r,r,true)?;
    association_case("association-foreign-object","controlled-root-adapter",r,native::identity(&folder_file)?,false)?;
    association_case("association-missing-durable","synthetic-field",r,native::retokenize(&root_file,r,"missing-created")?,false)?;
    for(name,errno)in[("ENOTSUP",libc::ENOTSUP),("ENOTTY",libc::ENOTTY),("ENOSYS",libc::ENOSYS),
        ("EACCES",libc::EACCES),("EPERM",libc::EPERM),("ENOENT",libc::ENOENT),("EINVAL",libc::EINVAL),("EIO",libc::EIO)]{
        let result=native::injected_error(errno);
        emit(&format!("availability-{name}"),"availability","injected-errno",json!({"name":name,"errno":errno}),
            json!({"ok":result.is_ok(),"available":result.as_ref().ok().map(|v|v.is_some()),"error":result.err().map(|e|format!("{e:#}"))}));
    }
    Ok(())
}
