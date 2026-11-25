import Base

type Version is Data:
  Version{major: Nat, minor: Nat}
type Encoding is Data:
  Legacy{value: Nat}
  MajorMinor{major: Nat, minor: Nat}

def normalize(e: Encoding) -> Version:
  match e:
    case Legacy{n}: Version{n,0n}
    case MajorMinor{a,b}: Version{a,b}
def legacy_representation(v: Version) -> Maybe<&2,Nat>:
  match v:
    case Version{a,b}: Bool.pick(Maybe<&2,Nat>,Nat.is_eq(b,0n),Some{a},None{})
def declared_java_satisfied(required: Nat, available: Nat) -> Bool:
  Bool.not(Nat.is_gt(required,available))

law legacy_round_trip:
  for n: Nat
  {legacy_representation(normalize(Legacy{n})) == Some{n} : Maybe<&2,Nat>}
def legacy_round_trip(n):
  {==}
law pair_preserves_both:
  for a: Nat
  for b: Nat
  {normalize(MajorMinor{a,b}) == Version{a,b} : Version}
def pair_preserves_both(a,b):
  {==}
law resource_minor_refuses_legacy:
  {legacy_representation(Version{97n,1n}) == None{} : Maybe<&2,Nat>}
def resource_minor_refuses_legacy():
  {==}
law data_minor_refuses_legacy:
  {legacy_representation(Version{94n,1n}) == None{} : Maybe<&2,Nat>}
def data_minor_refuses_legacy():
  {==}
law zero_minor_can_be_legacy:
  {legacy_representation(Version{75n,0n}) == Some{75n} : Maybe<&2,Nat>}
def zero_minor_can_be_legacy():
  {==}
law required25_not_satisfied_by21:
  {declared_java_satisfied(25n,21n) == False{} : Bool}
def required25_not_satisfied_by21():
  {==}
law required21_not_satisfied_by17:
  {declared_java_satisfied(21n,17n) == False{} : Bool}
def required21_not_satisfied_by17():
  {==}
