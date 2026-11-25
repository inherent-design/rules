use std::{env,fs,io::Write,path::PathBuf};
fn main() {
    println!("cargo::rerun-if-changed=build.rs");
    println!("cargo::rerun-if-changed=input.txt");
    println!("cargo::rerun-if-env-changed=RULES_TRACKED");
    println!("cargo::rerun-if-env-changed=RULES_FAIL");
    let watched=env::var("RULES_TRACKED").ok();
    // Deliberately undeclared input. Its omission is a fixture violation.
    let hidden=env::var("RULES_HIDDEN").ok();
    let fail=env::var_os("RULES_FAIL").is_some();
    let input=fs::read_to_string("input.txt").unwrap();
    let data=format!("tracked={:?};hidden={:?};file={};fail={}",watched,hidden,input.trim(),fail);
    let mut journal=fs::OpenOptions::new().append(true).create(true)
        .open(env::var_os("RULES_JOURNAL").unwrap()).unwrap();
    writeln!(journal,"start {}",data).unwrap();
    let out=PathBuf::from(env::var_os("OUT_DIR").unwrap());
    fs::write(out.join("selected.txt"),&data).unwrap();
    writeln!(journal,"wrote {}",out.join("selected.txt").display()).unwrap();
    if fail {
        writeln!(journal,"failed").unwrap();
        panic!("controlled failure after generated-file write");
    }
    writeln!(journal,"success").unwrap();
}
