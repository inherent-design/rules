//! Research adapter; the producer injects unchanged address and encoding bodies.
use empack_core::{model::ContentLayer, path::{PathSyntax, PortableRelPath}};
type Result<T> = std::result::Result<T, Box<dyn std::error::Error>>;

/*ADDRESS*/

mod encoding {
/*ENCODING*/
}

fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}
fn unhex(value: &str) -> Vec<u8> {
    assert!(value.len().is_multiple_of(2));
    value.as_bytes().chunks_exact(2).map(|pair| {
        u8::from_str_radix(std::str::from_utf8(pair).unwrap(), 16).unwrap()
    }).collect()
}
fn main() {
    let text = std::fs::read_to_string(std::env::args().nth(1).unwrap()).unwrap();
    for (index, line) in text.lines().enumerate() {
        let (kind, value) = line.split_once('\t').unwrap();
        let bytes = unhex(value);
        let value = std::str::from_utf8(&bytes).unwrap();
        match kind {
            "address" => {
                let result = match template_address(value) {
                    Ok(None) => "ignore".to_owned(),
                    Err(error) => format!("error:{error}"),
                    Ok(Some((layer, path, mode))) => format!("{:?}:{}:{:?}", layer, hex(path.as_str().as_bytes()), mode),
                };
                println!("{index}\taddress\t{result}");
            },
            "value" => println!("{index}\tvalue\t{}\t{}", hex(encoding::ini_value(value).as_bytes()),
                hex(encoding::properties_value(value).as_bytes())),
            _ => panic!("Unknown study row kind"),
        }
    }
}
