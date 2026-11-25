//! A bounded research join, not empack's production project format or writer.
use anyhow::{Context as _,Result,bail,ensure};
use serde::{Deserialize,Serialize};
use serde_json::{Value,json};
use sha2::{Digest,Sha256};
use std::{collections::{BTreeMap,BTreeSet},io::{self,Cursor,Read,Seek,SeekFrom,Write}};
use empack_core::{digest::ContentId,distribution::Recipe,files::FilePermissions,inventory::{BuildInventory,BuildSelection,ContentOwner,InventoryInput,OptionalPolicy,Representation},model::{ContentLayer,ExpectedContent,LoaderKind,ResolutionLock,ResolvedProject,RuntimeResolution},path::{InstallDestination,PathSyntax,PortableRelPath},requirements::{Requirement,Requirements}};
mod cancellation;
pub mod engine {
 pub mod documents;pub mod layout;pub mod prism;pub mod runtime_versions;pub mod templates;
 pub fn launcher(project:&empack_core::model::ResolvedProject,cancel:&crate::cancellation::Cancellation)->anyhow::Result<(Vec<u8>,Vec<u8>)>{
  let config=templates::render_default(project,include_str!("engine/instance.cfg.template"),[("INSTANCE_WRAPPER_COMMAND".into(),String::new())],16384,cancel)?;
  let profile=prism::profile(&project.lock().runtime)?;prism::verify_profile(&profile,&project.lock().runtime)?;Ok((config,profile))
 }
 pub fn verify_profile(bytes:&[u8],runtime:&empack_core::model::RuntimeResolution)->anyhow::Result<()>{prism::verify_profile(bytes,runtime)}
}
const PACKET:usize=65536;const CHUNK:usize=16384;const MAX_FILE:u64=8*1024*1024;const MAX_TOTAL:u64=8*1024*1024;const MAX_ZIP:u64=16*1024*1024;const MAX_OPS:usize=4;
fn hex(bytes:&[u8])->String{bytes.iter().map(|v|format!("{v:02x}")).collect()}
fn unhex(value:&str)->Result<Vec<u8>>{ensure!(value.len()<=PACKET&&value.len()%2==0,"Study hex bound");value.as_bytes().chunks_exact(2).map(|p|{let d=|b:u8|match b{b'0'..=b'9'=>Ok(b-b'0'),b'a'..=b'f'=>Ok(b-b'a'+10),_=>bail!("Invalid study hex")};Ok(d(p[0])?*16+d(p[1])?)}).collect()}
fn digest(bytes:&[u8])->String{hex(&Sha256::digest(bytes))}
fn opaque(value:&str)->bool{value.len()==36&&value.bytes().enumerate().all(|(i,b)|if[8,13,18,23].contains(&i){b==b'-'}else{b.is_ascii_digit()||(b'a'..=b'f').contains(&b)})}
#[derive(Clone,Serialize,Deserialize)]#[serde(deny_unknown_fields)]pub struct Asset{pub id:String,pub sha256:String,pub bytes:u64,pub original_name:String}
#[derive(Clone,Serialize,Deserialize)]#[serde(deny_unknown_fields)]pub struct Entry{pub source:String,pub destination:String,pub layer:u8,pub permissions:u8,pub asset:Option<Asset>}
#[derive(Clone,Serialize,Deserialize)]#[serde(deny_unknown_fields)]pub struct Draft{pub schema:u8,pub author_hex:String,pub bindings_hex:Option<String>,pub entries:Vec<Entry>}
#[derive(Serialize,Deserialize)]#[serde(deny_unknown_fields)]struct Snapshot{format:String,schema:u8,image:String,draft:Draft}
fn check(d:&Draft)->Result<()>{
 ensure!(d.schema==1&&d.entries.len()<=16,"Unsupported or oversized study draft");ensure!(unhex(&d.author_hex)?.len()<=8192,"Study author bound");if let Some(v)=&d.bindings_hex{ensure!(unhex(v)?.len()<=8192,"Study binding bound");}
 for e in &d.entries{ensure!(e.source.len()<=256&&e.destination.len()<=256&&e.layer<=3&&e.permissions<=3,"Study entry shape");if let Some(a)=&e.asset{ensure!(opaque(&a.id)&&a.bytes<=MAX_FILE&&a.sha256.len()==64&&unhex(&a.sha256)?.len()==32&&a.original_name.len()<=256,"Study asset shape");}}
 Ok(())
}
fn image(d:&Draft)->Result<String>{check(d)?;let mut h=Sha256::new();h.update(b"rules.empack.joined-study.image.v1\0");h.update(serde_json::to_vec(d)?);Ok(hex(&h.finalize()))}
fn document(d:&Draft)->Result<engine::documents::DecodedIntent>{engine::documents::DocumentCodec.decode_authoring(&unhex(&d.author_hex)?,d.bindings_hex.as_deref().map(unhex).transpose()?.as_deref(),"joined study")}
fn view(d:&Draft)->Result<Value>{let img=image(d)?;let interpretation=match document(d){Ok(v)=>json!({"valid":true,"name":v.intent().metadata.name,"semantic":hex(&v.semantic_revision().0)}),Err(e)=>json!({"valid":false,"error":format!("{e:#}")})};Ok(json!({"draft":d,"image":img,"interpretation":interpretation}))}
#[derive(Deserialize)]#[serde(tag="action",rename_all="kebab-case",deny_unknown_fields)]enum Request{
 Limits{schema:u8},Create{schema:u8,author_hex:String},Inspect{schema:u8,draft:Draft},Import{schema:u8,draft:Draft,assets:Vec<Asset>},Author{schema:u8,draft:Draft,author_hex:String},Rename{schema:u8,draft:Draft,name:String},Place{schema:u8,draft:Draft,index:usize,destination:String},Missing{schema:u8,draft:Draft,destination:String},Remove{schema:u8,draft:Draft,index:usize},Snapshot{schema:u8,draft:Draft},Reopen{schema:u8,wire:String},
 ObserveBegin{schema:u8,id:String,original_name:String},ObserveFeed{schema:u8,id:String,offset:u64,hex:String},ObserveEnd{schema:u8,id:String},Cancel{schema:u8,id:String},
 ExportBegin{schema:u8,id:String,draft:Draft,expected_image:String},ExportFeed{schema:u8,id:String,asset_id:String,offset:u64,hex:String},ExportVerify{schema:u8,id:String,fault:Option<String>},ArtifactRead{schema:u8,id:String,offset:u64},Status{schema:u8,id:String},
}
impl Request{fn schema(&self)->u8{match self{Self::Limits{schema}|Self::Create{schema,..}|Self::Inspect{schema,..}|Self::Import{schema,..}|Self::Author{schema,..}|Self::Rename{schema,..}|Self::Place{schema,..}|Self::Missing{schema,..}|Self::Remove{schema,..}|Self::Snapshot{schema,..}|Self::Reopen{schema,..}|Self::ObserveBegin{schema,..}|Self::ObserveFeed{schema,..}|Self::ObserveEnd{schema,..}|Self::Cancel{schema,..}|Self::ExportBegin{schema,..}|Self::ExportFeed{schema,..}|Self::ExportVerify{schema,..}|Self::ArtifactRead{schema,..}|Self::Status{schema,..}=>*schema}}}
struct Observation{hash:Sha256,bytes:u64,name:String}
struct Bounded(Cursor<Vec<u8>>);
impl Write for Bounded{fn write(&mut self,b:&[u8])->io::Result<usize>{if self.0.position().checked_add(b.len()as u64).is_none_or(|v|v>MAX_ZIP){return Err(io::Error::other("Study ZIP byte bound"));}self.0.write(b)}fn flush(&mut self)->io::Result<()>{Ok(())}}
impl Seek for Bounded{fn seek(&mut self,p:SeekFrom)->io::Result<u64>{let n=self.0.seek(p)?;if n>MAX_ZIP{return Err(io::Error::other("Study ZIP seek bound"));}Ok(n)}}
#[derive(Clone)]enum Source{Generated(Vec<u8>),Asset{asset:Asset,input:usize}}
#[derive(Clone)]struct Output{path:String,source:Source,sha:String,bytes:u64,mode:u32}
struct Writing{basis:String,outputs:Vec<Output>,inputs:Vec<InventoryInput>,runtime:RuntimeResolution,index:usize,offset:u64,hash:Sha256,header:bool,writer:zip::ZipWriter<Bounded>}
struct Awaiting{basis:String,outputs:Vec<Output>,inputs:Vec<InventoryInput>,runtime:RuntimeResolution,zip:Vec<u8>}
struct Artifact{basis:String,zip:Vec<u8>,inventory:Value,sha:String}
enum Export{Writing(Writing),Ready(Artifact)}
impl Writing{
 fn next(&mut self)->Result<Value>{
  while let Some(o)=self.outputs.get(self.index){
   if !self.header{self.writer.start_file(&o.path,zip::write::SimpleFileOptions::default().system(zip::System::Unix).unix_permissions(o.mode))?;self.header=true;}
   match &o.source{
    Source::Generated(bytes)=>{self.writer.write_all(bytes)?;self.index+=1;self.header=false;},
    Source::Asset{asset,..}=>{
     if self.offset==asset.bytes{self.complete_file()?;continue;}
     return Ok(json!({"phase":"needs-content","asset":asset,"offset":self.offset,"count":(asset.bytes-self.offset).min(CHUNK as u64),"basis":self.basis}));
    }
   }
  }
  Ok(json!({"phase":"needs-verification","basis":self.basis}))
 }
 fn complete_file(&mut self)->Result<()>{let o=&self.outputs[self.index];let actual=hex(&self.hash.clone().finalize());ensure!(actual==o.sha&&self.offset==o.bytes,"Retained bytes differ for {}",o.path);if let Source::Asset{input,..}=&o.source{let content: [u8;32]=unhex(&actual)?.try_into().unwrap();let mode=o.mode;self.inputs[*input].representation=Representation::Embedded{content:ContentId::from_sha256(content),bytes:self.offset,permissions:FilePermissions{readonly:mode&0o200==0,executable:mode&0o100!=0}};}self.index+=1;self.offset=0;self.hash=Sha256::new();self.header=false;Ok(())}
 fn feed(&mut self,asset_id:&str,offset:u64,bytes:&[u8])->Result<Value>{
  let o=self.outputs.get(self.index).context("Export expects no input")?;let Source::Asset{asset,..}=&o.source else{bail!("Export expects generated content")};ensure!(asset.id==asset_id&&self.offset==offset,"Input association/offset differs for {}",o.path);ensure!(!bytes.is_empty()&&bytes.len()<=CHUNK&&self.offset+bytes.len()as u64<=asset.bytes,"Input chunk bound");self.writer.write_all(bytes)?;self.hash.update(bytes);self.offset+=bytes.len()as u64;self.next()
 }
 fn finish(self)->Result<Awaiting>{ensure!(self.index==self.outputs.len(),"Export still needs input");let zip=self.writer.finish()?.0.into_inner();Ok(Awaiting{basis:self.basis,outputs:self.outputs,inputs:self.inputs,runtime:self.runtime,zip})}
}
fn prepare(d:Draft,basis:String)->Result<Writing>{
 ensure!(image(&d)?==basis,"Draft changed before export");let decoded=document(&d)?;let intent=decoded.intent();ensure!(intent.roots.is_empty(),"Study cannot resolve authored dependency roots");ensure!(intent.source_excludes.is_empty()&&intent.layout.is_empty(),"Study does not interpret custom discovery/layout policy");ensure!(intent.runtime.loader==LoaderKind::Vanilla,"Study exports an exact vanilla runtime only");
 let runtime=RuntimeResolution{minecraft:intent.runtime.minecraft.clone(),loader:LoaderKind::Vanilla,loader_version:None};let lock=ResolutionLock{acceptable_versions:intent.runtime.acceptable_versions.clone(),intent_revision:decoded.semantic_revision(),resolver:"rules-joined-study/no-provider-resolution".into(),dependencies:BTreeMap::new(),required_edges:BTreeMap::new(),coverage:BTreeMap::new(),runtime:runtime.clone()};let project=ResolvedProject::validate(intent.clone(),lock,decoded.semantic_revision())?;let cancel=cancellation::Cancellation::default();let(config,profile)=engine::launcher(&project,&cancel)?;
 let mut inputs=Vec::new();for(i,e)in d.entries.iter().enumerate(){let layer=match e.layer{0=>ContentLayer::Common,1=>ContentLayer::CommonOverride,2=>ContentLayer::Client,_=>ContentLayer::Server};let requirements=Requirements{client:if e.layer==3{Requirement::Unsupported}else{Requirement::Required},server:if e.layer==2{Requirement::Unsupported}else{Requirement::Required}};inputs.push(InventoryInput{owner:ContentOwner::Source(i.to_string()),destination:InstallDestination::parse(&e.destination)?,layer,requirements,representation:Representation::Unacquired{expected:ExpectedContent{digests:None,size:e.asset.as_ref().map(|a|a.bytes),accepted_observation:None}}});}
 let selected=BuildSelection::select(&inputs,Recipe::PRISM_BUNDLED,&OptionalPolicy::Resolve{choices:BTreeMap::new(),use_defaults:false})?;let mut outputs=Vec::new();for e in selected.entries(){let ContentOwner::Source(index)=&e.owner else{bail!("Unknown study source")};let index:usize=index.parse()?;let a=d.entries[index].asset.clone().with_context(||format!("Missing input for {}",e.destination.relative().as_str()))?;let p=d.entries[index].permissions;outputs.push(Output{path:format!(".minecraft/{}",e.destination.relative().as_str()),sha:a.sha256.clone(),bytes:a.bytes,mode:if p&1!=0{0o444}else{0o644}|if p&2!=0{0o111}else{0},source:Source::Asset{asset:a,input:index}});}
 for(path,bytes)in[("instance.cfg",config),("mmc-pack.json",profile)]{outputs.push(Output{path:path.into(),sha:digest(&bytes),bytes:bytes.len()as u64,mode:0o644,source:Source::Generated(bytes)});}
 outputs.sort_by(|a,b|a.path.cmp(&b.path));let mut collisions=engine::layout::CollisionIndex::default();let mut directories=BTreeSet::new();let mut total=0u64;for o in &outputs{collisions.insert_file(&PortableRelPath::parse(&o.path,PathSyntax::ArchiveMember)?)?;total=total.checked_add(o.bytes).context("Output length overflow")?;ensure!(total<=MAX_TOTAL,"Study output total bound");let mut p=o.path.as_str();while let Some((parent,_))=p.rsplit_once('/'){directories.insert(parent.to_owned());p=parent;}}
 let mut writer=zip::ZipWriter::new(Bounded(Cursor::new(Vec::new())));for p in directories{writer.add_directory(format!("{p}/"),zip::write::SimpleFileOptions::default().system(zip::System::Unix).unix_permissions(0o755))?;}
 Ok(Writing{basis,outputs,inputs,runtime,index:0,offset:0,hash:Sha256::new(),header:false,writer})
}
fn verify(mut a:Awaiting,fault:Option<String>)->Result<Artifact>{
 let _finished=BuildInventory::project(&a.inputs,Recipe::PRISM_BUNDLED,&OptionalPolicy::Resolve{choices:BTreeMap::new(),use_defaults:false})?;
 if let Some(f)=fault{ensure!(f=="truncate-archive","Unknown study fault");a.zip.truncate(a.zip.len()/2);}
 let mut zip=zip::ZipArchive::new(Cursor::new(&a.zip))?;let mut expected:BTreeMap<_,_>=a.outputs.iter().map(|o|(o.path.clone(),o)).collect();let mut directories=BTreeSet::new();for o in &a.outputs{let mut p=o.path.as_str();while let Some((parent,_))=p.rsplit_once('/'){directories.insert(format!("{parent}/"));p=parent;}}
 let mut rows=Vec::new();for i in 0..zip.len(){let mut f=zip.by_index(i)?;ensure!(!f.encrypted()&&!f.is_symlink(),"Encrypted/linked ZIP member");let path=f.name()?.into_owned();if f.is_dir(){ensure!(directories.remove(&path),"Unplanned/duplicate ZIP directory");ensure!(f.unix_mode().is_some_and(|v|v&0o777==0o755),"ZIP directory mode differs");continue;}let o=expected.remove(&path).context("Unplanned/duplicate ZIP file")?;ensure!(f.size()==o.bytes&&f.unix_mode().is_some_and(|v|v&0o777==o.mode),"ZIP size/mode differs for {path}");let mut h=Sha256::new();let mut total=0u64;let mut profile=Vec::new();loop{let mut b=[0u8;CHUNK];let n=f.read(&mut b)?;if n==0{break;}total+=n as u64;ensure!(total<=o.bytes,"ZIP decoded byte bound");h.update(&b[..n]);if path=="mmc-pack.json"{profile.extend_from_slice(&b[..n]);}}let hash=hex(&h.finalize());ensure!(total==o.bytes&&hash==o.sha,"ZIP content differs for {path}");if path=="mmc-pack.json"{engine::verify_profile(&profile,&a.runtime)?;}rows.push(json!({"path":path,"sha256":hash,"bytes":total,"mode":o.mode}));}
 ensure!(expected.is_empty()&&directories.is_empty(),"ZIP omits expected members");let sha=digest(&a.zip);Ok(Artifact{basis:a.basis,zip:a.zip,inventory:json!(rows),sha})
}
pub struct Session{observations:BTreeMap<String,Observation>,exports:BTreeMap<String,Export>}
impl Session{
 pub const fn new()->Self{Self{observations:BTreeMap::new(),exports:BTreeMap::new()}}
 fn reserve(&self,id:&str)->Result<()>{ensure!(opaque(id),"Invalid operation identity");ensure!(self.observations.len()+self.exports.len()<MAX_OPS&&!self.observations.contains_key(id)&&!self.exports.contains_key(id),"Operation capacity/identity unavailable");Ok(())}
 fn apply(&mut self,r:Request)->Result<Value>{ensure!(r.schema()==1,"Unsupported study request schema");match r{
 Request::Limits{..}=>Ok(json!({"chunk":CHUNK,"file":MAX_FILE,"totalOutput":MAX_TOTAL,"archive":MAX_ZIP,"entries":16,"author":8192,"format":"rules.empack.joined-study"})),
 Request::Create{author_hex,..}=>view(&Draft{schema:1,author_hex,bindings_hex:None,entries:Vec::new()}),Request::Inspect{draft,..}=>view(&draft),
 Request::Import{mut draft,assets,..}=>{for a in assets{let folder=if a.original_name.to_ascii_lowercase().ends_with(".jar"){"mods"}else{"config"};let destination=format!("{folder}/{}",a.original_name);draft.entries.push(Entry{source:format!("pack/{destination}"),destination,layer:0,permissions:0,asset:Some(a)});}view(&draft)},
 Request::Author{mut draft,author_hex,..}=>{draft.author_hex=author_hex;view(&draft)},
 Request::Rename{mut draft,name,..}=>{check(&draft)?;let source=document(&draft)?;let mut target=source.intent().clone();target.metadata.name=name;let p=engine::documents::DocumentCodec.replace_intent(&source,&target)?;draft.author_hex=hex(&p.bytes);draft.bindings_hex=p.bindings.as_deref().map(hex);view(&draft)},
 Request::Place{mut draft,index,destination,..}=>{let e=draft.entries.get_mut(index).context("Unknown entry")?;e.destination=destination;e.source=format!("pack/{}",e.destination);view(&draft)},
 Request::Missing{mut draft,destination,..}=>{draft.entries.push(Entry{source:format!("pack/{destination}"),destination,layer:0,permissions:0,asset:None});view(&draft)},Request::Remove{mut draft,index,..}=>{ensure!(index<draft.entries.len(),"Unknown entry");draft.entries.remove(index);view(&draft)},
 Request::Snapshot{draft,..}=>{let image=image(&draft)?;let wire=serde_json::to_string(&Snapshot{format:"rules.empack.joined-study".into(),schema:1,image:image.clone(),draft})?;ensure!(wire.len()<=24000,"Study snapshot bound");Ok(json!({"wire":wire,"image":image}))},
 Request::Reopen{wire,..}=>{ensure!(wire.len()<=24000,"Study snapshot bound");let saved:Snapshot=serde_json::from_str(&wire)?;ensure!(saved.schema==1&&saved.format=="rules.empack.joined-study"&&image(&saved.draft)?==saved.image,"Saved snapshot identity differs");view(&saved.draft)},
 Request::ObserveBegin{id,original_name,..}=>{self.reserve(&id)?;ensure!(original_name.len()<=256,"Source label bound");self.observations.insert(id.clone(),Observation{hash:Sha256::new(),bytes:0,name:original_name});Ok(json!({"id":id,"offset":0}))},
 Request::ObserveFeed{id,offset,hex:chunk,..}=>{let mut o=self.observations.remove(&id).context("Observation is not active")?;let b=unhex(&chunk)?;ensure!(o.bytes==offset&&!b.is_empty()&&b.len()<=CHUNK&&o.bytes+b.len()as u64<=MAX_FILE,"Observation association/byte bound");o.hash.update(&b);o.bytes+=b.len()as u64;let result=json!({"id":id,"offset":o.bytes});self.observations.insert(id,o);Ok(result)},
 Request::ObserveEnd{id,..}=>{let o=self.observations.remove(&id).context("Observation is not active")?;Ok(json!(Asset{id,sha256:hex(&o.hash.finalize()),bytes:o.bytes,original_name:o.name}))},
 Request::Cancel{id,..}=>{let observing=self.observations.remove(&id).is_some();let exporting=self.exports.remove(&id);let copied=matches!(exporting,Some(Export::Ready(_)));Ok(json!({"removed":observing||exporting.is_some(),"artifactMayHaveBeenCopied":copied}))},
 Request::ExportBegin{id,draft,expected_image,..}=>{self.reserve(&id)?;let mut w=prepare(draft,expected_image)?;let next=w.next()?;self.exports.insert(id,Export::Writing(w));Ok(next)},
 Request::ExportFeed{id,asset_id,offset,hex:chunk,..}=>{let state=self.exports.remove(&id).context("Export is not active")?;let Export::Writing(mut w)=state else{self.exports.insert(id,state);bail!("Export is not writing")};let next=w.feed(&asset_id,offset,&unhex(&chunk)?)?;self.exports.insert(id,Export::Writing(w));Ok(next)},
 Request::ExportVerify{id,fault,..}=>{let state=self.exports.remove(&id).context("Export is not active")?;let Export::Writing(w)=state else{self.exports.insert(id,state);bail!("Export is not awaiting verification")};let a=verify(w.finish()?,fault)?;let value=json!({"phase":"artifact-ready","basis":a.basis,"sha256":a.sha,"bytes":a.zip.len(),"inventory":a.inventory});self.exports.insert(id,Export::Ready(a));Ok(value)},
 Request::ArtifactRead{id,offset,..}=>{let Some(Export::Ready(a))=self.exports.get(&id)else{bail!("Verified artifact is not available")};let offset=usize::try_from(offset)?;ensure!(offset<=a.zip.len(),"Artifact offset bound");let end=(offset+CHUNK).min(a.zip.len());Ok(json!({"hex":hex(&a.zip[offset..end]),"offset":offset,"next":end,"done":end==a.zip.len(),"basis":a.basis}))},
 Request::Status{id,..}=>Ok(json!({"observation":self.observations.contains_key(&id),"export":match self.exports.get(&id){None=>"absent",Some(Export::Writing(_))=>"writing",Some(Export::Ready(_))=>"ready"}})),
 }}
 pub fn dispatch(&mut self,input:&[u8])->Vec<u8>{let result=(||{ensure!(input.len()<=PACKET,"Study packet bound");self.apply(serde_json::from_slice(input)?)})();let value=match result{Ok(v)=>json!({"ok":true,"value":v}),Err(e)=>json!({"ok":false,"error":format!("{e:#}")})};let out=serde_json::to_vec(&value).unwrap();if out.len()>PACKET{b"{\"ok\":false,\"error\":\"Study output bound\"}".to_vec()}else{out}}
}
#[cfg(target_arch="wasm32")]mod wasm{
 use std::sync::Mutex;static SESSION:Mutex<super::Session>=Mutex::new(super::Session::new());static INPUT:Mutex<Vec<u8>>=Mutex::new(Vec::new());static OUTPUT:Mutex<Vec<u8>>=Mutex::new(Vec::new());
 #[unsafe(no_mangle)]pub extern "C" fn prepare_input(n:u32)->u32{if n as usize>super::PACKET{return 0}let mut b=INPUT.lock().unwrap();b.clear();b.resize(n as usize,0);b.as_mut_ptr()as u32}
 #[unsafe(no_mangle)]pub extern "C" fn run_project()->u32{*OUTPUT.lock().unwrap()=SESSION.lock().unwrap().dispatch(&INPUT.lock().unwrap());0}
 #[unsafe(no_mangle)]pub extern "C" fn output_ptr()->u32{OUTPUT.lock().unwrap().as_ptr()as u32}#[unsafe(no_mangle)]pub extern "C" fn output_len()->u32{OUTPUT.lock().unwrap().len()as u32}
}
