//! Research wire adapter around unchanged empack-core planners. Not an empack
//! project/document codec, full portable engine, exporter or authority boundary.
use empack_core::{digest::ContentId,distribution::Recipe,files::FilePermissions,inventory::{BuildInventory,ContentOwner,InventoryInput,OptionalPolicy,Representation},model::{ContentLayer,ExpectedContent},path::InstallDestination,requirements::{ChoiceKey,OptionalChoice,Requirement,Requirements}};
use std::collections::BTreeMap;
const MAX:usize=65536;
struct Reader<'a>{bytes:&'a[u8],pos:usize}
impl<'a> Reader<'a>{
 fn take(&mut self,n:usize)->Result<&'a[u8],String>{let end=self.pos.checked_add(n).ok_or("wire: length overflow")?;let out=self.bytes.get(self.pos..end).ok_or("wire: truncated")?;self.pos=end;Ok(out)}
 fn u8(&mut self)->Result<u8,String>{Ok(self.take(1)?[0])}
 fn u32(&mut self)->Result<u32,String>{Ok(u32::from_le_bytes(self.take(4)?.try_into().unwrap()))}
 fn u64(&mut self)->Result<u64,String>{Ok(u64::from_le_bytes(self.take(8)?.try_into().unwrap()))}
 fn text(&mut self)->Result<String,String>{let n=self.u32()?as usize;if n>512{return Err("wire: text limit".into())}String::from_utf8(self.take(n)?.to_vec()).map_err(|_|"wire: invalid UTF-8".into())}
}
fn u32out(out:&mut Vec<u8>,n:usize){out.extend_from_slice(&(n as u32).to_le_bytes());}
fn textout(out:&mut Vec<u8>,s:&str){u32out(out,s.len());out.extend_from_slice(s.as_bytes());}
fn requirement(tag:u8,path:&str)->Result<Requirement,String>{Ok(match tag{0=>Requirement::Unsupported,1=>Requirement::Required,2|3=>Requirement::Optional(OptionalChoice{key:ChoiceKey::parse(&format!("optional:{path}")).map_err(|e|format!("choice: {e:?}"))?,default_enabled:tag==3,description:None}),_=>return Err("wire: requirement".into())})}
fn layer(tag:u8)->Result<ContentLayer,String>{Ok(match tag{0=>ContentLayer::Common,1=>ContentLayer::CommonOverride,2=>ContentLayer::Client,3=>ContentLayer::Server,_=>return Err("wire: layer".into())})}
fn layer_tag(v:ContentLayer)->u8{match v{ContentLayer::Common=>0,ContentLayer::CommonOverride=>1,ContentLayer::Client=>2,ContentLayer::Server=>3}}
pub fn project(bytes:&[u8])->Result<Vec<u8>,String>{
 if bytes.len()>MAX{return Err("wire: request limit".into())}
 let mut r=Reader{bytes,pos:0};if r.take(4)?!=b"RPI1"{return Err("wire: version".into())}
 let recipe=match r.u8()?{0=>Recipe::PRISM_BUNDLED,1=>Recipe::SERVER_BUNDLED,2=>Recipe::EMPACK_BUNDLED,_=>return Err("wire: recipe".into())};
 let policy=match r.u8()?{0=>OptionalPolicy::Preserve,1=>OptionalPolicy::Resolve{choices:BTreeMap::new(),use_defaults:true},2=>OptionalPolicy::Resolve{choices:BTreeMap::new(),use_defaults:false},_=>return Err("wire: optional policy".into())};
 let count=r.u32()?;if count>32{return Err("wire: count".into())}let mut inputs=Vec::new();
 for index in 0..count{
  let path=r.text()?;let destination=InstallDestination::parse(&path).map_err(|e|format!("path: {e:?}"))?;let layer=layer(r.u8()?)?;
  let requirements=Requirements{client:requirement(r.u8()?,&path)?,server:requirement(r.u8()?,&path)?};
  let representation=r.u8()?;let perm=r.u8()?;if perm>3{return Err("wire: permissions".into())}let bytes=r.u64()?;let digest=r.take(32)?.try_into().unwrap();
  let representation=match representation{0=>Representation::Embedded{content:ContentId::from_sha256(digest),bytes,permissions:FilePermissions{readonly:perm&1!=0,executable:perm&2!=0}},1=>Representation::Unacquired{expected:ExpectedContent{digests:None,size:Some(bytes),accepted_observation:None}},_=>return Err("wire: representation".into())};
  inputs.push(InventoryInput{owner:ContentOwner::Source(index.to_string()),destination,layer,requirements,representation});
 }
 if r.pos!=r.bytes.len(){return Err("wire: trailing bytes".into())}
 let inventory=BuildInventory::project(&inputs,recipe,&policy).map_err(|e|format!("inventory: {e:?}"))?;
 let mut out=b"RPO1".to_vec();u32out(&mut out,inventory.entries().len());u32out(&mut out,inventory.precedence().len());u32out(&mut out,inventory.choices().len());
 for entry in inventory.entries(){
  let ContentOwner::Source(owner)=&entry.owner else{return Err("adapter: owner".into())};u32out(&mut out,owner.parse().map_err(|_|"adapter: owner index")?);textout(&mut out,entry.destination.relative().as_str());out.push(layer_tag(entry.layer));
  let Representation::Embedded{content,bytes,permissions}=&entry.representation else{return Err("adapter: unfinished representation".into())};out.extend_from_slice(&bytes.to_le_bytes());out.extend_from_slice(content.bytes());out.push(u8::from(permissions.readonly)|u8::from(permissions.executable)*2);
 }
 for choice in inventory.choices(){textout(&mut out,&choice.key);out.push(u8::from(choice.enabled));out.push(u8::from(choice.used_default));}
 if out.len()>MAX{return Err("adapter: output limit".into())}Ok(out)
}
// The browser host supplies observations only. No native source, publication,
// acquisition, process or root capability can be constructed through this wire.
#[cfg(target_arch="wasm32")]
mod wasm{
 use std::sync::Mutex;
 static INPUT:Mutex<Vec<u8>>=Mutex::new(Vec::new());static OUTPUT:Mutex<Vec<u8>>=Mutex::new(Vec::new());
 #[unsafe(no_mangle)]pub extern "C"fn prepare_input(n:u32)->u32{if n as usize>super::MAX{return 0}let mut v=INPUT.lock().unwrap();v.clear();v.resize(n as usize,0);v.as_mut_ptr()as u32}
 #[unsafe(no_mangle)]pub extern "C"fn run_project()->u32{let input=INPUT.lock().unwrap();let (status,output)=match super::project(&input){Ok(v)=>(0,v),Err(e)=>(1,e.into_bytes())};*OUTPUT.lock().unwrap()=output;status}
 #[unsafe(no_mangle)]pub extern "C"fn output_ptr()->u32{OUTPUT.lock().unwrap().as_ptr()as u32}
 #[unsafe(no_mangle)]pub extern "C"fn output_len()->u32{OUTPUT.lock().unwrap().len()as u32}
}
#[cfg(not(target_arch="wasm32"))]
fn main(){use std::io::{Read,Write};let mut input=Vec::new();std::io::stdin().take((MAX+1)as u64).read_to_end(&mut input).unwrap();let(status,output)=match project(&input){Ok(v)=>(0u32,v),Err(e)=>(1,e.into_bytes())};let mut out=std::io::stdout().lock();out.write_all(&status.to_le_bytes()).unwrap();out.write_all(&(output.len()as u32).to_le_bytes()).unwrap();out.write_all(&output).unwrap();}
