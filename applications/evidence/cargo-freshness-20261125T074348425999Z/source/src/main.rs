fn main() {
    println!("{}|macro={:?}",include_str!(concat!(env!("OUT_DIR"),"/selected.txt")),option_env!("RULES_MACRO"));
}
