import Base

#0mod,1resource,2shader,3data,4world; selected is admitted by caller.
def recognized(+kind: Nat,module: Bool,+pack: Bool,assets: Bool,+data: Bool,shaders: Bool) -> Bool:
  Bool.pick(Bool,Nat.is_eq(kind,0n),module,Bool.pick(Bool,Nat.is_eq(kind,1n),Bool.and(pack,Bool.or(assets,Bool.not(data))),Bool.pick(Bool,Nat.is_eq(kind,2n),shaders,Bool.and(Nat.is_eq(kind,3n),Bool.and(pack,data)))))
def reason(chosen: Bool,+kind: Nat,folder: Bool,valid: Bool,foreign: Bool,recognized: Bool,accept: Bool,roots: Nat,nonempty: Bool,inside: Bool) -> Nat:
  Bool.pick(Nat,chosen,
    Bool.pick(Nat,folder,Bool.pick(Nat,valid,
      Bool.pick(Nat,Nat.is_eq(kind,4n),
        Bool.pick(Nat,Bool.and(Nat.is_eq(roots,1n),nonempty),Bool.pick(Nat,inside,0n,7n),6n),
        Bool.pick(Nat,foreign,4n,Bool.pick(Nat,Bool.or(recognized,accept),0n,5n))),3n),2n),1n)
def admitted(code: Nat) -> Bool:
  Nat.is_eq(code,0n)
def materialized(code: Nat,dry: Bool) -> Bool:
  Bool.and(admitted(code),Bool.not(dry))
def outputs(code: Nat,dry: Bool,kind: Nat,members: Nat) -> Nat:
  Bool.pick(Nat,materialized(code,dry),Bool.pick(Nat,Nat.is_eq(kind,4n),members,1n),0n)
def server(+kind: Nat) -> Bool:
  Bool.and(Bool.not(Nat.is_eq(kind,1n)),Bool.not(Nat.is_eq(kind,2n)))
def canonical(+kind: Nat) -> String:
  Bool.pick(String,Nat.is_eq(kind,0n),"mod",Bool.pick(String,Nat.is_eq(kind,1n),"resource-pack",Bool.pick(String,Nat.is_eq(kind,2n),"shader-pack",Bool.pick(String,Nat.is_eq(kind,3n),"data-pack","world"))))
def source_kind(kind: Nat) -> String:
  Bool.pick(String,Nat.is_eq(kind,4n),"local-files","local")
def ordinary(base: String,filename: String) -> String:
  base ++ "/" ++ filename
def world_member(base: String,key: String,member: String) -> String:
  base ++ "/" ++ key ++ "/" ++ member
def placement(automatic: Bool,fixed: String,base: String,filename: String) -> String:
  Bool.pick(String,automatic,ordinary(base,filename),fixed)
# Suffix matching is the retained original Java source premise, not a native game run.
def suffix(regular: Bool,lowercase_zip: Bool) -> Bool:
  Bool.and(regular,lowercase_zip)
def compatible(layout: Bool,format_known: Bool,format_good: Bool,loader_known: Bool,loader_good: Bool) -> Bool:
  Bool.and(layout,Bool.and(format_known,Bool.and(format_good,Bool.and(loader_known,loader_good))))

law mixed_resource:
  {recognized(1n,False{},True{},True{},True{},False{}) == True{} : Bool}
def mixed_resource(): {==}
law mixed_datapack:
  {recognized(3n,False{},True{},True{},True{},False{}) == True{} : Bool}
def mixed_datapack(): {==}
law unknown_refused:
  {reason(True{},0n,True{},True{},False{},False{},False{},0n,False{},False{}) == 5n : Nat}
def unknown_refused(): {==}
law explicit_acceptance:
  {reason(True{},0n,True{},True{},False{},False{},True{},0n,False{},False{}) == 0n : Nat}
def explicit_acceptance(): {==}
law acceptance_keeps_import_guard:
  {reason(True{},0n,True{},True{},True{},False{},True{},0n,False{},False{}) == 4n : Nat}
def acceptance_keeps_import_guard(): {==}
law type_choice_needed:
  {reason(False{},0n,False{},True{},False{},False{},False{},0n,False{},False{}) == 1n : Nat}
def type_choice_needed(): {==}
law preview_writes_none:
  {materialized(0n,True{}) == False{} : Bool}
def preview_writes_none(): {==}
law two_worlds_refused:
  {reason(True{},4n,True{},True{},False{},False{},False{},2n,False{},False{}) == 6n : Nat}
def two_worlds_refused(): {==}
law world_member_count:
  {outputs(0n,False{},4n,2n) == 2n : Nat}
def world_member_count(): {==}
law resource_client_only:
  {server(1n) == False{} : Bool}
def resource_client_only(): {==}
law mod_both_sides:
  {server(0n) == True{} : Bool}
def mod_both_sides(): {==}
law unknown_format_not_compatible:
  {compatible(True{},False{},True{},True{},True{}) == False{} : Bool}
def unknown_format_not_compatible(): {==}
law fixed_destination:
  {placement(False{},"mods/module.jar","custom-mods","module.jar") == "mods/module.jar" : String}
def fixed_destination(): {==}
law automatic_destination:
  {placement(True{},"mods/unknown.jar","custom-mods","unknown.jar") == "custom-mods/unknown.jar" : String}
def automatic_destination(): {==}
