//! Research ABI around the unchanged current DocumentCodec and its submodules.
//! This is not a production portable project format or an execution capability.
use serde::Deserialize;
use serde_json::{Value, json};
pub mod engine { pub mod documents; }
const MAX:usize=65536;
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Request { schema:u32, action:String, author_hex:String, bindings_hex:Option<String>, rename:Option<String> }
fn bytes(value:&str)->Result<Vec<u8>,String>{
 if value.len()>MAX||value.len()%2!=0{return Err("Study hex bound".into())}
 value.as_bytes().chunks_exact(2).map(|pair|{fn digit(b:u8)->Result<u8,String>{match b{b'0'..=b'9'=>Ok(b-b'0'),b'a'..=b'f'=>Ok(b-b'a'+10),_=>Err("Study hex digit".into())}}Ok(digit(pair[0])?*16+digit(pair[1])?)}).collect()
}
fn hex(value:&[u8])->String{value.iter().map(|b|format!("{b:02x}")).collect()}
fn evaluate(input:&[u8])->anyhow::Result<Value>{
 anyhow::ensure!(input.len()<=MAX,"Study request bound");
 let request:Request=serde_json::from_slice(input)?;
 anyhow::ensure!(request.schema==1,"Unsupported study schema");
 anyhow::ensure!(matches!(request.action.as_str(),"decode"|"rename"),"Unknown study action");
 anyhow::ensure!((request.action=="rename")==request.rename.is_some(),"Study rename field does not match action");
 let raw=bytes(&request.author_hex).map_err(anyhow::Error::msg)?;
 let bindings=request.bindings_hex.as_deref().map(bytes).transpose().map_err(anyhow::Error::msg)?;
 let codec=engine::documents::DocumentCodec;
 let source=codec.decode_authoring(&raw,bindings.as_deref(),"portable document study")?;
 let encoded=codec.encode_authoring(source.intent())?;
 let mut result=json!({"ok":true,"semantic":hex(&source.semantic_revision().0),"raw":hex(&source.raw_revision().0),"bindingsRevision":source.bindings_revision().map(|v|hex(&v.0)),"pack":{"id":source.intent().metadata.id,"name":source.intent().metadata.name,"version":source.intent().metadata.version},"normalizedAuthorHex":hex(&encoded.intent),"normalizedBindingsHex":encoded.bindings.as_deref().map(hex),"inspection":codec.inspect_authoring(&source,None)});
 if let Some(name)=request.rename {
  let mut next=source.intent().clone();next.metadata.name=name;
  let prepared=codec.replace_intent(&source,&next)?;
  let decoded=codec.decode_authoring(&prepared.bytes,prepared.bindings.as_deref(),"prepared study edit")?;
  result["prepared"]=json!({"expectedRaw":hex(&prepared.expected.0),"bindingsExpected":prepared.bindings_expected.map(|v|hex(&v.0)),"authorHex":hex(&prepared.bytes),"bindingsHex":prepared.bindings.as_deref().map(hex),"edit":format!("{:?}",prepared.edit),"semantic":hex(&decoded.semantic_revision().0),"name":decoded.intent().metadata.name});
 }
 Ok(result)
}
pub fn dispatch(input:&[u8])->Vec<u8>{
 let value=match evaluate(input){Ok(value)=>value,Err(error)=>json!({"ok":false,"error":format!("{error:#}")})};
 let output=serde_json::to_vec(&value).unwrap();
 if output.len()>MAX{serde_json::to_vec(&json!({"ok":false,"error":"Study output bound"})).unwrap()}else{output}
}
#[cfg(target_arch="wasm32")]
mod wasm{
 use std::sync::Mutex;
 static INPUT:Mutex<Vec<u8>>=Mutex::new(Vec::new());static OUTPUT:Mutex<Vec<u8>>=Mutex::new(Vec::new());
 #[unsafe(no_mangle)]pub extern "C" fn prepare_input(n:u32)->u32{if n as usize>super::MAX{return 0}let mut v=INPUT.lock().unwrap();v.clear();v.resize(n as usize,0);v.as_mut_ptr()as u32}
 #[unsafe(no_mangle)]pub extern "C" fn run_project()->u32{let input=INPUT.lock().unwrap();*OUTPUT.lock().unwrap()=super::dispatch(&input);0}
 #[unsafe(no_mangle)]pub extern "C" fn output_ptr()->u32{OUTPUT.lock().unwrap().as_ptr()as u32}
 #[unsafe(no_mangle)]pub extern "C" fn output_len()->u32{OUTPUT.lock().unwrap().len()as u32}
}
