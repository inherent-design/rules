use std::io::{Read,Write};
fn main(){let mut input=Vec::new();std::io::stdin().take(65537).read_to_end(&mut input).unwrap();let output=rules_document_study::dispatch(&input);std::io::stdout().write_all(&output).unwrap();}
