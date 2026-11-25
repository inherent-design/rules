use std::io::{BufRead,Write};
fn main(){let mut session=rules_joined_111512569488::Session::new();let input=std::io::stdin();let mut output=std::io::stdout().lock();for line in input.lock().split(b'\n'){let line=line.unwrap();if line.len()>65536{break;}let response=session.dispatch(&line);output.write_all(&response).unwrap();output.write_all(b"\n").unwrap();output.flush().unwrap();}}
